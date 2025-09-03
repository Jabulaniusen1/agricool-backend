from django.db.models import Count, Exists, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import CoolingUnit, Crate, Produce
from base.apps.storage.serializers import CoolingUnitSerializer
from base.apps.user.models import Farmer, Operator, ServiceProvider

# Default values
DEFAULT_WEIGHT_THRESHOLD = 0
DEFAULT_OCCUPANCY_THRESHOLD = 0
DEFAULT_DELETED = False
DEFAULT_PUBLIC = True

# Error messages
ERROR_COOLING_UNIT_ID_REQUIRED = "Cooling unit ID is required"
ERROR_ACCESS_DENIED = "Access denied"
ERROR_CANNOT_DELETE_ACTIVE_CHECKINS = "This cooling unit cannot be deleted because it has active check-ins"
ERROR_NO_PERMISSION_SENSOR_DATA = "You do not have permission to view sensor data for this cooling unit."

# Success messages
SUCCESS_DELETED_COOLING_UNIT = "Successfully deleted cooling unit"


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
            is_farmer_param = self.request.query_params.get("is_farmer")
            is_farmer = is_farmer_param and is_farmer_param.lower() == "true"
            if is_farmer:
                try:
                    farmer = Farmer.objects.get(
                        user__id=self.request.query_params.get("user")
                    )
                except Farmer.DoesNotExist:
                    return CoolingUnit.objects.none()

                crates = Crate.objects.filter(
                    produce__checkin__owned_by_user__farmer=farmer,
                    weight__gt=DEFAULT_WEIGHT_THRESHOLD,
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
                    occupancy__gt=DEFAULT_OCCUPANCY_THRESHOLD,
                    deleted=DEFAULT_DELETED,
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
            try:
                farmer = Farmer.objects.get(id=self.request.query_params.get("farmer_id"))
            except Farmer.DoesNotExist:
                return CoolingUnit.objects.none()
            return self.model.objects.filter(
                (Q(public=DEFAULT_PUBLIC) | Q(pk__in=farmer.cooling_units.all())), deleted=DEFAULT_DELETED
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
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        user = request.user
        cooling_unit_id = self.kwargs.get("pk")

        if not cooling_unit_id:
            return Response(
                {"error": ERROR_COOLING_UNIT_ID_REQUIRED},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cooling_unit = get_object_or_404(CoolingUnit, id=cooling_unit_id)
        company = cooling_unit.location.company

        if not ServiceProvider.is_employee_of_company(user, company):
            return Response(
                {"error": ERROR_ACCESS_DENIED}, status=status.HTTP_403_FORBIDDEN
            )

        if Produce.objects.filter(
            Q(crates__cooling_unit=cooling_unit)
            & Exists(Crate.generate_checkedin_crates_subquery())
        ).exists():
            return Response(
                {
                    "error": ERROR_CANNOT_DELETE_ACTIVE_CHECKINS
                },
                status=status.HTTP_409_CONFLICT,
            )

        cooling_unit.deleted = True
        cooling_unit.save()

        return Response(
            {"success": SUCCESS_DELETED_COOLING_UNIT}, status=status.HTTP_200_OK
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
                    "error": ERROR_NO_PERMISSION_SENSOR_DATA
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
                        "date_sensor_first_linked": sensor.date_sensor_first_linked,
                    }
                    for sensor in sensor_data
                ]
            },
            status=status.HTTP_200_OK,
        )
