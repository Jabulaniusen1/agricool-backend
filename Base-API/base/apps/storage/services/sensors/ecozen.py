from typing import List

from . import (MIN_DATETIME, CoolingUnitSpecifications, SensorIntegrationBase,
               SensorSource)

##
# Constants
##
API_ENDPOINT = 'https://api.ecozen.ai'
AUTH_ENDPOINT = API_ENDPOINT + '/api/dashboard/auth/login'

# @NOTE: TBD; currently not in use
class EcozenIntegration(SensorIntegrationBase):
    AUTHORIZATION_HEADER = "X-Authorization"

    def authorize(self) -> None:
        with self.session as ses:
            res = ses.post(AUTH_ENDPOINT, json={
                "username": self.credentials["username"],
                "password": self.credentials["password"],
            })

            if res.status_code == 401:
                raise Exception("Error: Invalid username or password")

            if res.status_code != 200:
                raise Exception(f"Error: Unable to authorize with Victron. Status code: {res.status_code}")

            try:
                json_body = res.json()
            except ValueError:
                raise Exception("Ecozen: Failed to parse JSON response")

            if "error" in json_body:
                raise Exception(f"Ecozen: {json_body['error']} - {json_body['message']}")

            access_token = json_body.get("accessToken")

            if not access_token:
                raise Exception("Error: Unable to capture access token from Ecozen")

            self.set_authorization(access_token)

    def get_datums_from_source(self, source_id=None, min_datetime=MIN_DATETIME) -> List[CoolingUnitSpecifications]:
        self.ensure_is_authorized()

        # if specification_type == "TEMPERATURE":
        return []

    def list_sources(self) -> List[SensorSource]:
        raise Exception("Not implemented")

    # Custom methods

    def api_get_room_param(self, start_datetime, end_datetime):
        res = self.session.post(
            f"https://api.ecozen.ai/dashboard/v1/ecofrost/graph/{self.credentials['machine_id']}",
            json={
                "from": start_datetime.strftime("%Y-%m-%d"),
                "to": end_datetime.strftime("%Y-%m-%d"),
                "paramList": "Room_1_T",
            },
        )

        json_body = res.json()
        if not json_body:
            raise Exception("Error: Unexpected response from Ecozen")

        return res.json()[0]["data"]
