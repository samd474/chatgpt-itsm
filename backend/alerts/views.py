from rest_framework import serializers

from core.permissions import IsAdministrator
from core.viewsets import AuditedModelViewSet

from .models import NotificationTemplate
from .templates import TEMPLATES, template_errors


class NotificationTemplateSerializer(serializers.ModelSerializer):
    default_subject = serializers.SerializerMethodField()
    default_body = serializers.SerializerMethodField()

    class Meta:
        model = NotificationTemplate
        fields = ["id", "event_type", "subject", "body", "enabled", "default_subject", "default_body", "updated_at"]
        read_only_fields = ["id", "updated_at"]

    def get_default_subject(self, obj):
        return TEMPLATES.get(obj.event_type, ("", ""))[0]

    def get_default_body(self, obj):
        return TEMPLATES.get(obj.event_type, ("", ""))[1]

    def validate_event_type(self, value):
        if value not in TEMPLATES:
            raise serializers.ValidationError(f"Choose one of: {', '.join(sorted(TEMPLATES))}")
        return value

    def validate(self, attrs):
        errors = {}
        for field in ("subject", "body"):
            if field in attrs:
                problems = template_errors(attrs[field])
                if problems:
                    errors[field] = problems
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class NotificationTemplateViewSet(AuditedModelViewSet):
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAdministrator]
    pagination_class = None
    queryset = NotificationTemplate.objects.all()
    audit_prefix = "config.notification_template"
