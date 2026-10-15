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
PRIORITY_MATRIX = {
    (1,1): 1, (1,2): 1, (1,3): 2,
    (2,1): 1, (2,2): 2, (2,3): 3,
    (3,1): 2, (3,2): 3, (3,3): 4
}

def calculate_priority(impact, urgency):
    return PRIORITY_MATRIX[(impact, urgency)]
