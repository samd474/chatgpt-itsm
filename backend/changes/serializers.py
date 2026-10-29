from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.roles import is_staff_user
from core.customfields import clean_custom_fields
from helprequests.access import visible_HelpRequests
from helprequests.models import HelpRequests

from .models import ChangeApproval, ChangeRequest

User = get_user_model()


def _name(user):
    return (user.get_full_name() or user.get_username()) if user else None


class ChangeApprovalSerializer(serializers.ModelSerializer):
    approver_name = serializers.SerializerMethodField()
    change_number = serializers.CharField(source="change.number", read_only=True)
    change_title = serializers.CharField(source="change.title", read_only=True)

    class Meta:
        model = ChangeApproval
        fields = ["id", "change", "change_number", "change_title", "approver", "approver_name", "state", "comment", "decided_at", "created_at"]
        read_only_fields = fields

    def get_approver_name(self, obj):
        return _name(obj.approver)


class ChangeRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField()
    implementer = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), allow_null=True, required=False)
    implementer_name = serializers.SerializerMethodField()
    approvals = ChangeApprovalSerializer(many=True, read_only=True)
    help_requests = serializers.SlugRelatedField(slug_field="public_id", many=True, queryset=HelpRequests.objects.all(), required=False)
    custom_fields = serializers.DictField(required=False)
    conflict_count = serializers.SerializerMethodField()

    class Meta:
        model = ChangeRequest
        fields = ["id", "number", "title", "description", "justification", "change_type", "status", "risk", "impact",
                  "service", "assignment_group", "requested_by", "requested_by_name", "implementer", "implementer_name",
                  "implementation_plan", "backout_plan", "test_plan", "planned_start", "planned_end", "actual_start",
                  "actual_end", "outcome", "closure_notes", "custom_fields", "assets", "help_requests", "approvals",
                  "conflict_count", "created_at", "updated_at"]
        # Status, outcome and actual times only change through transitions.
        read_only_fields = ["id", "number", "status", "requested_by", "actual_start", "actual_end", "outcome",
                            "created_at", "updated_at"]

    def get_requested_by_name(self, obj):
        return _name(obj.requested_by)

    def get_implementer_name(self, obj):
        return _name(obj.implementer)

    def get_conflict_count(self, obj):
        annotated = getattr(obj, "conflict_total", None)
        if annotated is not None:
            return annotated
        from .services import conflicts

        return conflicts(obj).count() if obj.pk else 0

    def _viewer(self):
        request = self.context.get("request")
        return request.user if request else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if "help_requests" not in getattr(instance, "_prefetched_objects_cache", {}):
            # The viewset prefetches only visible tickets; scope the paths that skip it (e.g. after a save).
            viewer = self._viewer()
            visible = visible_HelpRequests(viewer, instance.help_requests.all()) if viewer else HelpRequests.objects.none()
            data["help_requests"] = list(visible.values_list("public_id", flat=True))
        return data

    def update(self, instance, validated_data):
        viewer = self._viewer()
        if "help_requests" in validated_data and viewer is not None:
            # The editor never sees tickets outside their scope, so keep those links rather than drop them.
            linked = instance.help_requests.all()
            hidden = linked.exclude(pk__in=visible_HelpRequests(viewer, linked).values("pk"))
            validated_data["help_requests"] = [*validated_data["help_requests"], *hidden]
        instance = super().update(instance, validated_data)
        # The list annotation predates this save; the window or assets may have changed.
        instance.__dict__.pop("conflict_total", None)
        return instance

    def validate_implementer(self, value):
        if value is not None and not is_staff_user(value):
            raise serializers.ValidationError("Implementers must be staff.")
        return value

    def validate_custom_fields(self, value):
        return clean_custom_fields("change", value, existing=self.instance.custom_fields if self.instance else None)

    def validate(self, attrs):
        start = attrs.get("planned_start", getattr(self.instance, "planned_start", None))
        end = attrs.get("planned_end", getattr(self.instance, "planned_end", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"planned_end": "The window must end after it starts."})
        return attrs


class ChangeTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ChangeRequest.Status.choices)
    outcome = serializers.ChoiceField(choices=ChangeRequest.Outcome.choices, required=False)
    closure_notes = serializers.CharField(required=False, allow_blank=True, max_length=20000)


class ChangeDecisionSerializer(serializers.Serializer):
    state = serializers.ChoiceField(choices=[ChangeApproval.State.APPROVED, ChangeApproval.State.REJECTED])
    comment = serializers.CharField(required=False, allow_blank=True, default="", max_length=4000)
