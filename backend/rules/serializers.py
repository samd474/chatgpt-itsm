from rest_framework import serializers

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
