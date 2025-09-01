import datetime
import json

from django.db.models import F
from django.forms import model_to_dict
from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.views import APIView

from base.apps.prediction.models import MLMarketDataIndia, MLPredictionData


class PredictionsDataGraphAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        # Get request details and set today's date, past days of 28 and future forecast days of 14
        params = json.loads(request.body)
        today = datetime.date.today()

        NUMBER_OF_PAST_DAYS = 28
        NUMBER_OF_FORECASTS_DAYS = 14

        ########################################### PAST ##########################################
        # get the values from DB from the past starting date till date. In ML4, this should be past starting month till date
        past_starting_date = today - datetime.timedelta(days=NUMBER_OF_PAST_DAYS)

        past_values = MLMarketDataIndia.objects.filter(
            date__gte=past_starting_date,
            market=params["marketId"],
            crop=params["cropId"],
        ).values("date", price=F("modal_price_rs_per_quintal"))
        past_values_array = []

        for i in range(NUMBER_OF_PAST_DAYS):

            lookup_date = past_starting_date + datetime.timedelta(days=i)

            found = False
            # loop through found past values date by date and append the value to past value array, if not found, append price of None to it.
            for value in past_values:
                if value["date"] == lookup_date:
                    past_values_array.append(value)
                    found = True
                    break

            if not found:
                past_values_array.append({"date": lookup_date, "price": None})

        ######################################## PAST END #########################################

        ######################################## FORECASTS ########################################

        predictions = MLPredictionData.objects.filter(
            market=params["marketId"], crop=params["cropId"]
        )

        # Converting to dict to allow fetching a property with a dynamicaly-built key
        latest_prediction_dict = {}
        predictions_array = []

        try:
            latest_prediction_dict = model_to_dict(predictions.latest("reference_date"))
        except:
            # If there is no predictions for a given market-commodity combination, replace by empty values
            latest_prediction_dict["reference_date"] = today

        days_difference = (today - latest_prediction_dict["reference_date"]).days

        # Structure the predictions in a way the graph can use.
        for i in range(NUMBER_OF_FORECASTS_DAYS):
            forecast_key = "price_forecast_{}".format(i + days_difference)
            price = None
            only_interpolated_data = None

            if forecast_key in latest_prediction_dict:
                price = latest_prediction_dict[forecast_key]
            # TODO: confirm this interpolated data piece doesn't reset the price tozero
            if only_interpolated_data in latest_prediction_dict:
                price = latest_prediction_dict["only_interpolated_data"]

            predictions_array.append(
                {
                    "date": today + datetime.timedelta(days=i),
                    "price": price,
                    "only_interpolated_data": only_interpolated_data,
                }
            )

        ###################################### FORECASTS END ######################################

        only_null_values = True
        for obj in past_values_array + predictions_array:
            if obj["price"] != None:
                only_null_values = False
                break

        if only_null_values:
            return JsonResponse(
                {
                    "details": "No data found for this combination of market and commodity"
                },
                status=204,
            )

        return JsonResponse(
            {"pastValues": past_values_array, "forecastsValues": predictions_array},
            safe=False,
        )
