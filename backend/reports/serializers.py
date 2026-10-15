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

    def get_actor_name(self, obj):
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
