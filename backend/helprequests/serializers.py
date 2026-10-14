from rest_framework import serializers

from .models import Ticket


class TicketReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = (
            "public_id",
            "number",
            "Ticket_type",
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


class RequesterTicketUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["title", "description", "category", "service", "version"]
        extra_kwargs = {"version": {"write_only": True}}


class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["request_type", "title", "description", "category", "service", "client_request_id"]
    