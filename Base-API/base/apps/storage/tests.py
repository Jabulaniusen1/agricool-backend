from django.test import TestCase

from rest_framework.test import force_authenticate

from django.test.client import RequestFactory

from .models import Location, Crop
from .views import CropTypeViewSet, CoolingUnitViewSet

from base.utils.tests import (
    seed,
    purge,
    clean_client,
    get_client,
    crop_names,
    DummyFactory,
)

import time


class CropTypeViewSetTest(TestCase):

    def setUp(self):
        self.url = "/storage/v1/crop-list"

        self.factory = RequestFactory()
        self.view_for_get = CropTypeViewSet.as_view({"get": "list"})

        seed("crop-type")

    def test_get_crop_type(self):
        request = self.factory.get(self.url)

        response = self.view_for_get(request)

        # check response status code
        self.assertEqual(response.status_code, 200)

        # check response data
        response_data = response.data

        # check response data length
        self.assertEqual(len(response_data), len(crop_names))

        # check response data content
        crop_type_names = [crop["name"] for crop in response_data]
        self.assertCountEqual(crop_type_names, crop_names)

        purge()


class CropViewSetTest(TestCase):

    def setUp(self):
        pass


class CoolingUnitViewSetTest(TestCase):

    def setUp(self):

        self.url = "/storage/v1/cooling-unit/"

        self.factory = RequestFactory()

        self.view_for_post = CoolingUnitViewSet.as_view({"post": "create"})

        self.view_for_get = CoolingUnitViewSet.as_view({"get": "list"})

        clean_client()

        self.user = get_client("service_provider")

        self.dummy_instance = DummyFactory()

        seed("location")

    def test_create_cooling_unit_fail(self):

        payload = self.get_create_payload(self.dummy_instance)

        fails = False

        try:
            # remove required field
            del payload["location"]

            request = self.factory.post(self.url, data=payload)

            request.user = self.dummy_instance.user_company

            force_authenticate(request, user=self.dummy_instance.user_company)

            with self.assertRaises(Exception):
                fails = True
                response = self.view_for_post(request)
        except AssertionError:
            self.fail("Expected exception was not raised")

        self.assertTrue(fails, "FAILS WITH INADEQUATE DATA")

    def test_cooling_unit_success(self):
        """
        TEST create cooling unit
        """

        self.user = self.dummy_instance.user_company

        payload = self.get_create_payload(self.dummy_instance)

        request = self.factory.post(self.url, data=payload)

        request.user = self.user

        force_authenticate(request, user=self.user)

        response = self.view_for_post(request)

        # check response status code
        self.assertEqual(response.status_code, 200)

        # check response data
        response_data = response.data

        self.assertEqual(response_data["name"], payload["name"])

        """
        TEST get cooling units
        """

        # TODO : might include company
        request = self.factory.get(self.url)

        request.user = self.user

        response = self.view_for_get(request)

        # check response status code
        self.assertEqual(response.status_code, 200)

        # check response data
        response_data_get = response.data

        saved = False
        for cooling_unit in response_data_get:
            if cooling_unit["id"] == response_data["id"]:
                saved = True
                break

        self.assertEqual(saved, True)

        purge()

    def get_create_payload(self, dummy_instance):

        # Values have zero significance here
        payload = {
            "name": "name-" + str(time.time()),
            "location": dummy_instance.location.id,
            "metric": "CRATES",
            "capacity_in_number_crates": 20,
            "capacity_in_metric_tons": 20,
            "food_capacity_in_metric_tons": 30,
            "fixed_price": False,
            "price": 3000,
            "sensor": False,
            "public": False,
            "sensor_data": "",
            "operators": [],
            "crops": [int(crop.id) for crop in Crop.objects.all()],
            "crate_weight": 25,
            "cooling_unit_type": "FARM_GATE_STORAGE_ROOM",
        }

        return payload

    def get_create_body(self):
        # Values have zero significance here
        payload = {
            "name": "testing-random-name",
            "location": Location.objects.first().id,
            "metric": "CRATES",
            "capacity_in_number_crates": 20,
            "capacity_in_metric_tons": 20,
            "food_capacity_in_metric_tons": 30,
            "fixed_price": False,
            "price": 3000,
            "sensor": False,
            "public": False,
            "sensor_data": "",
            "operators": [],
            "crops": [100],
            "crate_weight": 25,
            "cooling_unit_type": "FARM_GATE_STORAGE_ROOM",
        }

        return payload
