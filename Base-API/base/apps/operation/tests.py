from django.test import TestCase

from rest_framework.test import APIRequestFactory, force_authenticate

import time

import json

import random

from .views import CheckinViewSet, CheckoutViewSet

from base.apps.storage.models import Crate

from base.utils.tests import clean_client, DummyFactory

# Constants
UNDEFINED_ID = "undefined"
CHECKIN_URL = "/operation/checkins/"
CHECKOUT_URL = "/operation/checkouts/"
TEST_WEIGHT_LARGE = 20
TEST_WEIGHT_SMALL = 10
TEST_HARVEST_DATE_PLACEHOLDER = -1
TEST_PLANNED_DAYS = "2"
TEST_CURRENCY = "NGN"
TEST_PAYMENT_TYPE = "CASH"
INVALID_ID_RANGE_START = 300
INVALID_ID_RANGE_END = 400
HTTP_SUCCESS_STATUS = 200


def get_checkin_payload(dummy_factory):
    payload = {
        "id": UNDEFINED_ID,
        "produces": json.dumps(
            [
                {
                    "crop": {"id": dummy_factory.crop.id},
                    "additional_info": str(time.time()),
                    "crates": [
                        {
                            "check_out": None,
                            "weight": TEST_WEIGHT_LARGE,
                            "cooling_unit_id": dummy_factory.cooling_unit.id,
                            "planned_days": TEST_PLANNED_DAYS,
                        },
                        {
                            "check_out": None,
                            "weight": TEST_WEIGHT_SMALL,
                            "cooling_unit_id": dummy_factory.cooling_unit.id,
                            "planned_days": TEST_PLANNED_DAYS,
                        },
                    ],
                    "harvest_date": TEST_HARVEST_DATE_PLACEHOLDER,
                    "initial_grade": None,
                    "size": None,
                    "has_picture": False,
                }
            ]
        ),
        "farmer_id": dummy_factory.user_farmer.id,
    }
    return payload


class CheckinViewSetTest(TestCase):

    def setUp(self):
        self.url = CHECKIN_URL

        self.factory = APIRequestFactory()

        self.view_for_post = CheckinViewSet.as_view({"post": "create"})

        clean_client()

        self.dummy_instance = DummyFactory()

    def test_invalid_user_type_fail(self):

        # passing in wrong user type i.e !operator

        invalid_user_type = self.dummy_instance.user_farmer
        fails = False
        try:

            payload = get_checkin_payload(self.dummy_instance)

            user = invalid_user_type

            request = self.factory.post(self.url, data=payload)

            request.user = user

            force_authenticate(request, user=user)

            with self.assertRaises(Exception):
                fails = True
                response = self.view_for_post(request)
        except AssertionError:
            self.fail("Expected exception was not raised")
        # check response status code
        self.assertTrue(fails, "FAILS WITH INVALID USER")

    def test_invalid_data_fail(self):

        dummy_instance = self.dummy_instance
        user = dummy_instance.user_operator

        failed = True

        try:

            payload = get_checkin_payload(dummy_instance)

            # any random number will do
            payload["farmer_id"] = random.randint(INVALID_ID_RANGE_START, INVALID_ID_RANGE_END)

            request = self.factory.post(self.url, data=payload)

            request.user = user

            force_authenticate(request, user=user)

            with self.assertRaises(Exception):
                self.view_for_post(request)

        except AssertionError:
            failed = False
            self.fail("Expected exception was not raised")
        self.assertTrue(failed, "FAILS WITH INVALID DATA")

    def test_checkin_success(self):
        dummy_instance = self.dummy_instance

        payload = get_checkin_payload(dummy_instance)

        user = dummy_instance.user_operator.user

        request = self.factory.post(self.url, data=payload)

        request.user = user

        force_authenticate(request, user=user)

        response = self.view_for_post(request)

        # check response status code
        self.assertEqual(response.status_code, HTTP_SUCCESS_STATUS)

        self.assertEqual(response.data["farmer"], payload["farmer_id"])


class MovementViewSetTest(TestCase):

    def setUp(self):
        pass

    def tests(self):
        """
        list  :
            create multiple scenarios

            ensure expected results are given

            add to POSTMAN

        """
        pass


class CheckoutViewSetTest(TestCase):

    def setUp(self):
        self.url = CHECKOUT_URL

        self.factory = APIRequestFactory()

        self.view_for_post = CheckoutViewSet.as_view({"post": "create"})

        clean_client()

    def tests(self):
        """
        list :

            checkout NONE existent

            checkout what does not belong to you

            is math , mathing ?

        """
        pass

    def test_checkout_success(self):
        dummy_instance = DummyFactory()

        self.create_checkin_situation(dummy_instance)

        self.assertEqual(HTTP_SUCCESS_STATUS, HTTP_SUCCESS_STATUS)

        # check creates in the db then checkout

        user_crates = Crate.objects.filter(
            cooling_unit=dummy_instance.cooling_unit,
            check_out=None,
            produce__checkin__owned_by_user__farmer=dummy_instance.user_farmer,
        )

        payload = {
            "crates": [crate.id for crate in user_crates],
            "price_discount": 0,
            "currency": TEST_CURRENCY,
            "payment_type": TEST_PAYMENT_TYPE,
            "paid": True,
        }

        user = dummy_instance.user_operator.user

        request = self.factory.post(self.url, data=payload)

        request.user = user

        force_authenticate(request, user=user)

        response = self.view_for_post(request)

        # check response status code

        self.assertEqual(response.status_code, HTTP_SUCCESS_STATUS)

    def create_checkin_situation(self, dummy_instance):
        """
        checkin a for a user
        """

        payload = get_checkin_payload(dummy_instance)

        url = CHECKIN_URL

        factory = APIRequestFactory()

        view_for_post = CheckinViewSet.as_view({"post": "create"})

        request = factory.post(url, data=payload)

        request.user = dummy_instance.user_operator.user

        force_authenticate(request, user=dummy_instance.user_operator.user)

        view_for_post(request)


class CheckoutToCheckinViewSetTest(TestCase):

    def setUp(self):
        pass

    def test_1(self):
        """
        list :
            Know what it does

            ??????

        """
        pass


class MarketSurveyViewSetTest(TestCase):

    def setUp(self):
        pass

    def test(self):
        """
        list :

            survey returns expected

        """
        pass
