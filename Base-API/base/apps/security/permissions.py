from rest_framework.permissions import BasePermission

# Default permission values
DEFAULT_PERMISSIONS = []


class PermissionsRequired(BasePermission):
    """Permission class for checking if a user has the required django permissions. The view class should have a
    `permissions` attribute that is a list of permission names required for the user to access the view. This permission
    class checks if the user is authenticated first. If the user is not authenticated, the user will NOT be allowed
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        required_permissions = getattr(view, "permissions", DEFAULT_PERMISSIONS)
        required_permissions = required_permissions + getattr(
            view, "permissions_" + str(request.method.lower()), DEFAULT_PERMISSIONS
        )
        return request.user.has_perms(required_permissions)
