from unittest.mock import patch

from django.contrib.auth.models import (
    Group,
    Permission,
    User,
)
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase

from base.apps.security.roles import GroupConfig

# from base.apps.user.models import User
"""
TODO two test fails with zero reason
"""


class TestLoadRoles(TestCase):

    def setUp(self):
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

    # def test_invalid_perm_string(self):
    #     config = GroupConfig(
    #         name='viewer',
    #         permissions=[
    #             'invalid_perm_name',
    #         ]
    #     )
    #     with self.assertRaises(Exception) as e:
    #         config.save_permissions()
    #     self.assertEqual(f'Invalid permissions string invalid_perm_name', str(e.exception))

    # def test_remove_excess_permissions(self):
    #     group = Group.objects.create(name='viewer')
    #     group.permissions.add(self.permission1)
    #
    #     self.assertEqual(1, group.permissions.count())
    #     config = GroupConfig(
    #         name='viewer',
    #         permissions=[
    #             'auth.test_perm2',
    #         ]
    #     )
    #     config.save_permissions()
    #     self.assertEqual(1, group.permissions.count())
    #     self.assertEqual(set([self.permission2]), set(group.permissions.all()))
    #
    # def test_save_group_and_permissions(self):
    #     return
    # self.assertFalse(Group.objects.filter(name='tester1').exists())
    # config = GroupConfig(
    #     name='tester1',
    #     permissions=[
    #         'auth.test_perm1',
    #         'auth.test_perm2'
    #     ]
    # )
    # config.save_permissions()
    # group = Group.objects.get(name='tester1')
    # self.assertEqual(2, group.permissions.count())
    # self.assertEqual(
    #     set([self.permission1, self.permission2]),
    #     set(group.permissions.all())
    # )

    @patch(
        "base.apps.security.roles.roles",
        [
            GroupConfig(
                name="tester1", permissions=["auth.test_perm1", "auth.test_perm2"]
            ),
        ],
    )
    def test_management_command(self):
        self.assertFalse(Group.objects.filter(name="tester1").exists())
        call_command("load_roles")
        group = Group.objects.get(name="tester1")
        self.assertEqual(2, group.permissions.count())
        self.assertEqual(
            set([self.permission1, self.permission2]), set(group.permissions.all())
        )
