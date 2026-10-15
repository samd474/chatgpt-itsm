from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import User
from accounts.roles import AUDITOR, REQUESTER, has_role, is_staff_user


class NotReadOnlyAuditor(BasePermission):
    """Auditors may read approved data but never mutate operational records."""

    message = "Auditors have read-only access."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if not isinstance(user, User):
            return False
        if has_role(user, AUDITOR) and not (is_staff_user(user) or has_role(user, REQUESTER) or user.is_superuser):
            return False
        return True


class CanExportHelpRequests(BasePermission):
    message = "You do not have permission to export help requests."

    def has_permission(self, request, view):
        user = request.user
        return isinstance(user, User) and user.has_perm("helprequests.export_helprequests")
