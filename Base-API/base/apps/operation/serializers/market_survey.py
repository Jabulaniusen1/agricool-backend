import datetime

from rest_framework import serializers

from base.apps.operation.models import (
    MarketSurvey,
    MarketsurveyCheckout,
    MarketsurveyPreprocessing,
)
from base.apps.prediction.models import Market

# Constants
ERROR_MARKET_SURVEY_ALREADY_FILLED = "Market survey already filled for this checkout and crop"
ERROR_MARKET_SURVEY_UNAVAILABLE = "Market survey unavailable for this checkout"
ERROR_MARKET_NOT_FOUND = "Market not found, please register it"


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
            raise serializers.ValidationError(ERROR_MARKET_SURVEY_ALREADY_FILLED)

        has_been_preprocessed = MarketsurveyPreprocessing.objects.filter(
            checkout=request.data["checkout"],
            crop=request.data["crop"],
        ).exists()

        if not has_been_preprocessed:
            raise serializers.ValidationError(ERROR_MARKET_SURVEY_UNAVAILABLE)

        # TODO: if in Nigeria, get state data instead of market
        if "local_market" in request.data and request.data["local_market"] is not None:
            local_market = request.data.pop("local_market")
            target_market = Market.objects.filter(
                name=local_market["market"], state__name=local_market["state"]
            )
            if not target_market.exists():
                raise serializers.ValidationError(ERROR_MARKET_NOT_FOUND)
            data["market"] = target_market.first()

        return data

    def create(self, validated_data):

        market_survey = MarketSurvey.objects.create(
            **validated_data, date_filled_in=datetime.datetime.now().astimezone()
        )

        self.attach_to_similar_crops(market_survey, validated_data["checkout"])

        return market_survey

    def attach_to_similar_crops(self, market_survey, checkout):

        current = MarketsurveyPreprocessing.objects.filter(
            checkout=checkout, crop=market_survey.crop
        ).first()

        valid_checkouts = MarketsurveyPreprocessing.objects.filter(
            crop=current.crop,
            farmer=current.farmer,
            operator=current.operator,
            is_active=True,
        ).distinct("checkout")

        for preprocessing in valid_checkouts:
            MarketsurveyCheckout.objects.create(
                checkout=preprocessing.checkout, market_survey=market_survey
            )
