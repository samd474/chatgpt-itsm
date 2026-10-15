from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.roles import is_staff_user
from core.customfields import filter_for_requester

from . import queues
from .models import (
    Approval,
    Attachment,
    Category,
    FulfillmentTask,
    HelpRequests,
    HelpRequestsComment,
    Queue,
    Services,
    SupportGroups,
    TicketTemplate,
)

User = get_user_model()


def _name(user):
    return (user.get_full_name() or user.get_username()) if user else None


class HelpRequestsReadSerializer(serializers.ModelSerializer):
    requester_name = serializers.SerializerMethodField()
    technician_name = serializers.SerializerMethodField()
    assignment_group_name = serializers.CharField(source="assignment_group.name", default=None, read_only=True)
    category_name = serializers.CharField(source="category.name", default=None, read_only=True)
    service_name = serializers.CharField(source="service.name", default=None, read_only=True)
    sla = serializers.SerializerMethodField()
    custom_fields = serializers.SerializerMethodField()
    open_tasks = serializers.SerializerMethodField()

    class Meta:
        model = HelpRequests
        fields = (
            "public_id",
            "request_number",
            "request_type",
            "subject",
            "description",
            "requester",
            "requester_name",
            "technician",
            "technician_name",
            "assignment_group",
            "assignment_group_name",
            "category",
            "category_name",
            "service",
            "service_name",
            "impact",
            "urgency",
            "priority",
            "status",
            "request_payload",
            "custom_fields",
            "open_tasks",
            "resolution_code",
            "resolution_body",
            "first_response_time",
            "resolved_at",
            "closed_at",
            "created_at",
            "updated_at",
            "sla",
        )
        read_only_fields = fields

    def get_custom_fields(self, obj):
        request = self.context.get("request")
        if request is not None and not is_staff_user(request.user):
            return filter_for_requester(obj.custom_fields)
        return obj.custom_fields

    def get_open_tasks(self, obj):
        annotated = getattr(obj, "open_task_count", None)
        if annotated is not None:
            return annotated
        return obj.tasks.filter(status__in=FulfillmentTask.OPEN_STATUSES).count()

    def get_requester_name(self, obj):
        return _name(obj.requester)

    def get_technician_name(self, obj):
        return _name(obj.technician)

    def get_sla(self, obj):
        sla = getattr(obj, "sla", None)
        if sla is None:
            return None
        return {
            "policy": sla.policy.name,
            "response_due_at": sla.response_due_at,
            "resolution_due_at": sla.resolution_due_at,
            "response_breached": sla.response_breached,
            "resolution_breached": sla.resolution_breached,
            "paused": sla.pause_started_at is not None,
            "warning": sla.warning_sent_at is not None,
        }


class HelpRequestsCreateSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=True, allow_blank=False, max_length=20000)
    custom_fields = serializers.DictField(required=False, default=dict)
    template = serializers.PrimaryKeyRelatedField(queryset=TicketTemplate.objects.filter(active=True), required=False, allow_null=True)

    class Meta:
        model = HelpRequests
        fields = ["request_type", "subject", "description", "category", "service", "impact", "urgency", "custom_fields", "template"]

    def validate(self, attrs):
        for field in ("category", "service"):
            value = attrs.get(field)
            if value is not None and not value.active:
                raise serializers.ValidationError({field: "This option is no longer active."})
        return attrs


class RequesterHelpRequestsUpdateSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, max_length=20000)
    custom_fields = serializers.DictField(required=False)

    class Meta:
        model = HelpRequests
        fields = ["subject", "description", "category", "service", "custom_fields"]


class TechnicianHelpRequestsUpdateSerializer(serializers.ModelSerializer):
    technician = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), allow_null=True, required=False)
    description = serializers.CharField(required=False, allow_blank=True, max_length=20000)
    custom_fields = serializers.DictField(required=False)

    class Meta:
        model = HelpRequests
        fields = [
            "subject",
            "description",
            "category",
            "service",
            "technician",
            "assignment_group",
            "impact",
            "urgency",
            "custom_fields",
        ]


class TransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=HelpRequests.RequestStatus.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    resolution_code = serializers.CharField(required=False, allow_blank=True, max_length=60)
    resolution_body = serializers.CharField(required=False, allow_blank=True, max_length=20000)


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    body = serializers.CharField(max_length=20000)

    class Meta:
        model = HelpRequestsComment
        fields = ["id", "author", "author_name", "body", "visibility", "created_at"]
        read_only_fields = ["id", "author", "author_name", "created_at"]

    def get_author_name(self, obj):
        return _name(obj.author)


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "original_name", "content_type", "size_bytes", "sha256", "uploaded_by", "uploaded_by_name", "created_at"]
        read_only_fields = fields

    def get_uploaded_by_name(self, obj):
        return _name(obj.uploaded_by)


class ApprovalSerializer(serializers.ModelSerializer):
    approver_name = serializers.SerializerMethodField()
    help_request = serializers.SlugRelatedField(slug_field="public_id", read_only=True)
    request_number = serializers.CharField(source="help_request.request_number", read_only=True)
    subject = serializers.CharField(source="help_request.subject", read_only=True)

    class Meta:
        model = Approval
        fields = ["id", "help_request", "request_number", "subject", "approver", "approver_name",
                  "state", "comment", "decided_at", "created_at"]
        read_only_fields = fields

    def get_approver_name(self, obj):
        return _name(obj.approver)


class ApprovalDecisionSerializer(serializers.Serializer):
    state = serializers.ChoiceField(choices=[Approval.State.APPROVED, Approval.State.REJECTED])
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class SupportGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportGroups
        fields = ["id", "name", "active"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "parent", "active"]


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Services
        fields = ["id", "name", "active"]


class UserLookupSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "name"]

    def get_name(self, obj):
        return _name(obj)


class FulfillmentTaskSerializer(serializers.ModelSerializer):
    assignee = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), allow_null=True, required=False)
    assignee_name = serializers.SerializerMethodField()
    assignment_group_name = serializers.CharField(source="assignment_group.name", default=None, read_only=True)

    class Meta:
        model = FulfillmentTask
        fields = ["id", "title", "description", "assignment_group", "assignment_group_name", "assignee",
                  "assignee_name", "status", "position", "created_at", "completed_at"]
        read_only_fields = ["id", "created_at", "completed_at"]

    def get_assignee_name(self, obj):
        return _name(obj.assignee)

    def validate_assignee(self, value):
        if value is not None and not is_staff_user(value):
            raise serializers.ValidationError("Only staff can be assigned tasks.")
        return value


class TicketTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketTemplate
        fields = ["id", "name", "help_text", "request_type", "subject", "description", "category", "service",
                  "assignment_group", "impact", "urgency", "available_to_requesters", "active"]


class QueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = ["id", "name", "description", "filters", "ordering", "visible_to_roles", "position", "active"]

    def validate_filters(self, value):
        try:
            return queues.validate_filters(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate_visible_to_roles(self, value):
        try:
            return queues.validate_roles(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))


class SupportGroupAdminSerializer(serializers.ModelSerializer):
    members = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), many=True, required=False)
    managers = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), many=True, required=False)

    class Meta:
        model = SupportGroups
        fields = ["id", "name", "active", "members", "managers"]


class CategoryAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "parent", "active"]

    def validate_parent(self, value):
        node = value
        while node is not None:
            if self.instance is not None and node.pk == self.instance.pk:
                raise serializers.ValidationError("A category cannot be its own ancestor.")
            node = node.parent
        return value


class ServiceAdminSerializer(serializers.ModelSerializer):
    owner_group = serializers.PrimaryKeyRelatedField(source="managers", queryset=SupportGroups.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Services
        fields = ["id", "name", "owner_group", "active"]
