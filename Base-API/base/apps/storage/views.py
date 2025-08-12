from datetime import datetime, timedelta
from itertools import chain

import requests
from django.conf import settings
from django.db.models import Count, Exists, Q, OuterRef, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.mixins import (CreateModelMixin, DestroyModelMixin,
                                   ListModelMixin, RetrieveModelMixin,
                                   UpdateModelMixin)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from base.apps.storage.models import Crate
from base.apps.marketplace.models import MarketListedCrate
from base.apps.storage.serializers.sensors import SensorIntegrationSerializer
from base.apps.storage.services.sensors.utils import build_integration
from base.apps.storage.tasks.digital_twins import send_crate_failure_email, update_produce_crates_dts
from base.apps.user.models import Country, Farmer, Operator, ServiceProvider
from base.settings import ENVIRONMENT

from .apps import ANDROID_VERSION_CODE, IOS_VERSION_CODE
from .models import (CoolingUnit, CoolingUnitCrop, CoolingUnitPower,
                     CoolingUnitSpecifications, Crate, Crop, CropType, Location,
                     Produce, SensorIntegration)
from .serializers import (CoolingUnitCapacitySerializer,
                          CoolingUnitCropSerializer, CoolingUnitPowerSerializer,
                          CoolingUnitSerializer,
                          CoolingUnitSpecificationsSerializer, CrateSerializer,
                          CropSerializer, CropTypeSerializer,
                          LocationSerializer, ProduceSerializer)


class CropTypeViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = CropType
    serializer_class = CropTypeSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.order_by("name")


class CropViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = Crop
    serializer_class = CropSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        user = self.request.user

        # For some countries we want to filter crops only specific to them
        try:
            country = ServiceProvider.objects.get(user=user).company.country.name
        except:
            try:
                country = Operator.objects.get(user=user).company.country.name
            except:
                country = Farmer.objects.get(user=user).country

        isFilterCountry = False
        for c in Country.objects.all():
            if c.country.name == country:
                isFilterCountry = True
                break

        if isFilterCountry:
            if "crop" in self.request.data:
                return self.model.objects.filter(
                    crop_type__id=self.request.query_params.get("crop"),
                    countryRelated__country__name=country,
                ).order_by("name")
            else:
                return (
                    self.model.objects.filter(countryRelated__country__name=country)
                    .exclude(name="Other")
                    .order_by("name")
                )

        if "crop" in self.request.data:
            return self.model.objects.filter(
                crop_type__id=self.request.query_params.get("crop")
            ).order_by("name")
        else:
            return self.model.objects.all().order_by("name")


class CoolingUnitCapacityViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = CoolingUnit
    serializer_class = CoolingUnitCapacitySerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):

        if self.request.query_params.get("cooling_unit"):
            cooling_unit_id = self.request.query_params.get("cooling_unit")
            return self.model.objects.filter(id=cooling_unit_id)
        else:
            return self.model.objects.all()


