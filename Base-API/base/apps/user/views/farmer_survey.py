from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.user.models import Farmer, FarmerSurvey, FarmerSurveyCommodity, Operator
from base.apps.user.serializers.farmer_survey import FarmerSurveySerializer


class FarmerSurveyViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    model = FarmerSurvey
    serializer_class = FarmerSurveySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            raise AuthenticationFailed("Authentication credentials were not provided.")

        farmer_id = self.request.query_params.get("farmer_id")

        try:
            farmer = Farmer.objects.get(id=farmer_id)
        except ObjectDoesNotExist:
            farmer = None

        if farmer and farmer.user == user:
            return self.model.objects.filter(farmer=farmer)

        if Operator.objects.filter(user=user).exists():
            operator = Operator.objects.get(user=user)
            company_id = operator.company_id

            if farmer and farmer.companies.filter(id=company_id).exists():
                return self.model.objects.filter(farmer=farmer)
        raise AuthenticationFailed("You are not authorized to view this survey.")

    def create(self, request, *args, **kwargs):

        serializer = self.serializer_class(
            data=request.data,
            context={"request": request, "commodities": request.data["commodities"]},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data, status=200)

    def update(self, request, *args, **kwargs):
        data = request.data
        farmer = Farmer.objects.get(id=request.data["farmer"])
        experience = True if data["experience"] == "yes" else False
        instance = FarmerSurvey.objects.filter(farmer=farmer).first()
        if instance:
            FarmerSurvey.objects.filter(farmer=farmer).update(
                user_type=data["user_type"],
                experience=experience,
                experience_duration=data["experience_duration"],
                date_last_modified=datetime.now().astimezone(),
            )
        else:
            instance = FarmerSurvey.objects.create(
                farmer=farmer,
                user_type=data["user_type"],
                experience=experience,
                experience_duration=data["experience_duration"],
                date_filled_in=datetime.now().astimezone(),
                date_last_modified=datetime.now().astimezone(),
            )

        existing_commodities = list(
            FarmerSurveyCommodity.objects.filter(farmer_survey=instance.id).values(
                "crop_id", "date_filled_in"
            )
        )
        FarmerSurveyCommodity.objects.filter(farmer_survey=instance.id).delete()
        for crop_item in data["commodities"]:
            if crop_item["crop_id"] != "":
                old_commodity_date = next(
                    (
                        co["date_filled_in"]
                        for co in existing_commodities
                        if co["crop_id"] == crop_item["crop_id"]
                    ),
                    False,
                )
                FarmerSurveyCommodity.objects.create(
                    farmer_survey_id=instance.id,
                    crop_id=crop_item["crop_id"],
                    average_price=crop_item["average_price"],
                    unit=crop_item["unit"],
                    kg_in_unit=crop_item["kg_in_unit"],
                    reason_for_loss=crop_item["reason_for_loss"],
                    quantity_total=crop_item["quantity_total"],
                    quantity_self_consumed=crop_item["quantity_self_consumed"],
                    quantity_sold=crop_item["quantity_sold"],
                    quantity_below_market_price=crop_item[
                        "quantity_below_market_price"
                    ],
                    average_season_in_months=crop_item["average_season_in_months"],
                    currency=crop_item["currency"],
                    date_filled_in=(
                        old_commodity_date
                        if old_commodity_date
                        else datetime.now().astimezone()
                    ),
                    date_last_modified=datetime.now().astimezone(),
                )

        return Response(
            FarmerSurvey.objects.filter(farmer__id=request.data["farmer"]).values(),
            status=200,
        )
