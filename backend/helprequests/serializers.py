from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Approval, Attachment, Category, HelpRequests, HelpRequestsComment, Services, SupportGroups

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
    description = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = HelpRequests
        fields = ["request_type", "subject", "description", "category", "service", "impact", "urgency"]

    def validate(self, attrs):
        for field in ("category", "service"):
            value = attrs.get(field)
            if value is not None and not value.active:
                raise serializers.ValidationError({field: "This option is no longer active."})
        return attrs


class RequesterHelpRequestsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequests
        fields = ["subject", "description", "category", "service"]


class TechnicianHelpRequestsUpdateSerializer(serializers.ModelSerializer):
    technician = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), allow_null=True, required=False)

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
        ]


class TransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=HelpRequests.RequestStatus.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    resolution_code = serializers.CharField(required=False, allow_blank=True, max_length=60)
    resolution_body = serializers.CharField(required=False, allow_blank=True)


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

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
