from rest_framework import serializers

from core.schema import extend_schema_field
from helprequests.models import HelpRequests

from .models import TicketRule
from .validation import validate_actions, validate_conditions, validate_rule


class TicketRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketRule
        fields = ["id", "name", "description", "position", "active", "stop_processing", "runs_on", "conditions", "actions",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_conditions(self, value):
        try:
            return validate_conditions(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate_actions(self, value):
        try:
            return validate_actions(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate(self, attrs):
        runs_on = attrs.get("runs_on", getattr(self.instance, "runs_on", TicketRule.RunsOn.CREATED))
        conditions = attrs.get("conditions", getattr(self.instance, "conditions", {}))
        try:
            validate_rule(runs_on, conditions)
        except ValueError as exc:
            raise serializers.ValidationError({"conditions": str(exc)})
        return attrs


@extend_schema_field({"oneOf": [{"type": "string"}, {"type": "integer"}], "nullable": True})
class _NameOrNumberField(serializers.JSONField):
    """A group/category/service name, an impact/urgency number, or null when unset."""


class RulePreviewChangeSerializer(serializers.Serializer):
    field = serializers.CharField()
    from_ = _NameOrNumberField(allow_null=True)
    to = _NameOrNumberField(allow_null=True)

    def get_fields(self):
        fields = super().get_fields()
        fields["from"] = fields.pop("from_")  # "from" is a Python keyword
        return fields


class RulePreviewTicketSerializer(serializers.Serializer):
    public_id = serializers.CharField()
    request_number = serializers.CharField(allow_null=True)
    subject = serializers.CharField()
    status = serializers.ChoiceField(choices=HelpRequests.RequestStatus.choices)
    changes = RulePreviewChangeSerializer(many=True)


class RulePreviewSerializer(serializers.Serializer):
    """Shape of POST /api/rules/ticket-rules/preview/ (for the OpenAPI schema)."""

    scanned = serializers.IntegerField()
    matched = serializers.IntegerField()
    ignored_conditions = serializers.ListField(child=serializers.CharField())
    tickets = RulePreviewTicketSerializer(many=True)


class RulePreviewRequestSerializer(serializers.Serializer):
    conditions = serializers.JSONField()
    actions = serializers.JSONField(required=False)
