from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.roles import ADMINISTRATOR, has_role


class IsAdministrator(BasePermission):
    message = "Administrator access is required."

    def has_permission(self, request, view):
        return has_role(request.user, ADMINISTRATOR)


def role_permission(read_roles, write_roles):
    """Permission class: SAFE methods need one of read_roles, others one of write_roles.

    Superusers count as Administrators (see accounts.roles.has_role).
    """

    class RolePermission(BasePermission):
        message = "Your role does not allow this action."

        def has_permission(self, request, view):
            roles = read_roles if request.method in SAFE_METHODS else write_roles
            return has_role(request.user, *roles)

    return RolePermission
