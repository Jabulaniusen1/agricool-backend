from unittest.mock import MagicMock

from django.contrib.auth.models import (
    AnonymousUser,
    Permission,
)
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from base.apps.security.permissions import PermissionsRequired

from base.apps.user.models import User


class FakeView:

    def __init__(self, permissions=None, permissions_post=None):
        if permissions:
            self.permissions = permissions

        if permissions_post:
            self.permissions_post = permissions_post


# Todo : remove this comment left behind - EBUBE

"""
error found here:
    User is imported from django default auth models
    but it was replaced with a custom version  

    in the model , saw email but it has username in test
    not sure which should be accepted but went with email


    the permission needed to be changed from auth. to user.
    i do not know why , after logging that is what was seen

"""


class TestPermissionsClass(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="sample@email.com", password="123")
        self.permission = PermissionsRequired()
        self.request = MagicMock(user=self.user, method="GET")

        content_type = ContentType.objects.get_for_model(User)
        self.permission1 = Permission.objects.create(
            codename="test_perm1",
            name="Test Permission 1",
            content_type=content_type,
        )
        self.permission2 = Permission.objects.create(
            codename="test_perm2",
            name="Test Permission 2",
            content_type=content_type,
        )

    def test_missing_permissions(self):
        self.assertFalse(
            self.permission.has_permission(
                self.request,
                FakeView(permissions=["user.test_perm1", "user.test_perm2"]),
            )
        )

    def test_has_permissions(self):
        self.user.user_permissions.add(self.permission1, self.permission2)
        self.assertTrue(
            self.permission.has_permission(
                self.request,
                FakeView(permissions=["user.test_perm1", "user.test_perm2"]),
            )
        )

    def test_method_specific_permissions(self):
        fake_view = FakeView(
            permissions=["user.test_perm1"], permissions_post=["user.test_perm2"]
        )
        self.user.user_permissions.add(self.permission1)
        self.assertTrue(self.permission.has_permission(self.request, fake_view))
        self.assertFalse(
            self.permission.has_permission(
                MagicMock(user=self.user, method="POST"), fake_view
            )
        )
        self.user.user_permissions.add(self.permission2)
        self.user = User.objects.get(id=self.user.id)
        self.assertTrue(
            self.permission.has_permission(
                MagicMock(user=self.user, method="POST"), fake_view
            )
        )

    def test_not_authenticated_user(self):
        request = MagicMock(user=AnonymousUser(), method="GET")
        self.assertFalse(
            self.permission.has_permission(request, FakeView(permissions=[]))
        )
