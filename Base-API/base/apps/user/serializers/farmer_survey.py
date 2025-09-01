from datetime import datetime

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from base.apps.user.models import FarmerSurvey, FarmerSurveyCommodity


class FarmerSurveySerializer(serializers.ModelSerializer):
    co = serializers.SerializerMethodField()

    class Meta:
        model = FarmerSurvey
        fields = "__all__"

    def create(self, validated_data):
        commodities = self.context["commodities"]

        farmer_survey_instance = FarmerSurvey.objects.create(
            **validated_data,
            date_filled_in=datetime.now().astimezone(),
            date_last_modified=datetime.now().astimezone(),
        )
        for crop_item in commodities:
            if crop_item["crop_id"] != "":
                FarmerSurveyCommodity.objects.create(
                    farmer_survey_id=farmer_survey_instance.id,
                    crop_id=crop_item["crop_id"],
                    average_price=crop_item["average_price"],
                    unit=crop_item["unit"],
                    reason_for_loss=crop_item["reason_for_loss"],
                    kg_in_unit=crop_item["kg_in_unit"],
                    quantity_total=crop_item["quantity_total"],
                    quantity_self_consumed=crop_item["quantity_self_consumed"],
                    quantity_sold=crop_item["quantity_sold"],
                    quantity_below_market_price=crop_item[
                        "quantity_below_market_price"
                    ],
                    average_season_in_months=crop_item["average_season_in_months"],
                    currency=crop_item["currency"],
                    date_filled_in=datetime.now().astimezone(),
                    date_last_modified=datetime.now().astimezone(),
                )
        return farmer_survey_instance

    def get_co(self, instance):
        co = FarmerSurveyCommodity.objects.filter(farmer_survey=instance.id).values()
        return co


class FarmerSurveyCommoditySerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerSurveyCommodity
        fields = "__all__"
