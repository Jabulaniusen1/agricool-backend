import datetime
import json

from dateutil.relativedelta import relativedelta
from django.forms import model_to_dict
from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.views import APIView

from base.apps.prediction.models import MLMarketDataNigeria, MLPredictionDataNg


class PredictionsDataGraphAPIViewNg(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        # Get request details and set today's date, past days of 28 and future forecast days of 14
        params = json.loads(request.body)
        # NOTE - CHANGING TO FIRST DAY OF THE MONTH FOR THE CALCULATION TO MAKE SENSE!!!
        first_day_of_month = datetime.date.today().replace(day=1)

        NUMBER_OF_PAST_MONTHS = 16
        NUMBER_OF_FORECASTS_MONTHS = 8

        ########################################### PAST ##########################################
        # get the values from DB from the past starting date till date. In ML4, this should be past starting month till date
        past_starting_date = first_day_of_month - relativedelta(
            months=NUMBER_OF_PAST_MONTHS
        )

        print(f"starting date {past_starting_date} - {first_day_of_month}")
        past_values = MLMarketDataNigeria.objects.filter(
            date__gte=past_starting_date, state=params["stateId"], crop=params["cropId"]
        ).values("date", "price")
        past_values_array = []

        for i in range(NUMBER_OF_PAST_MONTHS):
            lookup_date = past_starting_date + relativedelta(months=i)

            found = False
            # loop through found past values date by date and append the value to past value array, if not found, append price of None to it.
            for value in past_values:
                if (
                    value["date"].year == lookup_date.year
                    and value["date"].month == lookup_date.month
                ):
                    past_values_array.append(value)
                    found = True
                    break

            if not found:
                past_values_array.append({"date": lookup_date, "price": None})

        ######################################## PAST END #########################################

        ######################################## FORECASTS ########################################

        predictions = MLPredictionDataNg.objects.filter(
            state=params["stateId"], crop=params["cropId"]
        )

        # Converting to dict to allow fetching a property with a dynamicaly-built key
        latest_prediction_dict = {}
        predictions_array = []

        try:
            latest_prediction_dict = model_to_dict(predictions.latest("reference_date"))
        except:
            # If there is no predictions for a given market-commodity combination, replace by empty values
            latest_prediction_dict["reference_date"] = first_day_of_month

        months_difference = relativedelta(
            first_day_of_month, latest_prediction_dict["reference_date"]
        ).months
        # Structure the predictions in a way the graph can use.
        for i in range(NUMBER_OF_FORECASTS_MONTHS):
            forecast_key = "price_forecast_{}".format(i + months_difference)
            price = None
            only_interpolated_data = None

            if forecast_key in latest_prediction_dict:
                price = latest_prediction_dict[forecast_key]
            # TODO: confirm this interpolated data piece doesn't reset the price to zero
            if only_interpolated_data in latest_prediction_dict:
                price = latest_prediction_dict["only_interpolated_data"]

            predictions_array.append(
                {
                    "date": first_day_of_month + relativedelta(months=i),
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
