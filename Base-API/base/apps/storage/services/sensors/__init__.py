import urllib.parse
from datetime import datetime, timezone
from typing import Generic, List, TypedDict, TypeVar

import requests
from django.db import transaction

from base.apps.storage.models.cooling_unit_specifications import \
  CoolingUnitSpecifications
from base.apps.user.models.notification import Notification

##
# Constants
##

MIN_DATETIME = datetime(2010, 1, 1, tzinfo=timezone.utc) # Selected 2010 as the minimum datetime for the events

# ###
# ## Sensory fns
# ###

# def __check_field(response, field):
#     for key, value in response["channel"].items():
#         if value == field:
#             return key
#     return


class SensorSource(TypedDict):
    id: str
    name: str
    specification_type: str

# Create a generic type variable for SensorSource
T = TypeVar("T", bound=SensorSource)

class SensorIntegrationBase(Generic[T]):
    AUTHORIZATION_HEADER = "Authorization"
    cached_sources = None

    ##
    # Common methods
    ##

    def __init__(self, cooling_unit, credentials):
        self.cooling_unit = cooling_unit
        self.credentials = credentials

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
        })

    def ensure_is_authorized(self):
        if self.is_authorized():
            return

        self.authorize()

    def is_authorized(self):
            return self.session.headers.get(self.AUTHORIZATION_HEADER) is not None

    def set_authorization(self, token):
        if token is not None:
            self.session.headers.update({self.AUTHORIZATION_HEADER: f"Bearer {token}"})
        else:
            self.session.headers.pop(self.AUTHORIZATION_HEADER, None)

    def get_latest_entry_on_db(self, specification_type="TEMPERATURE"):
        return (
            CoolingUnitSpecifications.objects
                .filter(
                    cooling_unit=self.cooling_unit,
                    specification_type=specification_type,
                )
                .order_by("-datetime_stamp")
                .first()
        ) or None

    def get_min_datetime(self, specification_type="TEMPERATURE"):
        lastest_entry = self.get_latest_entry_on_db(specification_type)
        return lastest_entry if lastest_entry is not None else MIN_DATETIME

    # Notifications
    @transaction.atomic
    def set_sensor_error_notifications(self):
        Notification.objects.update_or_create(
            event_type=Notification.NotificationType.SENSOR_ERROR, specific_id=self.cooling_unit.id
        )

    @transaction.atomic
    def clear_sensor_error_notifications(self):
        Notification.objects.filter(
            event_type=Notification.NotificationType.SENSOR_ERROR, specific_id=self.cooling_unit.id
        ).delete()

    @transaction.atomic
    def sync_with_source(self, source_id=None, specification_type="TEMPERATURE"):
        min_datetime = self.get_min_datetime(source_id)

        try:
            instances = self.get_datums_from_source(
                source_id=source_id, 
                min_datetime=min_datetime,
            )
        except:
            self.set_sensor_error_notifications()
            return

        # Save instances
        # CoolingUnitSpecifications.objects.bulk_create(instances)
        print(instances)

        # Clear notifications
        self.clear_sensor_error_notifications()

    def list_cached_sources(self) -> List[T]:
        if self.cached_sources is None:
            self.cached_sources = self.list_sources()

        return self.cached_sources

    def get_source(self, source_id: str) -> T:
        for source in self.list_cached_sources():
            if source['id'] == source_id:
                return source

        raise ValueError(f"Source with id {source_id} not found")

    def create_datum(
        self,
        source: T,
        value: float,
        timestamp: datetime,
        set_point_value = None,
    ) -> CoolingUnitSpecifications:

        if value is None:
            raise ValueError("Value cannot be None")

        if timestamp is None:
            raise ValueError("Timestamp cannot be None")

        return CoolingUnitSpecifications(
            value=value,
            set_point_value=set_point_value,
            datetime_stamp=timestamp,
            specification_type=source['specification_type'],
            cooling_unit=self.cooling_unit,
        )

    ##
    # Methods to be overridden
    ##

    def authorize(self) -> None:
        raise Exception("Not implemented")

    def get_datums_from_source(self, source_id=None, min_datetime=MIN_DATETIME) -> List[CoolingUnitSpecifications]:
        raise Exception("Not implemented")

    # dict with id, name, and
    def list_sources(self) -> List[T]:
        raise Exception("Not implemented")

def build_url(url, params=None):
    if params is None:
        return url

    # Manually format lists to use `[]` notation
    query_parts = []
    for key, value in params.items():
        if value is None:
            continue

        if isinstance(value, list):  # Handle lists correctly
            query_parts.extend([f"{urllib.parse.quote(key)}[]={urllib.parse.quote(str(v))}" for v in value])
        elif value is not None:  # Normal key-value pairs
            query_parts.append(f"{urllib.parse.quote(key)}={urllib.parse.quote(str(value))}")

    return f"{url}?{'&'.join(query_parts)}"
