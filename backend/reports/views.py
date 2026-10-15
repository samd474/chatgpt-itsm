from datetime import timedelta

from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from accounts.roles import ADMINISTRATOR, AUDITOR, MANAGER, has_role
from helprequests.access import visible_HelpRequests
from helprequests.models import HelpRequests

from core.permissions import IsAdministrator

from . import imports
from .audit import write_audit_event
from .models import AuditEvent, ExportJob, ImportJob
from .serializers import AuditEventSerializer, ExportJobSerializer, ImportJobSerializer


class IsAuditReader(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, AUDITOR, ADMINISTRATOR)


class IsReportReader(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, MANAGER, ADMINISTRATOR)


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only by design: there are no update or delete endpoints for audit data."""

    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated, IsAuditReader]
    queryset = AuditEvent.objects.select_related("initiated_by")
    filterset_fields = ["activity_type", "object_type", "object_id", "initiated_by", "request_id"]
    search_fields = ["activity_type", "object_id", "request_id"]
    ordering_fields = ["created_at"]


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsReportReader])
def service_desk_report(request):
    tickets = visible_HelpRequests(request.user, HelpRequests.objects.all())
    open_tickets = tickets.filter(status__in=HelpRequests.OPEN_STATUSES)
    now = timezone.now()

    breached = Q(sla__response_breached=True) | Q(sla__resolution_breached=True)
    age_buckets = {
        "under_1_day": open_tickets.filter(created_at__gte=now - timedelta(days=1)).count(),
        "1_to_3_days": open_tickets.filter(created_at__lt=now - timedelta(days=1), created_at__gte=now - timedelta(days=3)).count(),
        "3_to_7_days": open_tickets.filter(created_at__lt=now - timedelta(days=3), created_at__gte=now - timedelta(days=7)).count(),
        "over_7_days": open_tickets.filter(created_at__lt=now - timedelta(days=7)).count(),
    }
    return Response({
        "open_tickets": open_tickets.count(),
        "unassigned": open_tickets.filter(technician__isnull=True).count(),
        "sla_at_risk": open_tickets.filter(sla__warning_sent_at__isnull=False).exclude(breached).count(),
        "sla_breached": open_tickets.filter(breached).count(),
        "by_priority": {f"P{row['priority']}": row["n"] for row in open_tickets.values("priority").annotate(n=Count("id")).order_by("priority")},
        "by_status": {row["status"]: row["n"] for row in tickets.values("status").annotate(n=Count("id")).order_by("status")},
        "backlog_by_age": age_buckets,
    })


class ImportJobViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ImportJobSerializer
    permission_classes = [IsAuthenticated, IsAdministrator]
    parser_classes = [MultiPartParser]
    queryset = ImportJob.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        if upload.size > 2 * 1024 * 1024:
            raise ValidationError({"file": "CSV imports are limited to 2 MB."})
        try:
            content = upload.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValidationError({"file": "The file must be UTF-8 encoded CSV."})
        kind = serializer.validated_data["kind"]
        job = ImportJob.objects.create(
            kind=kind,
            original_name=upload.name[:255],
            content=content,
            preview=imports.validate(kind, content),
            uploaded_by=request.user,
        )
        write_audit_event(request, "import.uploaded", obj=job, metadata={"kind": kind, "name": job.original_name})
        return Response(self.get_serializer(job).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        job = self.get_object()
        if job.state != ImportJob.State.VALIDATED:
            raise ValidationError({"state": "This import has already been processed."})
        if not job.preview.get("valid"):
            raise ValidationError({"preview": "There are no valid rows to import."})
        job = imports.apply(job, actor=request.user, request=request)
        return Response(self.get_serializer(job).data)


class ExportJobViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """A user only ever sees and downloads their own export files."""

    serializer_class = ExportJobSerializer
    lookup_field = "public_id"
    pagination_class = None

    def get_queryset(self):
        return ExportJob.objects.filter(requested_by=self.request.user)[:50]

    def get_object(self):
        obj = ExportJob.objects.filter(requested_by=self.request.user, public_id=self.kwargs["public_id"]).first()
        if obj is None:
            raise Http404
        return obj

    @action(detail=True, methods=["get"])
    def download(self, request, public_id=None):
        job = self.get_object()
        if job.state != ExportJob.State.DONE or not job.file or (job.expires_at and job.expires_at < timezone.now()):
            raise Http404
        write_audit_event(request, "export.downloaded", obj=job, metadata={"row_count": job.row_count})
        return FileResponse(job.file.open("rb"), as_attachment=True, filename="help-requests.csv", content_type="text/csv")
