import datetime
import json

from django.forms import model_to_dict
from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.views import APIView

from base.apps.prediction.models import Market, MLPredictionData


class PredictionsDataTableAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):

        params = json.loads(request.body)
        predictions_array = []
        today = datetime.date.today()

        for marketId in params["marketsIds"]:
            market = None
            latest_prediction_dict = {}

            try:
                market = Market.objects.get(id=marketId)
            except:
                continue

            try:
                latest_prediction_dict = model_to_dict(
                    MLPredictionData.objects.filter(
                        market=market, crop=params["cropId"]
                    ).latest("reference_date")
                )
            except:
                latest_prediction_dict["reference_date"] = today

            for day in params["days"]:
                day = datetime.datetime.strptime(day, "%Y-%m-%d").date()
                if (day - today).days < 0:
                    continue
                days_difference = (day - latest_prediction_dict["reference_date"]).days
                forecast_key = "price_forecast_{}".format(days_difference)
                price = None
                if forecast_key in latest_prediction_dict:
                    price = round(latest_prediction_dict[forecast_key], 2)

                predictions_array.append(
                    {
                        "market": "{} / {} / {}".format(
                            market.name, market.district, market.state.name
                        ),
                        "date": day.strftime("%b, %d"),
                        "price": price,
                    }
                )

        return JsonResponse(predictions_array, safe=False)