class CoolingUnitViewSet(
    CreateModelMixin,
    GenericViewSet,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
):
    model = CoolingUnit
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CoolingUnitSerializer

    def get_queryset(self):
        if self.request.query_params.get("not_empty"):
            is_farmer = self.request.query_params.get("is_farmer").lower() == "true"
            if is_farmer:
                farmer = Farmer.objects.get(
                    user__id=self.request.query_params.get("user")
                )

                crates = Crate.objects.filter(
                    produce__checkin__owned_by_user__farmer=farmer,
                    weight__gt=0,
                ).distinct("cooling_unit")

                cooling_unit_ids = crates.values_list("cooling_unit", flat=True)
                cooling_units = self.model.objects.filter(id__in=cooling_unit_ids)

                if self.request.query_params.get("company"):
                    company_id = int(self.request.query_params.get("company"))
                    cooling_units = cooling_units.filter(
                        location__company__id=company_id
                    )

                return cooling_units

            if self.request.query_params.get("company"):
                return self.model.objects.filter(
                    Q(location__company_id=self.request.query_params.get("company"))
                    & Exists(
                        Crate.generate_checkedin_crates_subquery(
                            "crate_cooling_unit__produce_id"
                        )
                    )
                    & Q(deleted=False),
                ).distinct("id")
            if self.request.query_params.get("user"):
                return self.model.objects.annotate(op=Count("name")).filter(
                    op__lte=1,
                    operators=self.request.query_params.get("operator"),
                    occupancy__gt=0,
                    deleted=False,
                )
        if self.request.query_params.get("company"):
            return self.model.objects.filter(
                location__company=self.request.query_params.get("company"),
                deleted=False,
            )
        if self.request.query_params.get("operator"):
            return self.model.objects.filter(
                operators=self.request.query_params.get("operator"), deleted=False
            )
        elif self.request.query_params.get("farmer_id"):
            farmer = Farmer.objects.get(id=self.request.query_params.get("farmer_id"))
            return self.model.objects.filter(
                (Q(public=True) | Q(pk__in=farmer.cooling_units.all())), deleted=False
            )
        return self.model.objects.filter(deleted=False)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class.optimized_init(queryset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):

        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    def update(self, request, *args, **kwargs):
        instance = get_object_or_404(CoolingUnit, pk=self.kwargs.get("pk", None))
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
            instance=instance,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    def delete(self, request, *args, **kwargs):
        user = request.user
        cooling_unit_id = self.kwargs.get("pk")

        if not cooling_unit_id:
            return Response(
                {"error": "Cooling unit ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cooling_unit = get_object_or_404(CoolingUnit, id=cooling_unit_id)
        company = cooling_unit.location.company

        if not ServiceProvider.is_employee_of_company(user, company):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        if Produce.objects.filter(
            Q(crates__cooling_unit=cooling_unit)
            & Exists(Crate.generate_checkedin_crates_subquery())
        ).exists():
            return Response(
                {
                    "error": "This cooling unit cannot be deleted because it has active check-ins"
                },
                status=status.HTTP_409_CONFLICT,
            )

        cooling_unit.deleted = True
        cooling_unit.save()

        return Response(
            {"success": "Successfully deleted cooling unit"}, status=status.HTTP_200_OK
        )

    # TODO: move this to a dedicated sensor viewset when/if we implement the multiple sensors support
    @action(detail=True, methods=["GET"], url_path="sensor-data")
    def retrieve_sensor_data(self, request, *args, **kwargs):
        cooling_unit = self.get_object()

        user = request.user
        unit_company = cooling_unit.location.company

        # Check if the user is an authorized Operator or ServiceProvider for this company
        operator = Operator.objects.filter(user=user, company=unit_company).first()
        service_provider = ServiceProvider.objects.filter(
            user=user, company=unit_company
        ).first()

        if not operator and not service_provider:
            return Response(
                {
                    "error": "You do not have permission to view sensor data for this cooling unit."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Fetch the sensor data
        sensor_data = cooling_unit.sensor_user_cooling_unit.all()

        # Return the sensor data
        return Response(
            {
                "sensor_data": [
                    {
                        "id": sensor.id,
                        "source_id": sensor.source_id,
                        "type": sensor.type,
                        "username": sensor.username,
                    }
                    for sensor in sensor_data
                ]
            },
            status=status.HTTP_200_OK,
        )


class CrateViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = Crate
    serializer_class = CrateSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        if self.request.query_params.get(
            "cooling_unit"
        ) and self.request.query_params.get("farmer"):
            return self.model.objects.filter(
                cooling_unit=self.request.query_params.get("cooling_unit"),
                weight__gt=0,
                produce__checkin__owned_by_user__farmer=self.request.query_params.get(
                    "farmer"
                ),
            )
        return self.model.objects.all()


class LocationViewSet(
    RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet
):
    model = Location
    serializer_class = LocationSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if self.request.query_params.get("company"):
            return self.model.objects.filter(
                company=self.request.query_params.get("company"), deleted=False
            )
        elif self.request.query_params.get("farmer_id"):
            farmer = Farmer.objects.get(id=self.request.query_params.get("farmer_id"))
            cooling_units = CoolingUnit.objects.filter(
                (Q(public=True) | Q(pk__in=farmer.cooling_units.all())), deleted=False
            )
            cooling_units = map(lambda cu: cu.location.id, cooling_units)
            return self.model.objects.filter(pk__in=cooling_units, deleted=False)
        else:
            return self.model.objects.filter(deleted=False)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    def delete(self, request, *args, **kwargs):
        user = request.user
        location_id = self.kwargs.get("pk")

        if not location_id:
            return Response(
                {"error": "Location ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        location = get_object_or_404(Location, id=location_id)
        company = location.company

        if not ServiceProvider.is_employee_of_company(user, company):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        cooling_units = CoolingUnit.objects.filter(location=location)
        if Produce.objects.filter(
            Q(crates__cooling_unit__in=cooling_units)
            & Exists(Crate.generate_checkedin_crates_subquery())
        ).exists():
            return Response(
                {
                    "error": "This location cannot be deleted because it has cooling units with active check-ins"
                },
                status=status.HTTP_409_CONFLICT,
            )

        location.deleted = True
        location.save()
        CoolingUnit.objects.filter(location=location).update(deleted=True)

        return Response(
            {"success": "Successfully deleted location and its cooling units"},
            status=status.HTTP_200_OK,
        )


class ProduceViewSet(
    RetrieveModelMixin,
    UpdateModelMixin,
    ListModelMixin,
    GenericViewSet,
    CreateModelMixin,
):
    model = Produce
    serializer_class = ProduceSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        cooling_unit_id = self.request.query_params.get("cooling_unit")

        queryset = (
            self.model.objects.filter(
                Q(crates__cooling_unit=cooling_unit_id)
                & Exists(Crate.generate_checkedin_crates_subquery())
            )
            .distinct()
            .order_by("-checkin__movement__date")
        )

        # Define subqueries for annotations
        listed_qs = MarketListedCrate.objects.filter(
            crate_id=OuterRef('pk'),
            delisted_at__isnull=True,
        )
        locked_qs = MarketListedCrate.objects.filter(
            crate_id=OuterRef('pk'),
            delisted_at__isnull=True,
            cmp_weight_locked_in_payment_pending_orders_in_kg__gt=0,
        )

        # Annotated Crates queryset
        crates_qs = Crate.objects.filter(weight__gt=0).annotate(
            is_listed_in_the_marketplace=Exists(listed_qs),
            is_locked_within_pending_orders=Exists(locked_qs),
        ).select_related(
            "cooling_unit",
            "cooling_unit__location__company"
        ).prefetch_related(
            Prefetch(
                "cooling_unit__crop_cooling_unit",
                queryset=CoolingUnitCrop.objects.select_related("pricing", "crop"),
                to_attr="all_crop_cooling_units",
            ),
        )

        # Prefetch related fields to solve the 1+N problem
        queryset = queryset.select_related(
            "checkin__owned_by_user",
            "checkin__owned_by_user__farmer",
            "checkin__movement",
            "checkin__movement__operator",  # Added operator join
            "checkin__movement__operator__user",  # Added users operator join
            "crop",
        ).prefetch_related(
            Prefetch("crates", queryset=crates_qs),

        )

        if self.request.query_params.get("farmer_id"):
            queryset = queryset.filter(
                checkin__owned_by_user__farmer__id=self.request.query_params.get(
                    "farmer_id"
                )
            )

        return queryset


class CoolingUnitCropViewSet(
    RetrieveModelMixin,
    UpdateModelMixin,
    ListModelMixin,
    GenericViewSet,
    CreateModelMixin,
):
    model = CoolingUnitCrop
    serializer_class = CoolingUnitCropSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        company = Operator.objects.get(user=self.request.user).company
        return self.model.objects.filter(
            Q(cooling_unit__id=self.request.query_params.get("cooling_unit_id"))
            & Q(crop__crop_type__id=self.request.query_params.get("crop"))
            & Q(active=True)
            & (Q(crop__in=company.crop.all()) | Q(crop__name="Other"))
        ).order_by("crop__name")


class CoolingUnitSpecificationsViewSet(
    RetrieveModelMixin, ListModelMixin, GenericViewSet, CreateModelMixin
):
    model = CoolingUnitSpecifications
    serializer_class = CoolingUnitSpecificationsSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.filter(
            cooling_unit=self.request.query_params.get("cooling_unit"),
            datetime_stamp__gte=datetime.now() - timedelta(days=7),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)


class CoolingUnitTemperatureViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = CoolingUnitSpecifications
    serializer_class = CoolingUnitSpecificationsSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.filter(
            cooling_unit=self.request.query_params.get("cooling_unit"),
            specification_type="TEMPERATURE",
            # Filter by last 7 days
            datetime_stamp__gte=datetime.now() - timedelta(days=7),
        ).order_by("datetime_stamp")


class NextCheckoutViewSet(ListModelMixin, GenericViewSet):
    model = Produce
    serializer_class = ProduceSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        by_remaining_shelf_life = (
            self.model.objects.filter(
                Q(crates__cooling_unit=self.request.query_params.get("cooling_unit"))
                & Exists(Crate.generate_checkedin_crates_subquery())
                & ~Q(crates__modified_dt=None)
            )
            .distinct()
            .order_by("crates__remaining_shelf_life")
        )
        by_planned_days = (
            self.model.objects.filter(
                Q(crates__cooling_unit=self.request.query_params.get("cooling_unit"))
                & Exists(Crate.generate_checkedin_crates_subquery())
                & Q(crates__modified_dt=None)
                & ~Q(crates__planned_days=None)
            )
            .distinct()
            .order_by("crates__planned_days")
        )
        by_checkout = (
            self.model.objects.filter(
                Q(crates__cooling_unit=self.request.query_params.get("cooling_unit"))
                & Exists(Crate.generate_checkedin_crates_subquery())
                & Q(crates__modified_dt=None)
                & Q(crates__planned_days=None)
            )
            .distinct()
            .order_by("-checkin__movement__date")
        )
        return list(
            dict.fromkeys(
                list(chain(by_remaining_shelf_life, by_planned_days, by_checkout))
            )
        )


class EcozenViewSet(GenericViewSet):
    permission_classes = (permissions.AllowAny,)

    @action(detail=False, methods=["POST"], url_path="test-connection")
    def test_connection(self, request, *args, **kwargs):
        """
        Authenticates with Ecozen API and fetches Ecofrost temperature data.
        Expected request format:
        {
            "username": "user@mail.com",
            "password": "Hello123",
            "source_id": "12345"
        }
        """
        params = {
            "username": request.data.get("username"),
            "password": request.data.get("password"),
        }

        if not params["username"] or not params["password"]:
            return Response(
                {"error": "Username and password are required."}, status=400
            )

        login_url = "https://api.ecozen.ai/api/dashboard/auth/login/"

        login_request = requests.post(login_url, json=params)

        if login_request.status_code == 401:
            return Response({"error": "Unknown user"}, status=401)

        try:
            access_token = login_request.json().get("accessToken")
        except ValueError:
            return Response({"error": "Invalid response from Ecozen API"}, status=500)

        if not access_token:
            return Response(
                {"error": "Authentication failed, no access token received"}, status=401
            )

        # Fetch temperature data
        room_headers = {"Authorization": f"Bearer {access_token}"}
        data_url = "https://api.ecozen.ai/api/dashboard/ecofrost/graph/"
        today = datetime.today().strftime("%Y/%m/%d")
        body = {"from": today, "to": today, "paramList": "Room_1_T, Set_T"}

        machine_id = request.data.get("source_id")
        if not machine_id:
            return Response({"error": "Machine ID is required."}, status=400)

        response = requests.post(data_url + machine_id, headers=room_headers, json=body)

        if response.status_code in [200, 201]:
            return Response({"success": "Successfully connected"}, status=200)
        elif response.status_code == 401:
            return Response({"error": "Unknown Machine ID"}, status=404)
        else:
            return Response({"error": "Unknown Error"}, status=400)


class MobileAppMinimumVersionCodesViewSet(ViewSet):
    """
    ViewSet to get the latest version code per platform.

    * Any authenticated user is able to access this view.
    """

    permission_classes = (permissions.AllowAny,)

    @action(methods=["GET"], url_path="android", detail=False)
    def android(self, request):
        return Response(ANDROID_VERSION_CODE)

    @action(methods=["GET"], url_path="ios", detail=False)
    def ios(self, request):
        return Response(IOS_VERSION_CODE)


class CoolingUnitPowerViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    model = CoolingUnitPower
    serializer_class = CoolingUnitPowerSerializer
    permission_classes = (permissions.AllowAny,)


class SensorIntegrationViewSet(GenericViewSet, CreateModelMixin, DestroyModelMixin):
    model = SensorIntegration
    permission_classes = (permissions.AllowAny,)

    @action(detail=False, methods=["POST"], url_path="sources")
    def list_sources(self, request, *args, **kwargs):
        """
        Tests credentials and returns available sources.
        Expected request format:
        {
            "integration_type": "figorr",
            "username": "user@mail.com",
            "password": "Hello123"
        }
        """

        integration_type = request.data.get("integration_type")
        username = request.data.get("username")
        password = request.data.get("password")

        if not integration_type or not username or not password:
            return Response(
                {"error": "Missing required fields (integration, username, password)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        credentials = {
            "username": username,
            "password": password,
            "type": integration_type,
        }
        integration = build_integration(None, credentials)

        if not integration:
            return Response(
                {"error": "Invalid integration type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            integration.authorize()
        except Exception as e:
            return Response(
                {"error": f"Authentication failed: {str(e)}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            raw_sources = integration.list_sources()

            serializer = SensorIntegrationSerializer(data=raw_sources, many=True)

            if serializer.is_valid():
                return Response({"sources": serializer.data}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "Invalid data format from integration"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve sources: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        user = self.request.user

        try:
            sensor = self.model.objects.get(id=kwargs.get("pk"))
        except:
            return Response({"error": "DOES NOT EXIST"}, status=400)

        if not user.service_provider or not (
            sensor.cooling_unit.location.company == user.service_provider.company
        ):
            return Response({"error": "CANNOT PERFORM OPERATION"}, status=400)

        # delete the sensor passed in
        sensor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ComsolCallbackViewSet(ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["post"], url_path="callback")
    def callback(self, request, *args, **kwargs):
        """
        POST /storage/v1/comsol/callback
        Requires header: X-Comsol-Callback-Key: <API_KEY>
        """
        auth_header = request.headers.get("X-Comsol-Callback-Key")

        if not auth_header or auth_header != settings.COMSOL_CALLBACK_KEY:
            return Response(
                {"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
            )

        print("COMSOL DT Resulting Callback received:", request.data)

        if request.data.get("error"):
            try:
                crate_id = request.data.get("crate_id")
                crate = Crate.objects.filter(id=crate_id).first()

                if ENVIRONMENT in ("development", "e2e"):
                    print(f"Skipping sending recomputation failure email for crate {crate.id}.")
                else:
                    send_crate_failure_email(crate)
                return Response({"status": "success"}, status=status.HTTP_200_OK)
            except Crate.DoesNotExist:
                return Response(
                    {"error": "Crate not found"}, status=status.HTTP_404_NOT_FOUND
                )

        outputs = request.data.get("outputs", {})
        crate_id = request.data.get("crate_id")
        shelf_life = outputs.get("shelf_life")
        quality_dt = outputs.get("quality_dt")
        temperature_dt = outputs.get("temperature_dt")

        if (
            crate_id is None
            or shelf_life is None
            or quality_dt is None
            or temperature_dt is None
        ):
            return Response(
                {"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST
            )

        crate = get_object_or_404(Crate, id=crate_id)

        try:
            update_produce_crates_dts(crate.produce_id, temperature_dt, quality_dt, shelf_life)
        except Crate.DoesNotExist:
            return Response(
                {"error": "Crate not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response({"status": "success"}, status=status.HTTP_200_OK)
