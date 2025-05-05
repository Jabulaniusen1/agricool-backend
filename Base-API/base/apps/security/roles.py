from django.contrib.auth.models import (
    Group,
    Permission,
)
from django.utils.functional import cached_property


class GroupConfig:

    def __init__(self, name, permissions):
        self.name = name
        self.permissions = permissions

    def save_group(self):
        """Create a new Group if it does not exist yet, returns the group"""
        group, created = Group.objects.get_or_create(name=self.name)
        return group

    @cached_property
    def group(self):
        print("group actually been created")
        return self.save_group()

    def save_permissions(self):
        """Attach the permissions to the group"""
        permission_objects = set()
        for perm_string in self.permissions:
            try:
                app_label, code = perm_string.split(".")
            except ValueError:
                raise Exception(f"Invalid permissions string {perm_string}")
            permission_objects.add(
                Permission.objects.get(content_type__app_label=app_label, codename=code)
            )

        existing_perms = set(self.group.permissions.all())
        removed_perms = existing_perms - permission_objects
        new_perms = permission_objects - existing_perms
        self.group.permissions.remove(*removed_perms)
        self.group.permissions.add(*new_perms)


roles = [
    # add a list of GroupConfig here, e.g.
    # GroupConfig(
    #     name='tester',
    #     permissions=(
    #         'auth.view_user',
    #         'auth.view_group',
    #     )
    # ),
    GroupConfig(
        name="ServiceProvider",
        permissions=(
            "user.view_all_users",
            "user.add_invitation_serviceprovider",
            "user.add_invitation_operator",
            "user.view_all_invitations",
            "user.view_serviceprovider_invitations",
            "user.view_operator_invitations",
            "user.add_farmer",
        ),
    ),
    GroupConfig(
        name="Operator",
        permissions=(
            "user.add_farmer",
            "user.view_all_users",
        ),
    ),
    GroupConfig(
        name="Farmer",
        permissions=[],
    ),
]
