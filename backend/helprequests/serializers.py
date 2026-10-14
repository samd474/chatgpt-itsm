from rest_framework import serializers
from .models import HelpRequests


class HelpRequestsReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequests
        fields = (
            "public_id",
            "number",
            "Request_type",
            "title",
            "description",
            "requester",
            "assigned_to",
            "assignment_group",
            "category",
            "service",
            "impact",
            "urgency",
            "priority",
            "status",
            "request_payload",
            "resolution_code",
            "resolution_notes",
            "first_response_time",
            "resolution_time",
            "closed_timestamp",
            "version",
            "creation_date",
            "last_updated",
        )
        read_only_fields = (
            "public_id",
            "number",
            "requester",
            "assigned_to",
            "assignment_group",
            "status",
            "first_response_time",
            "resolution_time",
            "closed_timestamp",
            "version",
            "creation_date",
            "last_updated",
        )


class RequesterHelpRequestsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequests
        fields = ["title", "description", "category", "service", "version"]
        extra_kwargs = {"version": {"write_only": True}}


class HelpRequestsCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequests
        fields = ["request_type", "title", "description", "category", "service", "client_request_id"]
    