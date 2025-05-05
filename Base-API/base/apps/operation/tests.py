from django.test import TestCase

from rest_framework.test import APIRequestFactory, force_authenticate

import time

import json

import random

from .views import CheckinViewSet, CheckoutViewSet

from base.apps.storage.models import Crate

from base.utils.tests import clean_client, DummyFactory


def get_checkin_payload(dummy_factory):
    payload = {
        "id": "undefined",
        "produces": json.dumps(
            [
                {
                    "crop": {"id": dummy_factory.crop.id},
                    "additional_info": str(time.time()),
                    "crates": [
                        {
                            "check_out": None,
                            "weight": 20,
                            "cooling_unit_id": dummy_factory.cooling_unit.id,
                            "planned_days": "2",
                        },
                        {
                            "check_out": None,
                            "weight": 10,
                            "cooling_unit_id": dummy_factory.cooling_unit.id,
                            "planned_days": "2",
                        },
                    ],
                    "harvest_date": -1,
                    "initial_grade": None,
                    "size": None,
                    "hasPicture": False,
                }
            ]
        ),
        "farmer_id": dummy_factory.user_farmer.id,
    }
    return payload


class CheckinViewSetTest(TestCase):

    def setUp(self):
        self.url = "/operation/checkins/"

        self.factory = APIRequestFactory()

        self.view_for_post = CheckinViewSet.as_view({"post": "create"})

        clean_client()

        self.dummy_instance = DummyFactory()

    def test_invalid_user_type_fail(self):

        # passing in wrong user time i.e !operator

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
            payload["farmer_id"] = random.randint(300, 400)

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
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data["farmer"], payload["farmer_id"])

    # def get_create_body(self):
    # not useful again
    #     """
    #     *** all must be same company
    #
    #     seed crop
    #
    #     create cooling unit
    #
    #     create farmer
    #
    #     assign cooling unit to a farmer
    #
    #     add to payload
    #
    #     # print("fields-list")
    #     # fields = self.user_company._meta.get_fields()
    #     # for field in fields:
    #     #     print('field-name', field.name)
    #
    #     """
    #
    #     self.user_company = get_client('service_provider')
    #
    #     company = self.user_company.service_provider.company
    #
    #     self.user_operator = baker.make('user.Operator', company=company, make_m2m=True)
    #
    #     location = baker.make('storage.Location', company=company)
    #
    #     cooling_unit = baker.make('storage.CoolingUnit',
    #                               operators=[self.user_operator.user], location=location, _fill_optional=True,
    #                               food_capacity_in_metric_tons=float(random.randint(1, 400)),
    #                               capacity_in_metric_tons=float(random.randint(1, 400)),
    #                               capacity_in_number_crates=random.randint(1, 400)
    #                               )
    #
    #     self.user_farmer = baker.make('user.Farmer', cooling_units=[cooling_unit],
    #                                   companies=[company], make_m2m=True)
    #
    #     crop_instance = baker.make('storage.Crop', crop_type=baker.make('storage.CropType'))
    #
    #     pricing = baker.make('storage.Pricing', _fill_optional=True)
    #
    #     cuc = baker.make('storage.CoolingUnitCrop', crop=crop_instance, cooling_unit=cooling_unit, pricing=pricing)
    #
    #     print("pricing created", cuc.pricing)
    #
    #     payload = {
    #         "id": "undefined",
    #         "produces": json.dumps([
    #             {
    #                 "crop": {"id": crop_instance.id},
    #                 "additional_info": str(time.time()),
    #                 "crates": [
    #                     {
    #                         "check_out": None,
    #                         "weight": 20,
    #                         "cooling_unit_id": cooling_unit.id,
    #                         "planned_days": "2"
    #                     },
    #                     {
    #                         "check_out": None,
    #                         "weight": 10,
    #                         "cooling_unit_id": cooling_unit.id,
    #                         "planned_days": "2"
    #                     }
    #                 ],
    #                 "harvest_date": -1,
    #                 "initial_grade": None,
    #                 "size": None,
    #                 "hasPicture": False
    #             }
    #         ]),
    #         "farmer_id": self.user_farmer.id
    #     }
    #
    #     return payload


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
        self.url = "/operation/checkouts/"

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

        self.assertEqual(200, 200)

        # check creates in the db then checkout

        user_crates = Crate.objects.filter(
            cooling_unit=dummy_instance.cooling_unit,
            check_out=None,
            produce__checkin__owned_by_user__farmer=dummy_instance.user_farmer,
        )

        payload = {
            "crates": [crate.id for crate in user_crates],
            "price_discount": 0,
            "currency": "NGN",
            "payment_type": "CASH",
            "paid": True,
        }

        user = dummy_instance.user_operator.user

        request = self.factory.post(self.url, data=payload)

        request.user = user

        force_authenticate(request, user=user)

        response = self.view_for_post(request)

        # check response status code

        self.assertEqual(response.status_code, 200)

    def create_checkin_situation(self, dummy_instance):
        """
        checkin a for a user
        """

        payload = get_checkin_payload(dummy_instance)

        url = "/operation/checkins/"

        factory = APIRequestFactory()

        view_for_post = CheckinViewSet.as_view({"post": "create"})

        request = factory.post(url, data=payload)

        request.user = dummy_instance.user_operator.user

        force_authenticate(request, user=dummy_instance.user_operator.user)

        view_for_post(request)


class CheckoutToCheckinViewSetTest(TestCase):

    def SetUp(selfs):
        pass

    def test_1(self):
        """
        list :
            Know what it does

            ??????

        """
        pass


class MarketSurveyViewSetTest(TestCase):

    def SetUp(selfs):
        pass

    def test(self):
        """
        list :

            survey returns expected

        """
        pass
