import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import List, TypedDict

from . import (MIN_DATETIME, CoolingUnitSpecifications, SensorIntegrationBase,
               build_url)

##
# Constants
##
API_ENDPOINT = 'https://vrmapi.victronenergy.com'
DEMO_AUTH_ENDPOINT = API_ENDPOINT + '/v2/auth/loginAsDemo'
AUTH_ENDPOINT = API_ENDPOINT + '/v2/auth/login'
QUERY_ENDPOINT = API_ENDPOINT + '/v2/installations/{site_id}/stats'
AGGR_STATS_ENDPOINT = API_ENDPOINT + '/v2/installations/{site_id}/overallstats'
USER_ENDPOINT = API_ENDPOINT + '/v2/admin/users'
USER_SITE_ENDPOINT = API_ENDPOINT + '/v2/users/{user_id}/installations'
WIDGETS_ENDPOINT = API_ENDPOINT + '/v2/installations/{site_id}/widgets/{widget_type}'
SYSTEM_OVERVIEW_ENDPOINT = API_ENDPOINT + '/v2/installations/{site_id}/system-overview'
SYSTEM_DIAGNOSTICS_ENDPOINT = API_ENDPOINT + '/v2/installations/{site_id}/diagnostics'
DIAG_ENDPOINT = API_ENDPOINT + '/v2/installations/{site_id}/diagnostics'

class VictronSensorSource(TypedDict):
    id: str
    name: str
    specification_type: str
    site_id: int
    site_name: str
    instance_id: int
    attribute_id: int
    attribute_code: str
    last_seen_at: datetime

MAX_DATAPOINTS_PER_REQUEST = 10000

