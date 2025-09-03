from django.contrib.auth.models import (
    Group,
    Permission,
)
from django.utils.functional import cached_property

# Error message constants
ERROR_INVALID_PERMISSION_STRING = "Invalid permissions string {perm_string}"

# Role names
ROLE_SERVICE_PROVIDER = "ServiceProvider"
ROLE_OPERATOR = "Operator"
ROLE_FARMER = "Farmer"

# Permission constants
PERMISSION_VIEW_ALL_USERS = "user.view_all_users"
PERMISSION_ADD_INVITATION_SERVICEPROVIDER = "user.add_invitation_serviceprovider"
PERMISSION_ADD_INVITATION_OPERATOR = "user.add_invitation_operator"
PERMISSION_VIEW_ALL_INVITATIONS = "user.view_all_invitations"
PERMISSION_VIEW_SERVICEPROVIDER_INVITATIONS = "user.view_serviceprovider_invitations"
PERMISSION_VIEW_OPERATOR_INVITATIONS = "user.view_operator_invitations"
PERMISSION_ADD_FARMER = "user.add_farmer"


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
                raise Exception(ERROR_INVALID_PERMISSION_STRING.format(perm_string=perm_string))
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
        name=ROLE_SERVICE_PROVIDER,
        permissions=(
            PERMISSION_VIEW_ALL_USERS,
            PERMISSION_ADD_INVITATION_SERVICEPROVIDER,
            PERMISSION_ADD_INVITATION_OPERATOR,
            PERMISSION_VIEW_ALL_INVITATIONS,
            PERMISSION_VIEW_SERVICEPROVIDER_INVITATIONS,
            PERMISSION_VIEW_OPERATOR_INVITATIONS,
            PERMISSION_ADD_FARMER,
        ),
    ),
    GroupConfig(
        name=ROLE_OPERATOR,
        permissions=(
            PERMISSION_ADD_FARMER,
            PERMISSION_VIEW_ALL_USERS,
        ),
    ),
    GroupConfig(
        name=ROLE_FARMER,
        permissions=[],
    ),
]
