from rest_framework import serializers
from .models import HelpRequests


class HelpRequestsReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequests
        fields = (
            "public_id",
            "request_number",
            "request_type",
            "subject",
            "requester",
            "technician",
            "assignment_group",
            "category",
            "service",
            "impact",
            "urgency",
            "status",
            "request_payload",
            "resolution_code",
            "resolution_body",
            "first_response_time",
            "resolved_at",
            "closed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RequesterHelpRequestsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequests
        fields = ["subject", "category", "service"]


class TechnicianHelpRequestsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequests
        fields = [
            "subject",
            "category",
            "service",
            "technician",
            "assignment_group",
            "impact",
            "urgency",
            "status",
            "resolution_code",
            "resolution_body",
        ]


class HelpRequestsCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequests
        fields = ["public_id", "request_type", "subject", "category", "service", "impact", "urgency", "request_payload"]
        read_only_fields = ["public_id"]
