from rest_framework import serializers
from HelpRequests.models import HelpRequests


class HelpRequestReadSerializer(serializers.ModelSerializer):
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


class RequesterHelpRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequest
        fields = ["title", "description", "category", "service", "version"]
        extra_kwargs = {"version": {"write_only": True}}


class HelpRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequest
        fields = ["request_type", "title", "description", "category", "service", "client_request_id"]
    