from datetime import datetime

from django.utils.dateparse import parse_datetime
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.roles import ADMINISTRATOR, AUDITOR, MANAGER, TECHNICIAN
from core.numbering import assign_number
from core.permissions import role_permission
from core.viewsets import AuditedModelViewSet
from helprequests.access import visible_HelpRequests
from helprequests.models import HelpRequests
from reports.audit import write_audit_event

from . import services
from .filters import ChangeFilter
from .models import ChangeApproval, ChangeRequest
from .serializers import ChangeApprovalSerializer, ChangeDecisionSerializer, ChangeRequestSerializer, ChangeTransitionSerializer

ChangeAccess = role_permission(read_roles=(TECHNICIAN, MANAGER, ADMINISTRATOR, AUDITOR), write_roles=(TECHNICIAN, MANAGER, ADMINISTRATOR))


class ChangeRequestViewSet(AuditedModelViewSet):
    serializer_class = ChangeRequestSerializer
    permission_classes = [IsAuthenticated, ChangeAccess]
    audit_prefix = "change"
    http_method_names = ["get", "post", "patch", "head", "options"]  # cancel instead of delete
    filterset_class = ChangeFilter
    search_fields = ["number", "title", "description"]
    ordering_fields = ["created_at", "planned_start", "updated_at"]

    def get_queryset(self):
        return ChangeRequest.objects.select_related("requested_by", "implementer", "service").prefetch_related(
            "approvals__approver", "assets", "help_requests",
        ).annotate(conflict_total=services.conflict_count_subquery())

    def _check_tickets(self, serializer):
        tickets = serializer.validated_data.get("help_requests") or []
        if tickets:
            visible = visible_HelpRequests(self.request.user, HelpRequests.objects.filter(pk__in=[t.pk for t in tickets]))
            if visible.count() != len({t.pk for t in tickets}):
                raise ValidationError({"help_requests": "One or more tickets were not found."})

    def perform_create(self, serializer):
        self._check_tickets(serializer)
        change = serializer.save(requested_by=self.request.user)
        assign_number(change, "CHG")
        write_audit_event(self.request, "change.created", obj=change, before={}, after=self._snapshot(change))

    def perform_update(self, serializer):
        change = serializer.instance
        user = self.request.user
        manager = services.is_change_manager(user)
        planning_fields = {"planned_start", "planned_end", "implementer"}
        if change.status in services.EDITABLE_STATUSES:
            if not (change.requested_by_id == user.pk or manager):
                raise PermissionDenied("Only the requester or a change manager can edit this change.")
        elif change.status in (ChangeRequest.Status.APPROVED, ChangeRequest.Status.SCHEDULED):
            # After approval the content is frozen; managers may only adjust scheduling.
            if not manager or not set(serializer.validated_data) <= planning_fields:
                raise PermissionDenied("Approved changes are locked except for scheduling by a change manager.")
            if change.status == ChangeRequest.Status.SCHEDULED:
                raise PermissionDenied("Move the change back to approved before rescheduling.")
        else:
            raise PermissionDenied("This change can no longer be edited.")
        self._check_tickets(serializer)
        super().perform_update(serializer)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        change = self.get_object()
        serializer = ChangeTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        change = services.transition(
            change, new_status=serializer.validated_data["status"], actor=request.user, request=request,
            outcome=serializer.validated_data.get("outcome"), closure_notes=serializer.validated_data.get("closure_notes"),
        )
        return Response(self.get_serializer(self.get_queryset().get(pk=change.pk)).data)

    @action(detail=True, methods=["get"])
    def conflicts(self, request, pk=None):
        change = self.get_object()
        clashes = services.conflicts(change).select_related("requested_by", "implementer")
        return Response([{"id": c.pk, "number": c.number, "title": c.title, "status": c.status,
                          "planned_start": c.planned_start, "planned_end": c.planned_end} for c in clashes])

    @action(detail=False, methods=["get"])
    def calendar(self, request):
        start = parse_datetime(request.query_params.get("start", "") or "")
        end = parse_datetime(request.query_params.get("end", "") or "")
        if not isinstance(start, datetime) or not isinstance(end, datetime) or end <= start:
            raise ValidationError({"detail": "Pass ISO start and end datetimes."})
        if (end - start).days > 120:
            raise ValidationError({"detail": "The calendar range is limited to 120 days."})
        changes = ChangeRequest.objects.filter(
            planned_start__lt=end, planned_end__gt=start,
        ).exclude(status__in=[ChangeRequest.Status.CANCELLED, ChangeRequest.Status.REJECTED, ChangeRequest.Status.DRAFT])
        return Response([{"id": c.pk, "number": c.number, "title": c.title, "status": c.status, "risk": c.risk,
                          "change_type": c.change_type, "planned_start": c.planned_start, "planned_end": c.planned_end}
                         for c in changes.order_by("planned_start")])


class ChangeApprovalViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Change approvals assigned to the current user."""

    serializer_class = ChangeApprovalSerializer
    filterset_fields = ["state"]

    def get_queryset(self):
        return ChangeApproval.objects.filter(approver=self.request.user).select_related("change", "approver")

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        approval = self.get_queryset().filter(pk=pk).first()
        if approval is None:
            raise ValidationError({"detail": "Approval not found."})
        serializer = ChangeDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approval = services.decide(approval, actor=request.user, state=serializer.validated_data["state"],
                                   comment=serializer.validated_data["comment"], request=request)
        return Response(ChangeApprovalSerializer(approval).data)
