from datetime import date, datetime

import requests

from base.apps.storage.services.sensors.figorr import FigorrIntegration
from base.apps.storage.services.sensors.ubibot import UbibotIntegration
from base.apps.storage.services.sensors.victron import VictronIntegration


def build_integration(cooling_unit, credentials):
  if credentials['type'] == "victron":
      return VictronIntegration(cooling_unit, credentials)
  if credentials['type'] == "ubibot":
      return UbibotIntegration(cooling_unit, credentials)
  if credentials['type'] == "figorr":
      return FigorrIntegration(cooling_unit, credentials)
  raise Exception("Integration not implemented")

def fetch_ecozen_temperature(credentials):
    login_url = "https://api.ecozen.ai/api/dashboard/auth/login"
    room_url = "https://api.ecozen.ai/dashboard/v1/ecofrost/graph/"

    params = {
        "username": credentials["username"],
        "password": credentials["password"],
    }

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }

    response = requests.post(login_url, headers=headers, json=params)
    
    if response.status_code != 200:
        raise Exception(f"Ecozen Authentication Failed: {response.text}")

    response_json = response.json()
    
    if "accessToken" not in response_json:
        raise Exception("Ecozen Authentication Failed: No access token received.")

    token = response_json["accessToken"]
    today = date.today().strftime("%Y-%m-%d")

    room_param = {"from": today, "to": today, "paramList": "Room_1_T"}
    room_headers = {"Authorization": token}
    
    temperature_response = requests.post(
        room_url + credentials["source_id"], headers=room_headers, json=room_param
    )

    if temperature_response.status_code != 200:
        raise Exception(f"Failed to retrieve room temperature: {temperature_response.text}")

    temperature_data = temperature_response.json()
    last_recorded_temperature = temperature_data[0]["data"][-1]

    room_param = {"from": today, "to": today, "paramList": "Set_T"}
    temperature_response = requests.post(
        room_url + credentials["source_id"], headers=room_headers, json=room_param
    )

    if temperature_response.status_code != 200:
        raise Exception(f"Failed to retrieve set point temperature: {temperature_response.text}")

    set_point_temperature = temperature_response.json()[0]["data"][-1]

    updated_date = datetime.fromtimestamp(last_recorded_temperature[0] / 1000).astimezone()
    updated_value = last_recorded_temperature[1]
    updated_point_value = set_point_temperature[1]

    return updated_date, updated_value, updated_point_value
