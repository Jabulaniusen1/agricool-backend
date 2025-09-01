import datetime

from rest_framework import serializers

from base.apps.operation.models import (
    MarketSurvey,
    MarketsurveyCheckout,
    MarketsurveyPreprocessing,
)
from base.apps.prediction.models import Market


class MarketSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketSurvey
        fields = "__all__"

    def validate(self, data):

        request = self.context["request"]

        market_survey_filled = MarketSurvey.objects.filter(
            crop=request.data["crop"],
            marketsurveycheckout_market_survey__checkout=request.data["checkout"],
        ).exists()

        if market_survey_filled:
            raise serializers.ValidationError(
                "Market survey already filled for this checkout and crop"
            )

        has_been_preprocessed = MarketsurveyPreprocessing.objects.filter(
            checkout=request.data["checkout"],
            crop=request.data["crop"],
        ).exists()

        if not has_been_preprocessed:
            raise serializers.ValidationError(
                "Market survey unavailable for this checkout"
            )

        # TODO: if in Nigeria, get state data instead of market
        if "local_market" in request.data and request.data["local_market"] is not None:
            local_market = request.data.pop("local_market")
            target_market = Market.objects.filter(
                name=local_market["market"], state__name=local_market["state"]
            )
            if not target_market.exists():
                raise serializers.ValidationError(
                    "Market not found, please register it"
                )
            data["market"] = target_market.first()

        return data

    def create(self, validated_data):

        market_survey = MarketSurvey.objects.create(
            **validated_data, date_filled_in=datetime.datetime.now().astimezone()
        )

        self.attach_to_similar_crops(market_survey, validated_data["checkout"])

        return market_survey

    def attach_to_similar_crops(self, markey_survey, checkout):

        current = MarketsurveyPreprocessing.objects.filter(
            checkout=checkout, crop=markey_survey.crop
        ).first()

        valid_checkouts = MarketsurveyPreprocessing.objects.filter(
            crop=current.crop,
            farmer=current.farmer,
            operator=current.operator,
            is_active=True,
        ).distinct("checkout")

        for i in valid_checkouts:
            MarketsurveyCheckout.objects.create(
                checkout=i.checkout, marketsurvey=markey_survey
            )
