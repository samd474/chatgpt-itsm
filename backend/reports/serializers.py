from rest_framework import serializers

from .models import AuditEvent, ExportJob, ImportJob


class AuditEventSerializer(serializers.ModelSerializer):
    # Names match the guide's API contract used by the frontend.
    actor = serializers.IntegerField(source="initiated_by_id", read_only=True)
    actor_name = serializers.SerializerMethodField()
    event_type = serializers.CharField(source="activity_type", read_only=True)

    class Meta:
        model = AuditEvent
        fields = ["id", "event_type", "object_type", "object_id", "actor", "actor_name", "request_id",
                  "source_ip", "before", "after", "metadata", "created_at"]
        read_only_fields = fields

    def get_actor_name(self, obj) -> str | None:
        user = obj.initiated_by
        return (user.get_full_name() or user.get_username()) if user else None


class ImportJobSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = ImportJob
        fields = ["id", "kind", "state", "original_name", "preview", "result", "file", "created_at", "applied_at"]
        read_only_fields = ["id", "state", "original_name", "preview", "result", "created_at", "applied_at"]


class ExportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportJob
        fields = ["public_id", "kind", "params", "state", "row_count", "error", "created_at", "finished_at", "expires_at"]
        read_only_fields = fields


class ServiceDeskReportSerializer(serializers.Serializer):
    """Shape of GET /api/reports/service-desk/ (for the OpenAPI schema)."""

    open_tickets = serializers.IntegerField()
    unassigned = serializers.IntegerField()
    sla_at_risk = serializers.IntegerField()
    sla_breached = serializers.IntegerField()
    by_priority = serializers.DictField(child=serializers.IntegerField())
    by_status = serializers.DictField(child=serializers.IntegerField())
    backlog_by_age = serializers.DictField(child=serializers.IntegerField())


# --- GET /api/reports/sla/ (shapes for the OpenAPI schema) ------------------------------------------

class SLANowSerializer(serializers.Serializer):
    breached = serializers.IntegerField()
    at_risk = serializers.IntegerField()
    paused = serializers.IntegerField()
    on_track = serializers.IntegerField()
    no_sla = serializers.IntegerField(help_text="Open tickets with no SLA policy.")


class SLAAttentionSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    request_number = serializers.CharField()
    subject = serializers.CharField()
    priority = serializers.IntegerField()
    status = serializers.CharField()
    assignment_group = serializers.CharField(allow_null=True)
    technician = serializers.CharField(allow_null=True)
    state = serializers.ChoiceField(choices=["breached", "at_risk"])
    target = serializers.ChoiceField(choices=["response", "resolution"])
    due_at = serializers.DateTimeField()
    paused = serializers.BooleanField()


class SLAPeriodSerializer(serializers.Serializer):
    resolved = serializers.IntegerField()
    resolution_met_percent = serializers.FloatField(allow_null=True)
    responded = serializers.IntegerField()
    response_met_percent = serializers.FloatField(allow_null=True)


class SLATrendDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    met = serializers.IntegerField()
    breached = serializers.IntegerField()


class SLABreakdownSerializer(serializers.Serializer):
    key = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()  # not "label": that would shadow Field.label
    resolved = serializers.IntegerField()
    resolution_met_percent = serializers.FloatField(allow_null=True)
    responded = serializers.IntegerField()
    response_met_percent = serializers.FloatField(allow_null=True)
    open_breached = serializers.IntegerField()


class SLAReportSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    days = serializers.IntegerField()
    now = SLANowSerializer()
    attention = SLAAttentionSerializer(many=True)
    period = SLAPeriodSerializer()
    trend = SLATrendDaySerializer(many=True)
    by_group = SLABreakdownSerializer(many=True)
    by_priority = SLABreakdownSerializer(many=True)
