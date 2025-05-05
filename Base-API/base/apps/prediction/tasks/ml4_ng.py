from configparser import RawConfigParser
import csv
import datetime
import json
import requests
from dateutil.relativedelta import relativedelta
from base import settings
from base.apps.prediction.models import (
    Market,
    StateNg,
    MLMarketDataIndia,
    MLPredictionDataNg,
    MLMarketDataNigeria,
)
from base.apps.storage.models import Crop
from base.celery import app
from django.core.mail import send_mail


@app.task
def prediction_calls_ng():
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
    COMMODITIES = ["Onion", "Plantain", "Tomato", "Irish Potato", "Sweet Potato"]
    COMMODITIES_OBJECTS = Crop.objects.filter(name__in=COMMODITIES)

    states = StateNg.objects.filter(added_by_user=False)

    for state in states:
        for commodity_object in COMMODITIES_OBJECTS:
            try:
                payload = {
                    "state": state.name,
                    "commodity": commodity_object.name,
                }

                response_content = json.loads(
                    requests.post(
                        settings.PRICE_PREDICTION_URL_NIGERIA, headers=HEADERS, json=payload
                    ).content
                )

                # print(response_content)
                # print(response_content['Predictions'])

                # Skip the response if we don't have data for this state-commodity combination.
                if (
                    response_content["Result"]
                    == "Not a valid state-commodity combination"
                ):
                    continue

                MLPredictionDataNg.objects.create(
                    state=state,
                    crop=commodity_object,
                    reference_date=datetime.datetime.strptime(
                        response_content["Dates"][0], "%b, %Y"
                    ).date()
                    - relativedelta(
                        months=1
                    ),  # Parse the first date string into a python date object, and remove one day to get the date at which the scraping was done.
                    price_forecast_1=response_content["Predictions"][0],
                    price_forecast_2=response_content["Predictions"][1],
                    price_forecast_3=response_content["Predictions"][2],
                    price_forecast_4=response_content["Predictions"][3],
                    price_forecast_5=response_content["Predictions"][4],
                    price_forecast_6=response_content["Predictions"][5],
                    price_forecast_7=response_content["Predictions"][6],
                    price_forecast_8=response_content["Predictions"][7],
                    only_interpolated_data=response_content["Result"]
                    == "No real data in the last 6 months, use predictions with caution",  # Builds a boolean
                )
            except Exception as error:
                message = "An error happened in NIGERIA prediction calls. State: {}; crop: {}".format(
                    state, commodity_object
                )
                send_mail(subject, message, email_from, recipient_list)
                print("error during prediction call", error)
                print(
                    f"An error occurred: {commodity_object.name} {state.name} {error}\n"
                )
    print("prediction_calls task finished")


