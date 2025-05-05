import datetime
from dateutil.relativedelta import relativedelta
import json
from django.forms import model_to_dict
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from django.db.models import F

from rest_framework import status, permissions

from rest_framework.viewsets import (
    GenericViewSet,
)
from rest_framework.views import APIView

from rest_framework.response import Response
from rest_framework.decorators import action

from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)

from base.apps.prediction.models import (
    MLMarketDataIndia,
    MLPredictionData,
    Market,
    State,
    StateNg,
    MLMarketDataNigeria,
    MLPredictionDataNg,
)
from base.apps.storage.models import Crop
from base.apps.user.models import Operator, ServiceProvider, Farmer
from .serializers import StateSerializer, MarketSerializer, StateNgSerializer


class StateViewSet(
    CreateModelMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin
):
    model = State
    serializer_class = StateSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        user = self.request.user
        try:
            country = ServiceProvider.objects.get(user=user).company.country
        except:
            country = Operator.objects.get(user=user).company.country

        return self.model.objects.filter(country__country=country).order_by("name")

    @action(detail=False, methods=["GET"], name="Get ML4 markets")
    def get_parameters_for_prediction(self, request, *args, **kwargs):
        user = self.request.user
        # try:
        #     try:
        #         company = ServiceProvider.objects.get(user=user).company
        #     except:
        #         company = Operator.objects.get(user=user).company
        #     country = company.country
        # except:
        #     country = Operator.objects.get(user=user).company

        try:
            country = ServiceProvider.objects.get(user=user).company.country
            print(f"Service provider country: {country}!")
        except:
            try:
                country = Operator.objects.get(user=user).company.country
                print(f"operator country: {country}!")

            except:
                country = Farmer.objects.get(user=user).country
                print(f"farmer country: {country}!")

        markets = (
            Market.objects.select_related("state")
            .filter(state__country__country=country, used_for_predictions=True)
            .order_by("state__name", "district", "name")
        )

        marketsDict = {}

        for market in markets:
            if not market.state.name in marketsDict:
                marketsDict[market.state.name] = {}

            if not market.district in marketsDict[market.state.name]:
                marketsDict[market.state.name][market.district] = []

            marketsDict[market.state.name][market.district].append(
                {"id": market.id, "name": market.name}
            )

        # TODO Beware of performances issues
        available_crops = list(
            Crop.objects.filter(crop_prediction__market__used_for_predictions=True)
            .distinct()
            .values("id", "name")
        )

        return JsonResponse(
            {"available_crops": available_crops, "available_markets": marketsDict}
        )


class MarketViewSet(
    CreateModelMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin
):
    model = Market
    serializer_class = MarketSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.filter(
            state__country=self.request.query_params.get("country")
        ).order_by("name")

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context={
                "country": request.data["country"],
                "state": request.data["state_name"],
            },
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)

        return Response(serializer.errors, status=400)


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


class StateViewSetNg(
    CreateModelMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin
):
    model = StateNg
    serializer_class = StateNgSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        user = self.request.user
        try:
            country = ServiceProvider.objects.get(user=user).company.country
        except:
            country = Operator.objects.get(user=user).company.country

        return self.model.objects.filter(country__country=country).order_by("name")

    @action(detail=False, methods=["GET"], name="Get ML4 states for nigeria")
    def get_parameters_for_prediction(self, request, *args, **kwargs):
        user = self.request.user
        available_crops = [
            {"id": 37, "name": "Onion"},
            {"id": 44, "name": "Plantain"},
            {"id": 56, "name": "Tomato"},
            {"id": 47, "name": "Irish Potato"},
            {"id": 72, "name": "Sweet Potato"},
        ]

        try:
            country = ServiceProvider.objects.get(user=user).company.country
            print(f"Service provider country: {country}!")
        except:
            try:
                country = Operator.objects.get(user=user).company.country
                print(f"operator country: {country}!")

            except:
                country = Farmer.objects.get(user=user).country
                print(f"farmer country: {country}!")

        available_states = list(self.model.objects.all().values("id", "name"))

        # TODO Beware of performances issues

        return JsonResponse(
            {"available_crops": available_crops, "available_states": available_states}
        )


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
            # TODO: confirm this interpolated data piece doesn't reset the price tozero
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
