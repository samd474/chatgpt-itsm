from django.contrib.auth import get_user_model
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.roles import STAFF_ROLES, is_staff_user
from reports.audit import write_audit_event
from reports.csv_utils import csv_response

from . import services
from .access import can_read_private_notes, visible_HelpRequests, works_ticket
from .models import Approval, Category, HelpRequests, HelpRequestsComment, Services, SupportGroups
from .permissions import CanExportHelpRequests, NotReadOnlyAuditor
from .serializers import (
    ApprovalDecisionSerializer,
    ApprovalSerializer,
    AttachmentSerializer,
    CategorySerializer,
    CommentSerializer,
    HelpRequestsCreateSerializer,
    HelpRequestsReadSerializer,
    RequesterHelpRequestsUpdateSerializer,
    ServiceSerializer,
    SupportGroupSerializer,
    TechnicianHelpRequestsUpdateSerializer,
    TransitionSerializer,
    UserLookupSerializer,
)

User = get_user_model()

EXPORT_COLUMNS = [
    ("request_number", "Number"),
    ("request_type", "Type"),
    ("subject", "Subject"),
    ("status", "Status"),
    ("priority", "Priority"),
    ("impact", "Impact"),
    ("urgency", "Urgency"),
    ("requester__username", "Requester"),
    ("technician__username", "Technician"),
    ("assignment_group__name", "Assignment group"),
    ("category__name", "Category"),
    ("service__name", "Service"),
    ("created_at", "Created"),
    ("resolved_at", "Resolved"),
    ("closed_at", "Closed"),
]


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

    filterset_fields = [
        "request_type",
        "status",
        "priority",
        "impact",
        "urgency",
        "technician",
        "assignment_group",
        "category",
        "service",
    ]
    search_fields = ["request_number", "subject", "description"]
    ordering_fields = ["created_at", "updated_at", "priority"]

    def get_queryset(self):
        qs = HelpRequests.objects.select_related(
            "requester",
            "technician",
            "assignment_group",
            "category",
            "service",
            "sla__policy",
        ).order_by("-created_at")
        return visible_HelpRequests(self.request.user, qs)

    def get_serializer_class(self):
        if self.action == "create":
            return HelpRequestsCreateSerializer
        if self.action in {"update", "partial_update"}:
            if is_staff_user(self.request.user):
                return TechnicianHelpRequestsUpdateSerializer
            return RequesterHelpRequestsUpdateSerializer
        return HelpRequestsReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        help_request = services.create_help_request(requester=request.user, request=request, **serializer.validated_data)
        return Response(HelpRequestsReadSerializer(help_request).data, status=status.HTTP_201_CREATED)

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
        help_request = services.update_help_request(
            help_request, actor=request.user, changes=serializer.validated_data, request=request,
        )
        return Response(HelpRequestsReadSerializer(help_request).data)

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
        return Response(HelpRequestsReadSerializer(help_request).data)

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

    @action(detail=True, methods=["get", "post"])
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
            content_type=attachment.content_type,
        )

    @action(detail=True, methods=["get"], url_path="approvals")
    def ticket_approvals(self, request, public_id=None):
        help_request = self.get_object()
        return Response(ApprovalSerializer(help_request.approvals.select_related("approver"), many=True).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, CanExportHelpRequests])
    def export(self, request):
        # Same scoping and filters as the list endpoint, with a fixed column list.
        queryset = self.filter_queryset(self.get_queryset())
        rows = list(queryset.values_list(*[column for column, _ in EXPORT_COLUMNS]))
        write_audit_event(request, "export.help_requests", object_type="help_requests", object_id="*",
                          metadata={"filters": request.query_params.dict(), "record_count": len(rows)})
        return csv_response("help-requests.csv", [label for _, label in EXPORT_COLUMNS], rows)


class ApprovalViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """The approvals assigned to the current user."""

    serializer_class = ApprovalSerializer
    filterset_fields = ["state"]

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


class SupportGroupViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SupportGroupSerializer
    queryset = SupportGroups.objects.filter(active=True)
    pagination_class = None


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.filter(active=True)
    pagination_class = None


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServiceSerializer
    queryset = Services.objects.filter(active=True)
    pagination_class = None


class TechnicianViewSet(viewsets.ReadOnlyModelViewSet):
    """Assignable staff. Only visible to staff."""

    serializer_class = UserLookupSerializer
    pagination_class = None
    filterset_fields = ["support_groups"]

    def get_queryset(self):
        if not is_staff_user(self.request.user):
            return User.objects.none()
        return User.objects.filter(is_active=True, groups__name__in=STAFF_ROLES).distinct().order_by("username")
