from rest_framework.permissions import IsAuthenticated

from accounts.roles import ADMINISTRATOR
from .permissions import role_permission
from .serializers import CustomFieldDefinitionSerializer
from .models import CustomFieldDefinition
from .viewsets import AuditedModelViewSet

ALL_ROLES = ("Requester", "Technician", "Manager", "Administrator", "Auditor")


class CustomFieldDefinitionViewSet(AuditedModelViewSet):
    """Everyone can read active definitions (forms need them); administrators manage them."""

    serializer_class = CustomFieldDefinitionSerializer
    permission_classes = [IsAuthenticated, role_permission(read_roles=ALL_ROLES, write_roles=(ADMINISTRATOR,))]
    pagination_class = None
    filterset_fields = ["entity", "active"]
    audit_prefix = "config.custom_field"

    def get_queryset(self):
        from accounts.roles import is_admin, is_staff_user

        qs = CustomFieldDefinition.objects.all()
        user = self.request.user
        if is_admin(user):
            return qs
        qs = qs.filter(active=True)
        if not is_staff_user(user):
            qs = qs.filter(entity=CustomFieldDefinition.Entity.TICKET, visible_to_requester=True)
        return qs
