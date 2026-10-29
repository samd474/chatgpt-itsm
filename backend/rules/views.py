from rest_framework.permissions import IsAuthenticated

from accounts.roles import ADMINISTRATOR, AUDITOR
from core.permissions import role_permission
from core.viewsets import AuditedModelViewSet

from .models import TicketRule
from .serializers import TicketRuleSerializer


class TicketRuleViewSet(AuditedModelViewSet):
    """Administrators manage ticket automation; auditors can review it."""

    serializer_class = TicketRuleSerializer
    permission_classes = [IsAuthenticated, role_permission(read_roles=(ADMINISTRATOR, AUDITOR), write_roles=(ADMINISTRATOR,))]
    queryset = TicketRule.objects.all()
    pagination_class = None
    audit_prefix = "config.ticket_rule"
