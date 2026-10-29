from rest_framework import serializers

from .models import TicketRule
from .validation import validate_actions, validate_conditions


class TicketRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketRule
        fields = ["id", "name", "description", "position", "active", "stop_processing", "conditions", "actions",
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
