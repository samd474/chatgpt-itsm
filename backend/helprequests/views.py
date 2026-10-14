
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from .models import Ticket
from .serializers import (
    TicketCreateSerializer,
    TicketReadSerializer,
    TechnicianTicketUpdateSerializer,
    RequesterTicketUpdateSerializer,
)

from services import create_ticket_from_serializer, visible_tickets


class TicketViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = "public_id"

    filterset_fields = [
        "ticket_type",
        "status",
        "priority",
        "assignment_group",
        "category",
    ]

    search_fields = ["number", "title", "description"]

    ordering_fields = [
        "created_at",
        "updated_at",
        "priority",
    ]

    def get_queryset(self):
        qs = Ticket.objects.select_related(
            "requester",
            "assignee",
            "assignment_group",
            "category",
            "service",
        ).all()

        return visible_tickets(self.request.user, qs)

    def get_serializer_class(self):

        if self.action == "create":
            return TicketCreateSerializer

        if self.action in {"update", "partial_update"}:
            if self.request.user.groups.filter(
                name__in=["Technician", "Manager", "Administrator"]
            ).exists():
                return TechnicianTicketUpdateSerializer

            return RequesterTicketUpdateSerializer

        return TicketReadSerializer

    def perform_create(self, serializer):
        create_ticket_from_serializer(
            request=self.request,
            serializer=serializer,
        )