class VictronIntegration(SensorIntegrationBase[VictronSensorSource]):
    AUTHORIZATION_HEADER = "X-Authorization"
    SensorSourceType = VictronSensorSource

    ##
    # Override methods
    ##

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

            res_body_json = res.json()

            access_token = res_body_json['token']
            self.user_id = res_body_json['idUser']

            if not access_token:
                raise Exception("Error: Unable to capture access token from Ecozen")

            self.set_authorization(accessToken)

    # def create_datum(self, source: VictronSensorSource, **kwargs) -> CoolingUnitSpecifications:
    #     return super().create_datum(source, **kwargs)

    def list_sources(self) -> List[VictronSensorSource]:
        self.ensure_is_authorized()

        sites = self.api_get_user_installations()
        sensors: List[VictronSensorSource] = []  # List to store sensors from all sites

        for site in sites:
            site_id = site['idSite']
            site_name = site['name']

            system_overview = self.api_get_system_overview(site_id)

            for device in system_overview["devices"]:
                instance_id = device['instance'] if 'instance' in device else None
                device_name = device['customName'] if 'customName' in device else device['name']

                if not instance_id:
                    continue

                # Don't include the device if it doesn't have "device-temperature-sensor" in its "class" AttributeError
                if "device-temperature-sensor" not in device.get("class", ""):
                    continue

                widget_summary = self.api_get_widget_temp_summary_and_graph(site_id, instance=instance_id)

                for attribute_id, attribute in widget_summary['records']['meta'].items():
                    specification_type = None

                    if attribute['description'] == 'Temperature':
                        specification_type = CoolingUnitSpecifications.SpecificationType.TEMPERATURE
                    elif attribute['description'] == 'Humidity':
                        specification_type = CoolingUnitSpecifications.SpecificationType.TEMPERATURE
                    # elif attribute['description'] == 'Pressure':
                    #     specification_type = "PRESSURE"
                    else:
                        continue

                    sensors.append({
                        'id': f'victron-{site_id}-{instance_id}-{attribute_id}',
                        'name': f'{site_name} | {device_name} | {attribute["description"]}',
                        'specification_type': specification_type,

                        # Victron specific attributes
                        'site_id': int(site_id),
                        'site_name': site_name,
                        'instance_id': int(instance_id),
                        'attribute_id': int(attribute_id),
                        'attribute_code': attribute['code'],
                        'last_seen_at': datetime.fromtimestamp(device['lastConnection']),
                    })

        return sensors

    def get_datums_from_source(self, source_id=None, min_datetime=MIN_DATETIME, delta=timedelta(minutes=15)) -> List[CoolingUnitSpecifications]:
        if not source_id:
            raise ValueError("source_id is required")

        source = self.get_source(source_id)

        # Ensure min_datetime is datetime so we can calculate
        min_datetime = datetime.fromtimestamp(min_datetime, timezone.utc) if isinstance(min_datetime, int) else min_datetime

        now = datetime.now(timezone.utc)
        min_datetime = max(MIN_DATETIME, min_datetime)

        # We need to know how many data points we will have to acquire from victron vrm api
        # Each datapoint should represent a 15 minute interval
        # The victron vrm api only provides an endpoint that responds directly to a graph rendering need in the frontend
        # So we need to calculate the number of data points we need to acquire from the api
        # 15 minutes has 900 seconds
        calculated_timeframe = now - min_datetime
        num_datapoints = int(calculated_timeframe // delta)
        ref_timeframe = timedelta(seconds=num_datapoints * delta.seconds)

        # the number of datapoints should be capped for a total of 200 datapoints
        num_datapoints = min(num_datapoints, MAX_DATAPOINTS_PER_REQUEST)

        # From the num of datapoints, we should now calculate the max_datetime
        # 15 minutes has 900 seconds
        max_datetime = min_datetime + ref_timeframe

        data = self.get_source_datapoints(
            source,
            start=min_datetime,
            end=max_datetime,
            points_per_pixel=1,
            width=num_datapoints,
        )

        datums = []

        for cur_victron_datum in data:
            cur_victron_timestamp, cur_victron_value = cur_victron_datum
            cur_victron_datetime = datetime.fromtimestamp(cur_victron_timestamp, tz=timezone.utc) if cur_victron_timestamp else None

            if cur_victron_value is None or cur_victron_datetime is None:
                continue

            datum = self.create_datum(
                source=source,
                value=cur_victron_value,
                timestamp=cur_victron_datetime,
                set_point_value=None,
            )

            datums.append(datum)

        return datums

    def get_min_datetime(self, source_id):
        super_min_datetime = super().get_min_datetime(source_id)

        if super_min_datetime != MIN_DATETIME:
            return super_min_datetime

        # In case theres no record, we'll need to fetch the whole window from the API and get
        # the starting point. This is due to the limitation in the VRM API, as we can only get
        # the data based on a graph data and not based on the actual recorded events.
        source = self.get_source(source_id)

        # Attempt to gather the min datetime from the API
        data = self.get_source_datapoints(
            source,
            start=MIN_DATETIME,
            end=datetime.now(timezone.utc).timestamp(),
            width=MAX_DATAPOINTS_PER_REQUEST,
        )

        if data:
            for datapoint in data:
                timestamp = datapoint[0]
                value = datapoint[1]

                if value is not None:
                    return timestamp

        return MIN_DATETIME

    def get_source_datapoints(self, source, **kwargs):
        # Lets retrieve the datapoints now
        res = self.api_get_widget_graph(
            site_id=source['site_id'],
            instance_id=source['instance_id'],
            attribute_ids=[source['attribute_id']],
            attribute_codes=[source['attribute_code']],
            **kwargs,
        )

        try:
            data = res['records']['data'][f"{source['attribute_id']}"]
        except KeyError:
            data = []

        return data
        # return [datapoint for datapoint in data if datapoint[1] is not None]

    ##
    # Custom API methods
    ##

    # Custom API methods

    def api_get_user_installations(self, extended=False):
        self.ensure_is_authorized()

        url = USER_SITE_ENDPOINT.format(user_id=self.user_id) + "?" + urllib.parse.urlencode({"extended": "1" if extended else None})

        with self.session as ses:
            res = ses.get(url)

            if res.status_code != 200:
                print(res.text)
                raise Exception(f"Error: Unable to get user installations. Status code: {res.status_code}")

            json = res.json()

            return json['records']

    def api_get_system_overview(self, site_id):

        self.ensure_is_authorized()

        url = (
            SYSTEM_OVERVIEW_ENDPOINT.format(site_id=site_id)
        )

        with self.session as ses:
            res = ses.get(url)

            if res.status_code != 200:
                print(res.text)
                raise Exception(f"Error: Unable to get installation system overview. Status code: {res.status_code}")

            json = res.json()

            return json['records']

    def api_get_system_diagnostics(self, site_id):
        self.ensure_is_authorized()

        url = (
            SYSTEM_DIAGNOSTICS_ENDPOINT.format(site_id=site_id)
        )

        with self.session as ses:
            res = ses.get(url)

            if res.status_code != 200:
                print(res.text)
                raise Exception(f"Error: Unable to get installation system diagnostics. Status code: {res.status_code}")

            json = res.json()

            return json['records']

    def api_get_widget_temp_summary_and_graph(self, site_id, instance=None):
        self.ensure_is_authorized()

        url = build_url(
            WIDGETS_ENDPOINT.format(
                site_id=site_id,
                widget_type="TempSummaryAndGraph",
            ),
            {
                "instance": instance or None,
            },
        )

        with self.session as ses:
            res = ses.get(url)

            if res.status_code != 200:
                raise Exception(f"Error: Unable to get widget/TempSummaryAndGraph. Status code: {res.status_code}")

            json = res.json()

            return json

    def api_get_widget_graph(self, site_id, attribute_ids=[], attribute_codes=[], instance_id=None, start=None, end=None, points_per_pixel=None, width=None, use_min_max=False):
        self.ensure_is_authorized()

        # Ensure start and end are int timestamps
        if start is not None:
            start = int(
                start.timestamp() if isinstance(start, datetime) else start
            )
        if end is not None:
            end = int(
                end.timestamp() if isinstance(end, datetime) else end
            )

        url = build_url(
            WIDGETS_ENDPOINT.format(
                site_id=site_id,
                widget_type="Graph",
            ),
            {
                "attributeIds": attribute_ids or [],
                "attributeCodes" : attribute_codes or [],
                "instance": instance_id if instance_id is not None else None,
                "start": start if start is not None else None,
                "end": end if end is not None else None,
                "pointsPerPixel": points_per_pixel if points_per_pixel is not None else None,
                "width": width if width is not None else None,
                "useMinMax": 1 if use_min_max else None,
            },
        )

        with self.session as ses:
            res = ses.get(url)

            if res.status_code != 200:
                raise Exception(f"Error: Unable to get widget/Graph. Status code: {res.status_code}")

            json = res.json()

            return json
