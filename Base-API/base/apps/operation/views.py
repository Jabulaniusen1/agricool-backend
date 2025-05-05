import json
from rest_framework import status, permissions
from rest_framework.decorators import action
from datetime import datetime
import random, string
from datetime import date
from django.db import connection
from django.db.models import F, Q, Exists, OuterRef, Count, Subquery, Case, When, IntegerField
from django.shortcuts import render, get_object_or_404
from .models import Checkin, Movement, Checkout, MarketSurvey
from base.apps.storage.models import Crate, Produce, Crop, CoolingUnit, CoolingUnitCrop
from base.apps.user.models import Farmer
from base.apps.storage.serializers import CrateSerializer
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.viewsets import (
    GenericViewSet,
    ViewSet,
)
from rest_framework.response import Response

from .serializers import (
    CheckinSerializer,
    MovementSerializer,
    CheckoutSerializer,
    MarketSurveySerializer,
)

from rest_framework.exceptions import ValidationError
from rest_framework.status import HTTP_403_FORBIDDEN
from base.apps.user.models import Operator, ServiceProvider, Notification
from base.celery import app
from base.apps.operation.models import MarketsurveyPreprocessing, MarketsurveyCheckout


class CheckinViewSet(
    RetrieveModelMixin, ListModelMixin, CreateModelMixin, GenericViewSet
):
    model = Checkin
    serializer_class = CheckinSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.all()

    def create(self, request, *args, **kwargs):
        request_data = request.data.copy()

        if request_data["farmer_id"] is not None:
            request_data["farmer"] = request_data["farmer_id"]
            farmer = get_object_or_404(Farmer, id=request_data["farmer_id"])
            request_data["owned_by_user"] = farmer.user_id
        elif request_data["owned_by_user_id"] is not None:
            request_data["owned_by_user"] = request_data["owned_by_user_id"]
            request_data["owned_on_behalf_of_company"] = request_data["owned_on_behalf_of_company_id"]

        if not request_data["owned_by_user"]:
            return Response({'error': "Please pass on the 'owned_by_user_id' and optionally the 'on_behalf_of_company_id'"}, status=HTTP_400_BAD_REQUEST)

        code = Movement.generate_code()
        movement_date = date.today()
        movement_instance = Movement.objects.create(
            code=code,
            date=movement_date,
            operator=Operator.objects.get(user_id=request.user.id),
            initiated_for=Movement.InitiatedFor.CHECK_IN,
        )
        request_data["movement"] = movement_instance.id

        produces = json.loads(request_data["produces"])

        cooling_unit = CoolingUnit.objects.get(
            id=produces[0]["crates"][0]["cooling_unit_id"]
        )

        serializer = self.serializer_class(data=request_data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save()
        cooling_unit.compute(save=True)
        return Response(serializer.data, status=200)

    def update(self, request, *args, **kwargs):
        produce = get_object_or_404(Produce, pk=self.kwargs.get("pk"))
        if not produce:
            return Response({'error': 'No produce found'}, status=404)

        checkin = Checkin.objects.filter(id=produce.checkin_id).first()
        crate = Crate.objects.filter(produce=produce).first()

        if not crate or not checkin:
            return Response({'error': 'No check in / crate found'}, status=404)

        print("check id, crate and produce id", checkin.id, produce.id, crate.id)

        cooling_unit = CoolingUnit.objects.get(id=crate.cooling_unit_id)
        movement_date = checkin.movement.date if checkin.movement else None

        if cooling_unit.editable_checkins and movement_date.date() == datetime.today().date():
            if request.data.get('farmer_id'):
                farmer = Farmer.objects.get(id=request.data.get('farmer_id'))
                checkin.owned_by_user_id = farmer.user_id
                checkin.save()

            produce.crop_id = request.data.get('crop_id', produce.crop_id)
            produce.save()

            Crate.objects.filter(produce=produce).update(
                planned_days=request.data.get('planned_days', crate.planned_days))
        else:
            print(
                f'coolingUnitEditable: {cooling_unit.editable_checkins}, {movement_date.date()} {datetime.today().date()}')
            return Response({'error': f'Check in is not editable.'}, status=400)

        # send a message to all the REs of the cooling unit about the update.
        service_providers = ServiceProvider.objects.filter(company=cooling_unit.location.company)
        for sp in service_providers:
            Notification.objects.create(
                user=sp.user, specific_id=checkin.id, event_type="CHECKIN_EDITED"
            )
        return Response({'success': 'Check in updated successfully'})


class MovementViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = Movement
    serializer_class = MovementSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        cooling_unit_id = self.request.query_params.get("cooling_unit")
        farmer_id = self.request.query_params.get("farmer_id")
        owned_by_user_id = self.request.query_params.get("owned_by_user_id")

        queryset = self.model.objects.all()

        if cooling_unit_id:
            queryset = queryset.filter(
                Q(checkins__produces__crates__cooling_unit=cooling_unit_id) |
                Q(checkouts__partial_checkouts__crate__cooling_unit=cooling_unit_id)
            )

        if farmer_id:
            queryset = queryset.filter(
                Q(checkins__owned_by_user__farmer__id=farmer_id) |
                Q(checkouts__partial_checkouts__crate__produce__checkin__owned_by_user__farmer__id=farmer_id)
            )

        if owned_by_user_id:
            queryset = queryset.filter(
                Q(checkins__owned_by_user_id=owned_by_user_id) |
                Q(checkouts__partial_checkouts__crate__produce__checkin__owned_by_user_id=owned_by_user_id)
            )

        return (
            queryset
            .order_by('-date')
            .distinct()
        )

    def list(self, request, *args, **kwargs):
        serializer = MovementSerializer.optimized_init(self.get_queryset())
        return Response(serializer.data, status=200)

    @action(detail=False, methods=["get"], url_path="revenue")
    def get_checkouts_revenue(self, request, *args, **kwargs):
        cooling_units = self.request.query_params.get("cooling_units", "").split(",")
        payment_methods = self.request.query_params.get("payment_methods", "").split(",")

        serializer = MovementSerializer.optimized_init((
            self.model.objects.all()
            .filter(
                Q(checkouts__partial_checkouts__crate__cooling_unit__in=cooling_units) & Q(checkouts__payment_method__in=payment_methods)
            )
            .order_by('-date')
            .distinct()
        ))

        return Response(serializer.data, status=200)

    @action(detail=False, methods=["get"], url_path="usage")
    def get_checkouts_usage(self, request, *args, **kwargs):
        cooling_units = self.request.query_params.get("cooling_units", "").split(",")
        serializer = MovementSerializer.optimized_init((
            self.model.objects.filter(
                Q(checkins__produces__crates__cooling_unit__in=cooling_units)
            )
        ))

        return Response(serializer.data, status=200)



class CheckoutViewSet(ListModelMixin, CreateModelMixin, GenericViewSet):
    model = Checkout
    serializer_class = CheckoutSerializer
    permission_classes = (permissions.AllowAny,)
    # use the movement_id instead of code
    lookup_field = 'movement_id'

    def get_queryset(self):
        code = self.request.query_params.get("code")

        if code:
            try:
                checkout = self.model.objects.get(movement__code=code)
                crates = Crate.objects.filter(partial_checkouts__checkout_id=checkout.id)
                return crates
            except:
                return None
        else:
            return self.model.objects.all()

    def create(self, request, *args, **kwargs):
        request_data = request.data.copy()

        code = Movement.generate_code()
        movement_date = date.today()
        operator = Operator.objects.get(user_id=self.request.user.id)
        movement_instance = Movement.objects.create(
            code=code, date=movement_date, operator=operator,
            initiated_for=Movement.InitiatedFor.CHECK_OUT,
        )
        request_data["movement"] = movement_instance.id

        serializer = self.serializer_class(data=request_data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save()
        return Response(serializer.data, status=200)

    @action(detail=True, methods=["POST"], url_path="send_sms_report")
    def send_sms_report(self, request, movement_id=None):
        """ GET /operation/checkouts/:movement_id/send_sms_report - sends an SMS report to a user """

        checkout = get_object_or_404(Checkout, movement_id=movement_id)
        app.send_task("base.apps.operation.tasks.sms.send_sms_checkout_movement_report", args=[checkout.id, request.user.id])

        return Response(status=200)

class CheckoutToCheckinViewSet(ListModelMixin, CreateModelMixin, GenericViewSet):
    model = Crate
    serializer_class = CrateSerializer

    def list(self, request):
        code = self.request.query_params.get("code")

        if code:
            try:
                movement = Movement.objects.get(code=code, used_for_checkin=False)
                checkout = Checkout.objects.get(movement=movement)
                crates = Crate.objects.filter(partial_checkouts__checkout_id=checkout.id)

                # Fix:
                # This is a temporary fix and could later be changed with a more appropriate solution
                # The crate doesn't have a reference for the latest checkout weight
                # The crate's weight determines its current weight, and the initial weight is the weight of the crate when it was checked in
                # But in the meantime, there could have been several partial checkouts that caused the weight to change over time.ArithmeticError
                # We're only interested to gather the latest checkout weight, so we will be patching this value just for the read aspect of it
                for crate in crates:
                    latest_crate_partial_checkout = crate.partial_checkouts.latest('id')
                    weight_to_be_considered_in_kg = latest_crate_partial_checkout.weight_in_kg if latest_crate_partial_checkout else crate.initial_weight

                    crate.weight = weight_to_be_considered_in_kg
                    crate.initial_weight = weight_to_be_considered_in_kg

                serializer = CrateSerializer(crates, many=True)
                return Response(serializer.data)
            except:
                return Response(
                    {"message": "This code has already been used for a check in."},
                    status=404,
                )
        else:
            return None

    def create(self, request, *args, **kwargs):
        code = request.data["params"]["code"]
        cooling_unit_id = request.data["params"]["coolingUnitId"]
        days = (
            request.data["params"].get("days", None)
        )
        tags = (
            request.data["params"].get("tags", [])
        )
        checkout = Checkout.objects.filter(movement__code=code)[0]
        crates = Crate.objects.filter(partial_checkouts__checkout_id=checkout.id)

        code = Movement.generate_code()

        if request.data["params"]["farmer"]:
            farmer = get_object_or_404(Farmer, id=request.data["params"]["farmer"])
            request_data = {"owned_by_user_id": farmer.user_id}
        else:
            request_data = {"owned_by_user_id": request.data["params"]["owned_by_user"]}

        movement_date = date.today()
        movement_instance = Movement.objects.create(
            code=code,
            date=movement_date,
            operator=Operator.objects.get(user_id=request.user.id),
            initiated_for=Movement.InitiatedFor.CHECK_IN,
        )
        request_data["movement"] = movement_instance

        checkin_instance = Checkin.objects.create(**request_data)
        produces = []

        # as we are in check in, better to take the cooling unit from the request and use it!
        cooling_unit = CoolingUnit.objects.get(id=cooling_unit_id)

        for c in crates:
            if c.produce.id not in produces:
                produces.append(c.produce.id)

        for produceId in produces:
            produce = Produce.objects.get(id=produceId)
            crop = Crop.objects.get(id=produce.crop.id)
            produce_object = {
                "harvest_date": produce.harvest_date,
                "initial_grade": produce.initial_grade,
                "size": produce.size,
            }

            produce_instance = Produce.objects.create(
                **produce_object, crop=crop, checkin=checkin_instance
            )

            for i, crate in enumerate(crates):
                if crate.produce.id == produce.id:
                    price = 0

                    # calculates pricing based on cooling unit pricing and crop type price
                    if not CoolingUnitCrop.objects.filter(
                            cooling_unit_id=cooling_unit_id, crop=crop, active=True
                    ):
                        return Response(
                            {
                                "message": "This cooling unit doesnt accept this type of produce"
                            },
                            status=404,
                        )

                    cup_crop = CoolingUnitCrop.objects.get(
                        cooling_unit_id=cooling_unit_id, crop=crop
                    )
                    metric_multiplier = (
                        crate.weight if cooling_unit.metric == "KILOGRAMS" else 1
                    )
                    if cup_crop.pricing.pricing_type == "FIXED":
                        price += metric_multiplier * cup_crop.pricing.fixed_rate
                    elif (
                            days
                            and int(days) > 0
                            and (cup_crop.pricing.pricing_type == "PERIODICITY")
                    ):
                        price += (
                                metric_multiplier * int(days) * cup_crop.pricing.daily_rate
                        )

                    try:
                        tag_value = tags[i] if tags[i] else None
                    except IndexError:
                        tag_value = None

                    latest_crate_partial_checkout = crate.partial_checkouts.latest('id')
                    weight_to_be_considered_in_kg = latest_crate_partial_checkout.weight_in_kg if latest_crate_partial_checkout else crate.initial_weight

                    Crate.objects.create(
                        # Operation
                        produce=produce_instance,
                        cooling_unit=cooling_unit,
                        price_per_crate_per_pricing_type=price,
                        currency=crate.currency,
                        planned_days=days,
                        tag=tag_value,

                        # Weight
                        weight=weight_to_be_considered_in_kg,
                        initial_weight=weight_to_be_considered_in_kg,

                        # Quality
                        remaining_shelf_life=crate.remaining_shelf_life,
                        quality_dt=crate.quality_dt,
                        temperature_dt=crate.temperature_dt,
                        modified_dt=crate.modified_dt,
                    )

                # THERESA check if oos still works here or we need to define
                # if ((crop.digital_twin_identifier) and (cooling_unit.location.company.digital_twin is True)):
                #   run_digital_twin.delay(produce_instance.id, crate.id)

        Movement.objects.filter(id=checkout.movement_id).update(used_for_checkin=True)
        cooling_unit.compute(save=True)

        return Response({"message": "Successfully moved crate"}, status=200)


class MarketSurveyViewSet(
    RetrieveModelMixin, ListModelMixin, GenericViewSet, CreateModelMixin
):
    model = MarketSurvey
    serializer_class = MarketSurveySerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.all()

    def create(self, request, *args, **kwargs):
        data = request.data
        temp = data["reason_for_loss"]

        if data["reason_for_loss"] and isinstance(data["reason_for_loss"], list):
            temp = data["reason_for_loss"]
            data["reason_for_loss"] = "other"

        serializer = self.serializer_class(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save(reason_for_loss=temp)
        return Response(serializer.data, status=200)
