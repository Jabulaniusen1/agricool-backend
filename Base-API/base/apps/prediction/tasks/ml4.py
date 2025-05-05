from configparser import RawConfigParser
import csv
import datetime
import json
import requests
from base import settings
from base.apps.prediction.models import Market, MLPredictionData, MLMarketDataIndia
from base.apps.storage.models import Crop
from base.apps.storage.models import Crop
from base.celery import app
from django.core.mail import send_mail


@app.task
def prediction_calls():
    """Call the prediction API for all supported commodities and save the result in database"""
    subject = f"{settings.ENVIRONMENT}-ENV: Scraping Module error"
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [
        "app@yourvcca.org"
    ]  # TODO Improve it so the email is set as an environment variable

    print("prediction_calls task starting")
    HEADERS = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
    # Set to one not to use interpolated values
    USE_ONLY_AVAILABLE_VALUES_FOR_ERROR = 1
    COMMODITIES = ["Apple", "Banana", "Green Chilli", "Tomato"]
    COMMODITIES_OBJECTS = Crop.objects.filter(name__in=COMMODITIES)

    markets = Market.objects.filter(used_for_predictions=True)

    for market in markets:
        for commodity_object in COMMODITIES_OBJECTS:
            try:
                payload = {
                    "state": market.state.name,
                    "district": market.district,
                    "market": market.name,
                    "commodity": commodity_object.name,
                    "Available_values": USE_ONLY_AVAILABLE_VALUES_FOR_ERROR,
                }

                response_content = json.loads(
                    requests.post(
                        settings.PRICE_PREDICTION_URL_INDIA, headers=HEADERS, json=payload
                    ).content
                )

                print(response_content["Result"])
                # Skip the response if we don't have data for this market-commodity combination.
                if (
                    response_content["Result"]
                    == "Not a valid state-district-market-commodity combination"
                ):
                    continue

                MLPredictionData.objects.create(
                    market=market,
                    crop=commodity_object,
                    reference_date=datetime.datetime.strptime(
                        response_content["Dates"][0], "%d-%b-%Y"
                    ).date()
                    - datetime.timedelta(
                        days=1
                    ),  # Parse the first date string into a python date object, an remove one day to get the date at which the scraping was done.
                    price_forecast_1=response_content["Predictions"][0],
                    price_forecast_2=response_content["Predictions"][1],
                    price_forecast_3=response_content["Predictions"][2],
                    price_forecast_4=response_content["Predictions"][3],
                    price_forecast_5=response_content["Predictions"][4],
                    price_forecast_6=response_content["Predictions"][5],
                    price_forecast_7=response_content["Predictions"][6],
                    price_forecast_8=response_content["Predictions"][7],
                    price_forecast_9=response_content["Predictions"][8],
                    price_forecast_10=response_content["Predictions"][9],
                    price_forecast_11=response_content["Predictions"][10],
                    price_forecast_12=response_content["Predictions"][11],
                    price_forecast_13=response_content["Predictions"][12],
                    price_forecast_14=response_content["Predictions"][13],
                    only_interpolated_data=response_content["Result"]
                    == "No real data in the last 6 months, use predictions with caution",  # Builds a boolean
                )
            except:
                message = "An error happened in INDIA prediction calls. Market: {}; crop: {}".format(
                    market, commodity_object
                )
                send_mail(subject, message, email_from, recipient_list)
                print("error during prediction call")
    print("prediction_calls task finished")


