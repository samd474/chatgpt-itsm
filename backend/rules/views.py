from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.roles import ADMINISTRATOR, AUDITOR
from core.permissions import role_permission
from core.viewsets import AuditedModelViewSet

from .models import TicketRule
from .preview import preview
from .serializers import TicketRuleSerializer
from .validation import validate_actions, validate_conditions


class TicketRuleViewSet(AuditedModelViewSet):
    """Administrators manage ticket automation; auditors can review it."""

    serializer_class = TicketRuleSerializer
    permission_classes = [IsAuthenticated, role_permission(read_roles=(ADMINISTRATOR, AUDITOR), write_roles=(ADMINISTRATOR,))]
    queryset = TicketRule.objects.all()
    pagination_class = None
    audit_prefix = "config.ticket_rule"

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """Dry run of a (possibly unsaved) rule against the most recent tickets. Changes nothing."""
        try:
            conditions = validate_conditions(request.data.get("conditions", {}))
            actions = validate_actions(request.data["actions"]) if request.data.get("actions") else {}
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})
        return Response(preview(conditions, actions))
