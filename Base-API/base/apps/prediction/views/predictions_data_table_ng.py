import datetime
import json

from dateutil.relativedelta import relativedelta
from django.forms import model_to_dict
from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.views import APIView

from base.apps.prediction.models import MLPredictionDataNg, StateNg


class PredictionsDataTableAPIViewNg(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):

        params = json.loads(request.body)
        predictions_array = []
        # Note - we have to use first day of each month for the calculation to make sense
        first_day_of_month = datetime.date.today().replace(day=1)

        for stateId in params["statesIds"]:
            state = None
            latest_prediction_dict = {}

            try:
                state = StateNg.objects.get(id=stateId)
            except:
                continue

            try:
                latest_prediction_dict = model_to_dict(
                    MLPredictionDataNg.objects.filter(
                        state=state, crop=params["cropId"]
                    ).latest("reference_date")
                )
            except:
                latest_prediction_dict["reference_date"] = first_day_of_month

            for day in params["days"]:
                day = datetime.datetime.strptime(day, "%Y-%m-%d").date()
                print(
                    f'confirm {state} {first_day_of_month} {params["days"]} {relativedelta(day, first_day_of_month).months} '
                )

                if relativedelta(day, first_day_of_month).months < 0:
                    continue
                months_difference = relativedelta(
                    day, latest_prediction_dict["reference_date"]
                ).months
                forecast_key = "price_forecast_{}".format(months_difference)
                price = None
                if forecast_key in latest_prediction_dict:
                    price = round(latest_prediction_dict[forecast_key], 2)

                predictions_array.append(
                    {
                        "state": state.name,
                        "date": day.strftime("%b, %d, %Y"),
                        "price": price,
                    }
                )

        return JsonResponse(predictions_array, safe=False)
