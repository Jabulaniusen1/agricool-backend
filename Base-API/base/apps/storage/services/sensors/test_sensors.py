import unittest

from base.apps.storage.models.cooling_unit import CoolingUnit
from base.settings import getEnv

from . import SensorIntegrationBase
from .figorr import FigorrIntegration
from .ubibot import UbibotIntegration
from .victron import VictronIntegration


class SensorsTest(unittest.TestCase):

    integrations = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cooling_unit = CoolingUnit.objects.first()

        if not cooling_unit:
            raise ValueError("No cooling unit found")

        integrations = [
            # EcozenIntegration(
            #     cooling_unit=cooling_unit,
            #     credentials={
            #         "username": getEnv("TEST_SENSORS_ECOZEN_USERNAME"),
            #         "password": getEnv("TEST_SENSORS_ECOZEN_PASSWORD"),
            #         "source_id": getEnv("TEST_SENSORS_ECOZEN_SOURCE_ID"),
            #     },
            # ) if getEnv("TEST_SENSORS_ECOZEN", None) else None,

            FigorrIntegration(
                cooling_unit=cooling_unit,
                credentials={
                    "username": getEnv("TEST_SENSORS_FIGORR_USERNAME"),
                    "password": getEnv("TEST_SENSORS_FIGORR_PASSWORD"),
                    "source_id": getEnv("TEST_SENSORS_FIGORR_SOURCE_ID"),
                },
            ) if getEnv("TEST_SENSORS_FIGORR", None) else None,

            # UbibotIntegration(
            #     cooling_unit=cooling_unit,
            #     credentials={
            #         "username": getEnv("TEST_SENSORS_UBIBOT_USERNAME"),
            #         "password": getEnv("TEST_SENSORS_UBIBOT_PASSWORD"),
            #         "source_id": getEnv("TEST_SENSORS_UBIBOT_SOURCE_ID"),
            #     },
            # ) if getEnv("TEST_SENSORS_UBIBOT", None) else None,

            VictronIntegration(
                cooling_unit=cooling_unit,
                credentials={
                    "username": getEnv("TEST_SENSORS_VICTRON_USERNAME"),
                    "password": getEnv("TEST_SENSORS_VICTRON_PASSWORD"),
                    "source_id": getEnv("TEST_SENSORS_VICTRON_SOURCE_ID"),
                },
            ) if getEnv("TEST_SENSORS_VICTRON", None) else None,
        ]

        # filter out None values
        self.integrations = [integration for integration in integrations if integration is not None]



    def test_integrations(self):
        for integration in self.integrations:
            self.assertIsNotNone(integration)
            self.assertIsInstance(integration, SensorIntegrationBase)

    def test_authorization(self):
        for integration in self.integrations:
            integration.authorize()
            self.assertTrue(integration.is_authorized())
            
    def test_listing_sources(self):
        for integration in self.integrations:
            source_id = integration.credentials['source_id']

            assert source_id is not None

            sources = integration.list_cached_sources()
            assert len(sources) > 0

            # sources include an object with the attributes: id, name, and other infos
            # this assert ensures that theres a source in the list that has the id, equal to the source_id
            source = next(source for source in sources if source['id'] == source_id)
            assert source['id'] == source_id

            source = integration.get_source(source_id)
            assert source['id'] == source_id


    def test_gathering_datums(self):
        for integration in self.integrations:
            source_id = integration.credentials['source_id']
            assert source_id is not None

            min_datetime = integration.get_min_datetime(source_id)

            datums = integration.get_datums_from_source(
                source_id=source_id,
                min_datetime=min_datetime,
            )

            assert len(datums) > 0