@app.task
def india_markets_data_db_insert():
    """Get scraping result from Master_encoded.csv file and store the latest values in DB"""
    subject = f"{settings.ENVIRONMENT}-ENV: Scraping Module error"
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [
        "app@yourvcca.org"
    ]  # TODO Improve it so the email is set as an environment variable

    print("india_markets_data_db_insert task starting")
    CONFIG_INI_PATH = "/code/ml4/Retraining-module/config.ini"
    MASTER_ENCODED_CSV_PATH = "/code/ml4/data/Master_encoded.csv"
    # Maximum number of days without new scraped data before sending a warning email.
    NO_NEW_DATA_MAX_DAYS = 3

    config = RawConfigParser()
    config.optionxform = lambda option: option
    config.read(CONFIG_INI_PATH)

    # Build the dictionaries from config.ini file
    dict_commodities = dict(config.items("dict_commodities"))
    dict_state = dict(config.items("dict_state"))
    dict_district = dict(config.items("dict_district"))
    dict_market = dict(config.items("dict_market"))

    # Invert keys and values in each dictionary to make fetching easier
    dict_commodities = {v: k for k, v in dict_commodities.items()}
    dict_state = {v: k for k, v in dict_state.items()}
    dict_district = {v: k for k, v in dict_district.items()}
    dict_market = {v: k for k, v in dict_market.items()}

    with open(MASTER_ENCODED_CSV_PATH, newline="") as csvfile:
        spamreader = csv.reader(csvfile, delimiter=",", quotechar="|")
        header = next(spamreader, None)  # Skip header row
        print("opening csv file")
        latest_inserted_date = datetime.date(year=2000, month=1, day=1)

        # Try to find the latest data's date or fallback to default
        try:
            latest_inserted_date = MLMarketDataIndia.objects.latest("date").date
            print("Latest date found: {}".format(latest_inserted_date))
        except:
            print("No latest date found, using default")

        for row in spamreader:
            row_dict = {}

            # Build a dictionary from the row array using the header
            for index, value in enumerate(row):
                row_dict[header[index]] = value

            # """ TODO Remove once columns renamed
            row_dict["date"] = row_dict["Date"]
            # """

            # Parse the date string to a python date object.
            row_dict["date"] = datetime.datetime.strptime(
                row_dict["date"], "%Y-%m-%d"
            ).date()

            # Only insert newest values
            if row_dict["date"] > latest_inserted_date:

                # Fetch the database entities names from the config.ini file using the labels properties of the API's response.
                commodity_name = dict_commodities[row_dict["Comm_Label"]]
                state_name = dict_state[row_dict["State_Label"]]
                district_name = dict_district[row_dict["District_Label"]]
                market_name = dict_market[row_dict["Market_Label"]]

                # Try to find the market and crop database entities matching the response data.
                try:
                    market = Market.objects.get(
                        state__name=state_name, district=district_name, name=market_name
                    )
                    crop = Crop.objects.get(name=commodity_name)
                    row_dict["market"] = market
                    row_dict["crop"] = crop
                except:
                    print("ERROR: CROP OR MARKET NOT MATCHING ANY")

                # """ TODO Remove once columns renamed
                # The followings are used to match the market data's API data to the database's data
                row_dict["date"] = row_dict["date"]
                row_dict["state_label"] = row_dict["State_Label"]
                row_dict["district_label"] = row_dict["District_Label"]
                row_dict["market_label"] = row_dict["Market_Label"]
                row_dict["commodity_label"] = row_dict["Comm_Label"]
                row_dict["arrivals_metric_tons"] = row_dict["Arrivals (Tonnes)"]
                row_dict["modal_price_rs_per_quintal"] = row_dict[
                    "Modal Price (Rs./Quintal)"
                ]
                row_dict["last_price_1d"] = row_dict["Last_Day_Price"]
                row_dict["last_price_2d"] = row_dict["Last_2D_Price"]
                row_dict["last_price_3d"] = row_dict["Last_3D_Price"]
                row_dict["last_price_4d"] = row_dict["Last_4D_Price"]
                row_dict["last_price_5d"] = row_dict["Last_5D_Price"]
                row_dict["last_price_6d"] = row_dict["Last_6D_Price"]
                row_dict["last_price_7d"] = row_dict["Last_7D_Price"]
                row_dict["week"] = row_dict["week"]
                row_dict["day"] = row_dict["day"]
                row_dict["month"] = row_dict["month"]
                row_dict["usd_to_inr"] = row_dict["USDtoINR"]
                row_dict["brent_oil_price"] = row_dict["BrentOil_Price"]
                row_dict["state_rollup"] = row_dict["State_Roll"]
                row_dict["district_rollup"] = row_dict["District_Roll"]
                row_dict["availability"] = row_dict["Availability"]
                row_dict["price_available"] = row_dict["Available"]
                row_dict["price_available_1d"] = row_dict["Available_1D_Price"]
                row_dict["price_available_2d"] = row_dict["Available_2D_Price"]
                row_dict["price_available_3d"] = row_dict["Available_3D_Price"]
                row_dict["price_available_4d"] = row_dict["Available_4D_Price"]
                row_dict["price_available_5d"] = row_dict["Available_5D_Price"]
                row_dict["price_available_6d"] = row_dict["Available_6D_Price"]
                row_dict["price_available_7d"] = row_dict["Available_7D_Price"]
                row_dict["usd_to_inr_1d"] = row_dict["USDINR_1D"]
                row_dict["brent_oil_price_1d"] = row_dict["Brent_1D"]
                row_dict["usd_to_inr_2d"] = row_dict["USDINR_2D"]
                row_dict["brent_oil_price_2d"] = row_dict["Brent_2D"]
                row_dict["usd_to_inr_3d"] = row_dict["USDINR_3D"]
                row_dict["brent_oil_price_3d"] = row_dict["Brent_3D"]
                row_dict["usd_to_inr_4d"] = row_dict["USDINR_4D"]
                row_dict["brent_oil_price_4d"] = row_dict["Brent_4D"]
                row_dict["usd_to_inr_5d"] = row_dict["USDINR_5D"]
                row_dict["brent_oil_price_5d"] = row_dict["Brent_5D"]
                row_dict["usd_to_inr_6d"] = row_dict["USDINR_6D"]
                row_dict["brent_oil_price_6d"] = row_dict["Brent_6D"]
                row_dict["usd_to_inr_7d"] = row_dict["USDINR_7D"]
                row_dict["brent_oil_price_7d"] = row_dict["Brent_7D"]
                row_dict["usd_to_inr_8d"] = row_dict["USDINR_8D"]
                row_dict["brent_oil_price_8d"] = row_dict["Brent_8D"]
                row_dict["usd_to_inr_9d"] = row_dict["USDINR_9D"]
                row_dict["brent_oil_price_9d"] = row_dict["Brent_9D"]
                row_dict["usd_to_inr_10d"] = row_dict["USDINR_10D"]
                row_dict["brent_oil_price_10d"] = row_dict["Brent_10D"]
                row_dict["usd_to_inr_11d"] = row_dict["USDINR_11D"]
                row_dict["brent_oil_price_11d"] = row_dict["Brent_11D"]
                row_dict["usd_to_inr_12d"] = row_dict["USDINR_12D"]
                row_dict["brent_oil_price_12d"] = row_dict["Brent_12D"]
                row_dict["usd_to_inr_13d"] = row_dict["USDINR_13D"]
                row_dict["brent_oil_price_13d"] = row_dict["Brent_13D"]
                row_dict["usd_to_inr_14d"] = row_dict["USDINR_14D"]
                row_dict["brent_oil_price_14d"] = row_dict["Brent_14D"]
                row_dict["usd_to_inr_lag"] = row_dict["USDtoINR_lag"]
                row_dict["brent_oil_price_lag"] = row_dict["BrentOil_Price_lag"]
                row_dict["availability_bit"] = row_dict["Availability_bit"]
                # """

                # """ TODO Remove once columns renamed
                del row_dict["Date"]
                del row_dict["State_Label"]
                del row_dict["District_Label"]
                del row_dict["Market_Label"]
                del row_dict["Comm_Label"]
                del row_dict["Arrivals (Tonnes)"]
                del row_dict["Modal Price (Rs./Quintal)"]
                del row_dict["Last_Day_Price"]
                del row_dict["Last_2D_Price"]
                del row_dict["Last_3D_Price"]
                del row_dict["Last_4D_Price"]
                del row_dict["Last_5D_Price"]
                del row_dict["Last_6D_Price"]
                del row_dict["Last_7D_Price"]
                del row_dict["USDtoINR"]
                del row_dict["BrentOil_Price"]
                del row_dict["State_Roll"]
                del row_dict["District_Roll"]
                del row_dict["Availability"]
                del row_dict["Available"]
                del row_dict["Available_1D_Price"]
                del row_dict["Available_2D_Price"]
                del row_dict["Available_3D_Price"]
                del row_dict["Available_4D_Price"]
                del row_dict["Available_5D_Price"]
                del row_dict["Available_6D_Price"]
                del row_dict["Available_7D_Price"]
                del row_dict["USDINR_1D"]
                del row_dict["Brent_1D"]
                del row_dict["USDINR_2D"]
                del row_dict["Brent_2D"]
                del row_dict["USDINR_3D"]
                del row_dict["Brent_3D"]
                del row_dict["USDINR_4D"]
                del row_dict["Brent_4D"]
                del row_dict["USDINR_5D"]
                del row_dict["Brent_5D"]
                del row_dict["USDINR_6D"]
                del row_dict["Brent_6D"]
                del row_dict["USDINR_7D"]
                del row_dict["Brent_7D"]
                del row_dict["USDINR_8D"]
                del row_dict["Brent_8D"]
                del row_dict["USDINR_9D"]
                del row_dict["Brent_9D"]
                del row_dict["USDINR_10D"]
                del row_dict["Brent_10D"]
                del row_dict["USDINR_11D"]
                del row_dict["Brent_11D"]
                del row_dict["USDINR_12D"]
                del row_dict["Brent_12D"]
                del row_dict["USDINR_13D"]
                del row_dict["Brent_13D"]
                del row_dict["USDINR_14D"]
                del row_dict["Brent_14D"]
                del row_dict["USDtoINR_lag"]
                del row_dict["BrentOil_Price_lag"]
                del row_dict["Availability_bit"]
                # """

                # In the csv, boolean values appear as '1.0' or '0.0' so here we convert them to booleans
                row_dict["price_available"] = row_dict["price_available"] == "1.0"
                row_dict["price_available_1d"] = row_dict["price_available_1d"] == "1.0"
                row_dict["price_available_2d"] = row_dict["price_available_2d"] == "1.0"
                row_dict["price_available_3d"] = row_dict["price_available_3d"] == "1.0"
                row_dict["price_available_4d"] = row_dict["price_available_4d"] == "1.0"
                row_dict["price_available_5d"] = row_dict["price_available_5d"] == "1.0"
                row_dict["price_available_6d"] = row_dict["price_available_6d"] == "1.0"
                row_dict["price_available_7d"] = row_dict["price_available_7d"] == "1.0"

                try:
                    MLMarketDataIndia.objects.create(**row_dict)
                except:
                    message = "Unable to insert ML4 Market INDIA Objects. Latest date: {}".format(
                        latest_inserted_date
                    )
                    send_mail(subject, message, email_from, recipient_list)

                    print("Error: Market Data India object creation failed")

    try:
        # If the latest scraping data has been scraped N days before today, send an email as a warning
        latest_inserted_date = MLMarketDataIndia.objects.latest("date").date
        if (
            latest_inserted_date + datetime.timedelta(days=NO_NEW_DATA_MAX_DAYS)
        ) < datetime.date.today():
            days_difference = (datetime.date.today() - latest_inserted_date).days
            print(
                "Scraping module error: no new data since {} days".format(
                    days_difference
                )
            )

            message = "An error happened in the scraping module. No new data has been scraped since {} days.".format(
                days_difference
            )
            send_mail(subject, message, email_from, recipient_list)

    except:
        print("No latest date found, using default")

    print("india_markets_data_db_insert task finished")
