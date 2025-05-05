from datetime import datetime, timezone
from typing import List, Optional, TypedDict
from urllib.parse import urlencode

from . import MIN_DATETIME, CoolingUnitSpecifications, SensorIntegrationBase

##
# Constants
##
API_ENDPOINT = 'https://enterprise.backend.figorr.com/app/api'
AUTH_ENDPOINT = API_ENDPOINT + '/v1/auth/login'
DEVICES_ENDPOINT = API_ENDPOINT + '/v1/devices'

class FigorrSensorSource(TypedDict):
    id: str
    name: str
    specification_type: str
    device_id: str
    is_active: bool
    owner: str
    power: Optional[bool]
    settings: Optional[dict]
    stat: Optional[dict]
    created_at: datetime
    updated_at: datetime

class FigorrIntegration(SensorIntegrationBase):
    SensorSourceType = FigorrSensorSource

    # Methods to be overridden
    def authorize(self) -> None:
        with self.session as ses:
            response = ses.post(AUTH_ENDPOINT, json={
                'email': self.credentials['username'],
                'password': self.credentials['password'],
            })

            if response.status_code == 401:
                raise Exception('Error: Invalid username or password')

            if response.status_code != 201:
                raise Exception(f'Error: Unable to authorize with Figorr. Status code: {response.status_code}')

        res_body_json = response.json()

        if 'payload' not in res_body_json or 'tokens' not in res_body_json['payload']:
            raise Exception('Error: Malformed API response, missing payload or tokens.')

        access_token = res_body_json['payload']['tokens'].get('accessToken')
        self.user_id = res_body_json['payload']['user'].get('id')

        if not access_token:
            raise Exception('Error: Unable to retrieve access token from Figorr API response')

        self.set_authorization(access_token)


    def list_sources(self) -> List[FigorrSensorSource]:
        self.ensure_is_authorized()

        devices = self.api_get_user_installations()
        sensors: List[FigorrSensorSource] = []

        for device in devices:
            stat = device.get('stat')
            if not stat:
                continue  # Skip devices without statistics

            # Extract sensor data
            temperature = stat.get('temperature')
            humidity = stat.get('humidity')

            if not temperature and not humidity:
                continue  # Skip if neither temperature nor humidity is available
            # TODO: expand to support other sensor types like Battery Level, for example

            if temperature:
                sensors.append(self.create_sensor_entry(device, CoolingUnitSpecifications.SpecificationType.TEMPERATURE, stat))

            if humidity:
                sensors.append(self.create_sensor_entry(device, CoolingUnitSpecifications.SpecificationType.HUMIDITY, stat))


        return sensors


    def get_datums_from_source(self, source_id=None, min_datetime=None) -> List[CoolingUnitSpecifications]:
        if not source_id:
            raise ValueError('source_id is required')
        
        source = self.get_source(source_id)

        # If min_datetime is not provided, use source.created_at; otherwise, use MIN_DATETIME
        if min_datetime is None:
            min_datetime = source.get('created_at', MIN_DATETIME)
        elif isinstance(min_datetime, int):
            min_datetime = self.parse_iso_timestamp(min_datetime)

        now = datetime.now(timezone.utc)
        min_datetime = max(MIN_DATETIME, min_datetime)

        data = self.api_get_source_datapoints(source, start=min_datetime, end=now)

        datums = []
        for datum in data:
            timestamp = self.parse_iso_timestamp(datum.get('timeStamp'))
            if not timestamp:
                continue  # Skip invalid timestamps

            value = datum.get('temperature') if source.get('specification_type') == CoolingUnitSpecifications.SpecificationType.TEMPERATURE else datum.get('humidity')
            datums.append(
                self.create_datum(
                    source=source,
                    value=value,
                    timestamp=timestamp,
                    set_point_value=None,
                )
            )

        return datums


    # Custom API methods
    def api_get_user_installations(self):
        self.ensure_is_authorized()

        with self.session as ses:
            response = ses.get(DEVICES_ENDPOINT)

            if response.status_code != 200:
                raise Exception(f'Error: Unable to get user installations. Status code: {response.status_code}')

            response_json = response.json()
            devices = response_json.get('payload', {}).get('data', [])

            return devices

    def api_get_source_datapoints(self, source, start: datetime, end: datetime, limit=100, page=1):
        self.ensure_is_authorized()

        url = self.get_device_history_url(device_id=source['device_id'], start=start, end=end, limit=limit, page=page)

        response = self.session.get(url)
        
        if response.status_code != 200:
            print(f'Error fetching data from {url}, Status Code: {response.status_code}, Response: {response.text}')
            return []

        try:
            response_json = response.json()
        except ValueError:
            print(f'Error decoding JSON from response: {response.text}')
            return []

        return response_json.get('payload', {}).get('data', [])

    def create_sensor_entry(self, device, specification_type, stat):
        return {
            'id': f"{device.get('deviceTag', '')}-{specification_type}",
            'name': device.get('settings', {}).get('name', ''),
            'specification_type': specification_type,
            'device_id': device.get('id', ''),
            'is_active': device.get('isActive', False),
            'owner': device.get('owner', ''),
            'power': device.get('power'),
            'settings': device.get('settings', {}) or {},
            'stat': stat,
            'created_at': self.parse_iso_timestamp(device.get('createdAt')),
            'updated_at': self.parse_iso_timestamp(device.get('updatedAt')),
        }

    def get_device_history_url(self, device_id: str, start: datetime = None, end: datetime = None, limit: int = 10, page: int = 1, filter_operator: str = 'and') -> str:
        params = {
            'limit': limit,
            'page': page,
            'filterOperator': filter_operator
        }
        if start:
            params['startDate'] = start.isoformat()
        if end:
            params['endDate'] = end.isoformat()
        query_string = urlencode(params)
        return f'{DEVICES_ENDPOINT}/{device_id}/history?{query_string}'
    
    def parse_iso_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        try:
            if timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                # If dt is naive, assume it's UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            return None
        except ValueError:
            return None
            
    def parse_timestamp(self, timestamp: Optional[int]) -> Optional[datetime]:
            return datetime.fromtimestamp(timestamp / 1000) if timestamp else None