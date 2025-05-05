from django.test import TestCase
from django.contrib import auth

from django.test.client import RequestFactory

from rest_framework.test import APIRequestFactory, force_authenticate

import random

from .models import User, InvitationUser

from .views import ServiceProviderRegistrationViewSet, InviteOperatorViewSet

from base.utils.tests import clean_client, DummyFactory


class AuthTestCase(TestCase):
    def setUp(self):
        self.u = User.objects.create_user("test@dom.com", "pass")
        self.u.is_staff = True
        self.u.is_superuser = True
        self.u.is_active = True
        self.u.save()

    def testLogin(self):
        self.client.login(username="test@dom.com", password="pass")


def get_operator_invite_payload(cooling_units):
    random_number = "".join(str(random.randint(0, 9)) for _ in range(8))

    payload = {
        "phone": f"+9170{random_number}",
        "cooling_units": cooling_units,
        "partOne": "localhost ",
        "urlOne": "localhost ",
        "urlTwo": f"&phoneNumber=+9170{random_number}",
    }
    return payload


class InviteOperatorViewSetTest(TestCase):
    def setUp(self):
        self.url = "/user/v1/operator-invite/"

        self.factory = APIRequestFactory()

        self.view_for_post = InviteOperatorViewSet.as_view({"post": "create"})

        clean_client()

        self.dummy_instance = DummyFactory()

    def test_operator_invite(self):
        """
        can invite operator successfully
        """

        user = self.dummy_instance.user_company

        payload = get_operator_invite_payload([self.dummy_instance.cooling_unit.id])

        request = self.factory.post(self.url, data=payload)

        request.user = user

        print(user)

        force_authenticate(request, user=user)

        response = self.view_for_post(request)

        print(response)

        self.assertEqual(response.status_code, 200)

        # check db values align

        invited_user = InvitationUser.objects.get(
            phone=payload["phone"], user_type=2, sender=user
        )

        print("check here now-->", invited_user.code)

        self.assertIsNotNone(invited_user, "invitation sent")

        """

        Check can accept invitation and sign up

        """


class ServiceProviderRegistrationViewSetTest(TestCase):

    def setUp(self):
        clean_client()

        self.url = "/user/v1/service-provider-signup/"

        self.factory = RequestFactory()

        self.view_for_post = ServiceProviderRegistrationViewSet.as_view(
            {"post": "create"}
        )

    def test_signup(self):
        return
        pass
        """
        send incomplete data
        """
        body_1 = self.get_create_body()

        # remove a required field
        del body_1["user"]["password"]

        request = self.factory.post(self.url, body_1)

        response = self.view_for_post(request)

        # check response status code
        self.assertEqual(response.status_code, 400)
        """
        pass in complete useful data
        """
        body_2 = self.get_create_body()
        request = self.factory.post(self.url, body_2)

        response = self.view_for_post(request)

        # check response status code
        print("status code returned", response.status_code)
        print("response gotten", response.data)
        # print()

        self.assertEqual(response.status_code, 200)

        """
        ensure new user cannot be created with existing
        """

        # repeating same request

        response = self.view_for_post(request)
        # check response status code
        self.assertNotEqual(response.status_code, 200)

    def get_create_body(self):
        # TODO remove hard coding

        payload = {
            "user": {
                "first_name": "Ebube",
                "last_name": "testing",
                "gender": "ma",
                "phone": "+917098485868",
                "email": "ezeebube16@gmail.com",
                "password": "Testing@123",
            },
            "company": {
                "name": "second-company-126",
                "country": "IN",
                "currency": "INR",
                "language": "ENG",
                "crop": [],
            },
        }

        return payload