@app.task
def nigeria_states_data_db_insert():
    """Get scraping result from Master_encoded.csv file and store the latest values in DB"""
    subject = f"{settings.ENVIRONMENT}-ENV: Scraping Module error"
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [
        "app@yourvcca.org"
    ]  # TODO Improve it so the email is set as an environment variable

    print("nigeria_markets_data_db_insert task starting")
    CONFIG_INI_PATH = "/code/ml4-ng/Retraining-module/config.ini"
    MASTER_ENCODED_CSV_PATH = "/code/ml4-ng/data/Master_encoded.csv"
    # Maximum number of days without new scraped data before sending a warning email.
    NO_NEW_DATA_MAX_DAYS = 60

    config = RawConfigParser()
    config.optionxform = lambda option: option
    config.read(CONFIG_INI_PATH)

    # Build the dictionaries from config.ini file
    dict_commodities = dict(config.items("dict_comm"))
    dict_state = dict(config.items("dict_state"))

    # Invert keys and values in each dictionary to make fetching easier
    dict_commodities = {v: k for k, v in dict_commodities.items()}
    # dict_state = {v: k for k, v in dict_state.items()}

    with open(MASTER_ENCODED_CSV_PATH, newline="") as csvfile:
        spamreader = csv.reader(csvfile, delimiter=",", quotechar="|")
        header = next(spamreader, None)  # Skip header row
        print("opening ML4 NG csv file")
        latest_inserted_date = datetime.date(year=2000, month=1, day=1)

        # Try to find the latest data's date or fallback to default
        try:
            latest_inserted_date = MLMarketDataNigeria.objects.latest("date").date
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
            try:
                row_dict["date"] = datetime.datetime.strptime(
                    row_dict["date"], "%Y-%m-%d"
                ).date()
            except ValueError:
                try:
                    row_dict["date"] = datetime.datetime.strptime(
                        row_dict["date"], "%Y-%m-%d %H:%M:%S"
                    ).date()
                except ValueError as e:
                    # Handle the case where neither format works
                    print(f"Continue on Error: {e}")
                    continue

            # row_dict['date']=datetime.datetime.strptime(row_dict['date'], "%Y-%m-%d").date()

            # Only insert newest values
            if row_dict["date"] > latest_inserted_date:

                # Fetch the database entities names from the config.ini file using the labels properties of the API's response.
                commodity_name = dict_commodities[row_dict["comm_label"]]
                state_name = dict_state[row_dict["st_label"]]

                # Try to find the market and crop database entities matching the response data.
                try:
                    state = StateNg.objects.get(name=state_name)
                    crop = Crop.objects.get(name=commodity_name)
                    row_dict["state"] = state
                    row_dict["crop"] = crop
                except:
                    print("ERROR: CROP OR MARKET NOT MATCHING ANY")

                # """ TODO Remove once columns renamed
                # The followings are used to match the market data's API data to the database's data
                row_dict["date"] = row_dict["date"]
                row_dict["state_label"] = row_dict["st_label"]
                row_dict["commodity_label"] = row_dict["comm_label"]
                row_dict["price"] = row_dict["Price"]
                row_dict["last_price_1m"] = row_dict["Last_Month_Price"]
                row_dict["last_price_2m"] = row_dict["Last_2M_Price"]
                row_dict["last_price_3m"] = row_dict["Last_3M_Price"]
                row_dict["last_price_4m"] = row_dict["Last_4M_Price"]
                row_dict["last_price_5m"] = row_dict["Last_5M_Price"]
                row_dict["usd_to_ngn"] = row_dict["USDtoNaira"]
                row_dict["state_rollup"] = row_dict["state_roll"]
                row_dict["cpi"] = row_dict["CPI"]
                # """

                # """ TODO Remove once columns renamed
                del row_dict["Date"]
                del row_dict["st_label"]
                del row_dict["comm_label"]
                del row_dict["Price"]
                del row_dict["Last_Month_Price"]
                del row_dict["Last_2M_Price"]
                del row_dict["Last_3M_Price"]
                del row_dict["Last_4M_Price"]
                del row_dict["Last_5M_Price"]
                del row_dict["USDtoNaira"]
                del row_dict["state_roll"]
                del row_dict["CPI"]
                # """

                print("updated row dict", row_dict)

                try:
                    MLMarketDataNigeria.objects.create(**row_dict)
                except Exception as e:
                    message = "Unable to insert ML4 Market NIGERIA Objects. Latest date: {}".format(
                        latest_inserted_date
                    )
                    send_mail(subject, message, email_from, recipient_list)

                    print("Error: Market Data Nigeria object creation failed")
                    print(f"Exception details: {e}")

    try:
        # If the latest scraping data has been scraped N days before today, send an email as a warning
        latest_inserted_date = MLMarketDataNigeria.objects.latest("date").date
        if (
            latest_inserted_date + datetime.timedelta(days=NO_NEW_DATA_MAX_DAYS)
        ) < datetime.date.today():
            days_difference = (datetime.date.today() - latest_inserted_date).days
            print(
                "NG Scraping module error: no new data since {} days".format(
                    days_difference
                )
            )

            message = "An error happened in the NG scraping module. No new data has been scraped since {} days.".format(
                days_difference
            )
            subject = f"{settings.ENVIRONMENT}-ENV : NG Scraping Module error"
            email_from = settings.DEFAULT_FROM_EMAIL
            recipient_list = [
                "app@yourvcca.org"
            ]  # TODO Improve it so the email is set as an environment variable
            send_mail(subject, message, email_from, recipient_list)

    except:
        print("No latest date found, using default")

    print("Nigeria_markets_data_db_insert task finished")
