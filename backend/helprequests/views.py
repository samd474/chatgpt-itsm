from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.throttling import ExportThrottle, UploadThrottle

from accounts.models import User as AccountUser
from accounts.roles import ADMINISTRATOR, STAFF_ROLES, has_role, is_admin, is_staff_user
from core.customfields import clean_custom_fields
from core.permissions import role_permission
from core.viewsets import AuditedModelViewSet
from reports.audit import write_audit_event
from reports.csv_utils import csv_response
from reports.models import ExportJob

from . import queues, services
from .access import can_read_private_notes, visible_HelpRequests, works_ticket
from .exports import EXPORT_HEADER, export_rows
from .filters import HelpRequestsFilter
from .models import (
    Approval,
    Category,
    FulfillmentTask,
    HelpRequests,
    HelpRequestsComment,
    Queue,
    Services,
    SupportGroups,
    TicketTemplate,
)
from .permissions import CanExportHelpRequests, NotReadOnlyAuditor
from .serializers import (
    ApprovalDecisionSerializer,
    ApprovalSerializer,
    AttachmentSerializer,
    CategoryAdminSerializer,
    CategorySerializer,
    CommentSerializer,
    FulfillmentTaskSerializer,
    HelpRequestsCreateSerializer,
    HelpRequestsReadSerializer,
    QueueSerializer,
    RequesterHelpRequestsUpdateSerializer,
    ServiceAdminSerializer,
    ServiceSerializer,
    SupportGroupAdminSerializer,
    SupportGroupSerializer,
    TechnicianHelpRequestsUpdateSerializer,
    TicketTemplateSerializer,
    TransitionSerializer,
    UserLookupSerializer,
)

User = get_user_model()

AdminWritable = role_permission(
    read_roles=("Requester", "Technician", "Manager", "Administrator", "Auditor"),
    write_roles=(ADMINISTRATOR,),
)


class HelpRequestsViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Tickets. There is deliberately no DELETE; cancel through a transition instead."""

    permission_classes = [IsAuthenticated, NotReadOnlyAuditor]
    lookup_field = "public_id"
    http_method_names = ["get", "post", "patch", "head", "options"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_class = HelpRequestsFilter
    ordering_fields = ["created_at", "updated_at", "priority"]

    def get_queryset(self):
        qs = HelpRequests.objects.select_related(
            "requester",
            "technician",
            "assignment_group",
            "category",
            "service",
            "sla__policy",
        ).annotate(
            open_task_count=Count("tasks", filter=Q(tasks__status__in=FulfillmentTask.OPEN_STATUSES), distinct=True),
        ).order_by("-created_at")
        return visible_HelpRequests(self.request.user, qs)

    def get_serializer_class(self):
        if self.action == "create":
            return HelpRequestsCreateSerializer
        if self.action in {"update", "partial_update"}:
            if is_staff_user(self.request.user):
                return TechnicianHelpRequestsUpdateSerializer
            return RequesterHelpRequestsUpdateSerializer
        if self.action == "tasks":
            return FulfillmentTaskSerializer
        return HelpRequestsReadSerializer

    def _read(self, help_request):
        return HelpRequestsReadSerializer(help_request, context=self.get_serializer_context()).data

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        template = data.pop("template", None)
        if template is not None:
            if not template.available_to_requesters and not is_staff_user(request.user):
                raise PermissionDenied("That template is not available.")
            # Routing comes from the template on the server, so requesters can't pick queues themselves.
            data["assignment_group"] = template.assignment_group
        data["custom_fields"] = clean_custom_fields(
            "ticket", data.pop("custom_fields", {}), for_requester=not is_staff_user(request.user),
        )
        help_request = services.create_help_request(requester=request.user, request=request, **data)
        return Response(self._read(help_request), status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        help_request = self.get_object()
        staff = works_ticket(request.user, help_request)
        if not staff:
            if help_request.requester_id != request.user.pk:
                raise PermissionDenied("You cannot edit this ticket.")
            if help_request.status != HelpRequests.RequestStatus.NEW:
                raise PermissionDenied("Requesters can only edit tickets that have not been picked up yet.")
        serializer_class = TechnicianHelpRequestsUpdateSerializer if staff else RequesterHelpRequestsUpdateSerializer
        serializer = serializer_class(help_request, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        changes = dict(serializer.validated_data)
        if "custom_fields" in changes:
            changes["custom_fields"] = clean_custom_fields(
                "ticket", changes["custom_fields"], existing=help_request.custom_fields, for_requester=not staff,
            )
        help_request = services.update_help_request(help_request, actor=request.user, changes=changes, request=request)
        return Response(self._read(help_request))

    @action(detail=True, methods=["post"])
    def transition(self, request, public_id=None):
        help_request = self.get_object()
        serializer = TransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        help_request = services.transition_help_request(
            help_request,
            new_status=data["status"],
            actor=request.user,
            reason=data.get("reason", ""),
            resolution_code=data.get("resolution_code"),
            resolution_body=data.get("resolution_body"),
            request=request,
        )
        return Response(self._read(help_request))

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, public_id=None):
        help_request = self.get_object()
        if request.method == "POST":
            serializer = CommentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            comment = services.add_comment(
                help_request,
                author=request.user,
                body=serializer.validated_data["body"],
                visibility=serializer.validated_data.get("visibility", HelpRequestsComment.Visibility.PUBLIC),
                request=request,
            )
            return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)

        comments = help_request.comments.select_related("author")
        if not can_read_private_notes(request.user, help_request):
            # Filter in the query: private notes must never reach a requester's browser.
            comments = comments.filter(visibility=HelpRequestsComment.Visibility.PUBLIC)
        return Response(CommentSerializer(comments, many=True).data)

    @action(detail=True, methods=["get", "post"], throttle_classes=[UploadThrottle])
    def attachments(self, request, public_id=None):
        help_request = self.get_object()
        if request.method == "POST":
            uploaded = request.FILES.get("file")
            if uploaded is None:
                return Response({"file": ["Choose a file to upload."]}, status=status.HTTP_400_BAD_REQUEST)
            attachment = services.add_attachment(help_request, uploaded_by=request.user, uploaded_file=uploaded, request=request)
            return Response(AttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)
        attachments = help_request.attachments.select_related("uploaded_by", "comment")
        if not can_read_private_notes(request.user, help_request):
            attachments = attachments.exclude(comment__visibility=HelpRequestsComment.Visibility.PRIVATE)
        return Response(AttachmentSerializer(attachments, many=True).data)

    @action(detail=True, methods=["get"], url_path=r"attachments/(?P<attachment_id>\d+)/download")
    def download_attachment(self, request, public_id=None, attachment_id=None):
        # get_object() applies the same visibility scope as every other ticket read.
        help_request = self.get_object()
        attachments = help_request.attachments.all()
        if not can_read_private_notes(request.user, help_request):
            attachments = attachments.exclude(comment__visibility=HelpRequestsComment.Visibility.PRIVATE)
        attachment = get_object_or_404(attachments, pk=attachment_id)
        write_audit_event(request, "attachment.downloaded", obj=help_request,
                          metadata={"attachment_id": attachment.pk})
        return FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=attachment.original_name,
            content_type="application/octet-stream",
        )

    @action(detail=True, methods=["get"], url_path="approvals")
    def ticket_approvals(self, request, public_id=None):
        help_request = self.get_object()
        return Response(ApprovalSerializer(help_request.approvals.select_related("approver"), many=True).data)

    @action(detail=True, methods=["get", "post"])
    def tasks(self, request, public_id=None):
        help_request = self.get_object()
        if request.method == "POST":
            if not works_ticket(request.user, help_request):
                raise PermissionDenied("Only staff working this ticket can add tasks.")
            serializer = FulfillmentTaskSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            task = serializer.save(help_request=help_request)
            write_audit_event(request, "ticket.task_created", obj=help_request, metadata={"task_id": task.pk, "title": task.title})
            return Response(FulfillmentTaskSerializer(task).data, status=status.HTTP_201_CREATED)
        if not (works_ticket(request.user, help_request) or has_role(request.user, "Auditor")):
            return Response([])
        tasks = help_request.tasks.select_related("assignee", "assignment_group")
        return Response(FulfillmentTaskSerializer(tasks, many=True).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, CanExportHelpRequests],
            throttle_classes=[ExportThrottle], url_path="export")
    def export(self, request):
        # Same scoping and filters as the list endpoint, with a fixed column list.
        queryset = self.filter_queryset(self.get_queryset())
        count = queryset.count()
        params = {k: v for k, v in request.query_params.items() if k in HelpRequestsFilter.get_filters() or k == "ordering"}
        if count > settings.EXPORT_SYNC_LIMIT:
            from typing import cast

            from celery import Task

            from reports.tasks import generate_export

            job = ExportJob.objects.create(kind="help_requests", params=params, requested_by=request.user)
            write_audit_event(request, "export.queued", obj=job, metadata={"filters": params, "record_count": count})
            cast(Task, generate_export).delay(job.pk)
            return Response({"export_id": str(job.public_id), "state": job.state, "row_count": count},
                            status=status.HTTP_202_ACCEPTED)
        rows = list(export_rows(queryset))
        write_audit_event(request, "export.help_requests", object_type="help_requests", object_id="*",
                          metadata={"filters": params, "record_count": len(rows)})
        return csv_response("help-requests.csv", EXPORT_HEADER, rows)


class FulfillmentTaskViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Update a task's status or assignee. Scoped to tickets the user can see."""

    serializer_class = FulfillmentTaskSerializer
    permission_classes = [IsAuthenticated, NotReadOnlyAuditor]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        visible = visible_HelpRequests(self.request.user, HelpRequests.objects.all())
        return FulfillmentTask.objects.filter(help_request__in=visible).select_related("help_request", "assignee")

    def update(self, request, *args, **kwargs):
        task = self.get_object()
        serializer = self.get_serializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        allowed = {k: v for k, v in serializer.validated_data.items() if k in ("status", "assignee", "title", "description", "assignment_group")}
        task = services.update_task(task, actor=request.user, changes=allowed, request=request)
        return Response(self.get_serializer(task).data)


class ApprovalViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """The approvals assigned to the current user."""

    serializer_class = ApprovalSerializer
    filterset_fields = ["state"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return Approval.objects.filter(approver=self.request.user).select_related("approver", "help_request")

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        approval = self.get_object()
        serializer = ApprovalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approval = services.decide_approval(
            approval, actor=request.user, state=serializer.validated_data["state"],
            comment=serializer.validated_data.get("comment", ""), request=request,
        )
        return Response(ApprovalSerializer(approval).data)


class LookupViewSet(AuditedModelViewSet):
    """Everyone reads active rows; administrators see everything and can edit."""

    permission_classes = [IsAuthenticated, AdminWritable]
    pagination_class = None
    model: Any = None
    public_serializer: Any = None
    admin_serializer: Any = None

    def get_queryset(self):
        qs = self.model.objects.all()
        return qs if is_admin(self.request.user) else qs.filter(active=True)

    def get_serializer_class(self) -> Any:
        return self.admin_serializer if is_admin(self.request.user) else self.public_serializer


class SupportGroupViewSet(LookupViewSet):
    model = SupportGroups
    public_serializer = SupportGroupSerializer
    admin_serializer = SupportGroupAdminSerializer
    audit_prefix = "config.support_group"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("members", "managers")


class CategoryViewSet(LookupViewSet):
    model = Category
    public_serializer = CategorySerializer
    admin_serializer = CategoryAdminSerializer
    audit_prefix = "config.category"


class ServiceViewSet(LookupViewSet):
    model = Services
    public_serializer = ServiceSerializer
    admin_serializer = ServiceAdminSerializer
    audit_prefix = "config.service"


class TicketTemplateViewSet(AuditedModelViewSet):
    serializer_class = TicketTemplateSerializer
    permission_classes = [IsAuthenticated, AdminWritable]
    pagination_class = None
    audit_prefix = "config.ticket_template"

    def get_queryset(self):
        qs = TicketTemplate.objects.all()
        if is_admin(self.request.user):
            return qs
        qs = qs.filter(active=True)
        return qs if is_staff_user(self.request.user) else qs.filter(available_to_requesters=True)


class QueueViewSet(AuditedModelViewSet):
    serializer_class = QueueSerializer
    permission_classes = [IsAuthenticated, role_permission(read_roles=STAFF_ROLES + ("Auditor",), write_roles=(ADMINISTRATOR,))]
    pagination_class = None
    audit_prefix = "config.queue"

    def get_queryset(self):
        qs = Queue.objects.all()
        user = self.request.user
        if is_admin(user):
            return qs
        roles = set(user.groups.values_list("name", flat=True)) if isinstance(user, AccountUser) else set()
        visible = [q.pk for q in qs.filter(active=True) if not q.visible_to_roles or roles & set(q.visible_to_roles)]
        return qs.filter(pk__in=visible)

    @action(detail=True, methods=["get"])
    def tickets(self, request, pk=None):
        queue = self.get_object()
        base = HelpRequests.objects.select_related(
            "requester", "technician", "assignment_group", "category", "service", "sla__policy",
        ).annotate(open_task_count=Count("tasks", filter=Q(tasks__status__in=FulfillmentTask.OPEN_STATUSES), distinct=True))
        # Queues narrow what the user may already see; they never widen it.
        qs = queues.apply_filters(visible_HelpRequests(request.user, base), queue.filters, request.user)
        qs = HelpRequestsFilter(request.query_params, queryset=qs).qs.order_by(queue.ordering, "-created_at")
        page = self.paginate_queryset(qs)
        data = HelpRequestsReadSerializer(page, many=True, context=self.get_serializer_context()).data
        return self.get_paginated_response(data)

    @property
    def paginator(self):
        if self.action == "tickets":
            from config.pagination import StandardPagination

            if not hasattr(self, "_queue_paginator"):
                self._queue_paginator = StandardPagination()
            return self._queue_paginator
        return None


class TechnicianViewSet(viewsets.ReadOnlyModelViewSet):
    """Assignable staff. Only visible to staff."""

    serializer_class = UserLookupSerializer
    pagination_class = None
    filterset_fields = ["support_groups"]

    def get_queryset(self):
        if not is_staff_user(self.request.user):
            return User.objects.none()
        return User.objects.filter(is_active=True, is_enabled=True, groups__name__in=STAFF_ROLES).distinct().order_by("username")


class PeopleViewSet(viewsets.ReadOnlyModelViewSet):
    """Directory of active people for staff pickers (asset assignment, project members).

    Requesters get nothing: they have no need to enumerate other users.
    """

    serializer_class = UserLookupSerializer
    search_fields = ["username", "first_name", "last_name", "email"]

    def get_queryset(self):
        if not is_staff_user(self.request.user):
            return User.objects.none()
        return User.objects.filter(is_active=True, is_enabled=True).order_by("first_name", "last_name", "username")
