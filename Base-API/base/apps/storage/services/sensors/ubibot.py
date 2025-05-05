import hashlib
from datetime import datetime, timezone
from typing import List, Optional, TypedDict
from urllib.parse import urlencode

from . import MIN_DATETIME, CoolingUnitSpecifications, SensorIntegrationBase

##
# Constants
##
API_ENDPOINT = 'https://api-cdn.ubibot.com'
AUTH_ENDPOINT = API_ENDPOINT + '/accounts/login'
GET_ALL_CHANNELS_ENDPOINT = API_ENDPOINT + '/channels'
GET_CHANNEL_PARTIAL_ENDPOINT = '/summary.json'

CONTENT_TYPE_HEADER = { 'Content-Type': 'application/x-www-form-urlencoded' }

FIELD_TYPE_MAPPING = {
    '\u6e29\u5ea6': 'TEMPERATURE',  # 温度
    '\u6e7f\u5ea6': 'HUMIDITY',     # 湿度
}

class UbibotSensorSource(TypedDict):
    id: str
    name: str
    specification_type: str
    channel_id: str
    last_seen_at: Optional[datetime]
    fields: dict
    latitude: Optional[float]
    longitude: Optional[float]
    created_at: datetime
    updated_at: datetime


class UbibotIntegration(SensorIntegrationBase):
    SensorSourceType = UbibotSensorSource

    def authorize(self) -> None:
        with self.session as ses:
            payload = {
                'username': self.credentials['username'],
                'password': self.hash_password(self.credentials['password']),
                'enable_2fa': 'false',
                'expire_in_seconds': '2592000',
                'password_type': 'sha256',
            }

            response = ses.post(AUTH_ENDPOINT, data=payload, headers=CONTENT_TYPE_HEADER)

            if response.status_code == 401:
                raise Exception('Error: Invalid username or password')

            if response.status_code != 200:
                raise Exception(f'Error: Unable to authorize with Ubibot. Status code: {response.status_code}, Response: {response.text}')

        res_body_json = response.json()

        if res_body_json.get('result') != 'success':
            raise Exception(f'Error: API responded with an unsuccessful result: {res_body_json}')

        account_info = res_body_json.get('account', {})
        self.user_id = account_info.get('user_id')

        token_id = res_body_json.get('token_id')
        if not token_id:
            raise Exception('Error: Missing token_id in API response.')

        self.set_authorization(token_id)

    def list_sources(self) -> List[UbibotSensorSource]:
        self.ensure_is_authorized()

        token_id = self.session.headers.get(self.AUTHORIZATION_HEADER).replace('Bearer ', '')
        url = f'{GET_ALL_CHANNELS_ENDPOINT}?token_id={token_id}'

        response = self.session.get(url)

        if response.status_code != 200:
            raise Exception(f'Error fetching channels from Ubibot. Status Code: {response.status_code}, Response: {response.text}')

        res_body_json = response.json()
        if res_body_json.get('result') != 'success':
            raise Exception(f'Error: API responded with an unsuccessful result: {res_body_json}')

        sources = []
        for channel in res_body_json.get("channels", []):
            channel_id = channel.get("channel_id")
            name = channel.get("name", "Unknown Channel")

            fields = {f'field{i}': channel.get(f'field{i}') for i in range(1, 11) if channel.get(f'field{i}')}
            latitude, longitude = map(lambda x: float(x) if x else None, [channel.get('latitude'), channel.get('longitude')])
            created_at = self.parse_iso_timestamp(channel.get('created_at'))
            updated_at = self.parse_iso_timestamp(channel.get('updated_at'))
            last_seen_at = self.parse_iso_timestamp(channel.get('last_entry_date'))

            for sensor_type, tag in [("TEMPERATURE", CoolingUnitSpecifications.SpecificationType.TEMPERATURE), ("HUMIDITY", CoolingUnitSpecifications.SpecificationType.HUMIDITY)]:
                sensor_field = next((k for k, v in fields.items() if FIELD_TYPE_MAPPING.get(v) == sensor_type), None)
                if sensor_field:
                    sources.append({
                        'id': f"{channel_id}-{tag}",
                        'name': name,
                        'specification_type': tag,
                        'channel_id': channel_id,
                        'last_seen_at': last_seen_at,
                        'fields': {sensor_field: fields[sensor_field]},
                        'latitude': latitude,
                        'longitude': longitude,
                        'created_at': created_at,
                        'updated_at': updated_at
                    })

        return sources


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

        data = self.api_get_source_datapoints(source.get('channel_id'), start=min_datetime, end=now)

        field_map = {
            FIELD_TYPE_MAPPING.get(v, v): k
            for k, v in source.get("fields", {}).items()
            if v in FIELD_TYPE_MAPPING
        }

        datums = []

        for entry in data:
            timestamp = self.parse_iso_timestamp(entry.get('created_at'))
            if not timestamp:
                continue

            if source.get('specification_type') == CoolingUnitSpecifications.SpecificationType.TEMPERATURE:
                value = entry.get(field_map.get("TEMPERATURE", ""), {}).get('avg')
            else:
                value = entry.get(field_map.get("HUMIDITY", ""), {}).get('avg')

            if value is None:
                continue

            datums.append(
                self.create_datum(
                    source=source,
                    value=value,
                    timestamp=timestamp,
                    set_point_value=None,
                )
            )

        return datums


    # Custom methods
    def api_get_source_datapoints(self, source_id, start: datetime, end: datetime, results=100) -> List[dict]:
        self.ensure_is_authorized()

        token_id = self.session.headers.get(self.AUTHORIZATION_HEADER).replace('Bearer ', '')
        params = {
            'token_id': token_id,
            'start': start.isoformat(),
            'end': end.isoformat(),
            'results': results
        }

        url = f'{GET_ALL_CHANNELS_ENDPOINT}/{source_id}{GET_CHANNEL_PARTIAL_ENDPOINT}?{urlencode(params)}'

        response = self.session.get(url)

        if response.status_code != 200:
            raise Exception(f'Error fetching data from {url}, Status Code: {response.status_code}, Response: {response.text}')

        res_body_json = response.json()

        if res_body_json.get('result') != 'success':
            raise Exception(f'Error: API responded with an unsuccessful result: {res_body_json}')

        return res_body_json.get('feeds', [])

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

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
