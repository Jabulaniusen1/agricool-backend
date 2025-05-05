from datetime import datetime, timedelta, timezone

import requests

from base.apps.storage.models import (CoolingUnit, CoolingUnitSpecifications,
                                      SensorIntegration)
from base.apps.storage.services.sensors.figorr import FigorrIntegration
from base.apps.storage.services.sensors.ubibot import UbibotIntegration
from base.apps.storage.services.sensors.victron import VictronIntegration
from base.apps.user.models import Notification
from base.celery import app


@app.task
def update_temperature():
    """Update temperature of cold rooms every fifteen minutes"""
    lowest_timestamp = datetime(1970, 1, 1, tzinfo=timezone.utc) # 0 unix timestamp

    cooling_units = CoolingUnit.objects.filter(sensor=True, deleted=False)
    print(f'Looping through {len(cooling_units)} cooling units')

    for cu in cooling_units:
        print(f'Cooling Unit [{cu.id}]: Name "{cu.name}"')

        try:
            credentials = SensorIntegration.objects.filter(cooling_unit=cu).values().first()
            if not credentials:
                print(f'Cooling Unit [{cu.id}]: No credentials found')
                continue
        except Exception as e:
            print(f'Cooling Unit [{cu.id}]: Error retrieving credentials - {str(e)}')
            continue

        updates = []
        cu_spec = CoolingUnitSpecifications.objects.filter(
            cooling_unit=cu, specification_type="TEMPERATURE"
        )

        last_entry = cu_spec.order_by("-datetime_stamp").first()
        last_entry_timestamp = last_entry.datetime_stamp if last_entry else lowest_timestamp
        last_entry_formatted = last_entry_timestamp.strftime("%Y-%m-%d %H:%M:%S")

        if not cu_spec.exists() or last_entry is None:
            print(f"Cooling Unit [{cu.id}]: No temperature found")

        print(f'Cooling Unit [{cu.id}]: Last Entry "{last_entry}"')


        if credentials["type"] in ["ubibot", "figorr", "victron"]:
            try:
                integration = None
                if credentials["type"] == "figorr":
                    integration = FigorrIntegration(cu, credentials)
                elif credentials["type"] == "ubibot":
                    integration = UbibotIntegration(cu, credentials)
                elif credentials["type"] == "victron":
                    integration = VictronIntegration(cu, credentials)

                datums = integration.get_datums_from_source(source_id=credentials["source_id"], min_datetime=last_entry_timestamp)

                for datum in datums:
                    updates.append({
                        "updated_date": datum.datetime_stamp,
                        "updated_value": datum.value,
                        "updated_point_value": None
                    })

            except Exception as e:
                print(f"Error fetching {credentials['type']} data: {str(e)}")
                continue

        # === ECOZEN ===
        elif credentials["type"] == "ecozen":
            try:
                params = {
                    "username": credentials["username"],
                    "password": credentials["password"],
                }

                ecozen_url = "https://api.ecozen.ai/api/dashboard/auth/login"
                headers = {
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                }
                response = requests.post(ecozen_url, headers=headers, json=params)

                if "accessToken" in response.json():
                    token = response.json()["accessToken"]
                    date_from = last_entry_formatted
                    date_to = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    room_url = "https://api.ecozen.ai/dashboard/v1/ecofrost/graph/"
                    room_param = {"from": date_from, "to": date_to, "paramList": "Room_1_T"}
                    room_headers = {"Authorization": token}

                    temperature_response = requests.post(
                        room_url + credentials["source_id"], headers=room_headers, json=room_param
                    )
                    temperature_data = temperature_response.json()[0]["data"]

                    room_param = {"from": date_from, "to": date_to, "paramList": "Set_T"}
                    temperature_response = requests.post(
                        room_url + credentials["source_id"], headers=room_headers, json=room_param
                    )
                    set_point_temperature = temperature_response.json()[0]["data"]

                    delta = timedelta(minutes=15)
                    last_time = last_entry_timestamp

                    for i in range(len(temperature_data)):
                        data_time = temperature_data[i][0]
                        data_time = (
                            datetime.fromtimestamp((data_time / 1000))
                        ).astimezone()
                        if data_time > last_entry_timestamp and data_time - last_time > delta:
                            last_time = data_time
                            updates.append({
                                "updated_date": data_time,
                                "updated_value": temperature_data[i][1],
                                "updated_point_value": set_point_temperature[i][1],
                            })

            except Exception as e:
                print(f"Error fetching Ecozen data: {str(e)}")
                continue

        print(f'Cooling Unit [{cu.id}]: {len(updates)} updates found')

        # === STORE TEMPERATURE UPDATES ===
        for new_data in updates:
            if new_data["updated_value"] and (credentials["type"] != "ecozen" or new_data["updated_point_value"]):
                CoolingUnitSpecifications.objects.get_or_create(
                    datetime_stamp=new_data["updated_date"],
                    specification_type="TEMPERATURE",
                    value=new_data["updated_value"],
                    set_point_value=new_data["updated_point_value"],
                    cooling_unit=cu,
                )

                Notification.objects.filter(event_type="SENSOR_ERROR", specific_id=cu.id).delete()

        print(f'Cooling Unit [{cu.id}]: Temperature data updated')

