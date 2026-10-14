
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from .models import HelpRequest
from .serializers import (
    HelpRequestCreateSerializer,
    HelpRequestReadSerializer,
    TechnicianHelpRequestUpdateSerializer,
    RequesterHelpRequestUpdateSerializer,
)

from services import create_HelpRequest_from_serializer, visible_HelpRequests


class HelpRequestViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = "public_id"

    filterset_fields = [
        "HelpRequest_type",
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
        qs = HelpRequest.objects.select_related(
            "requester",
            "assignee",
            "assignment_group",
            "category",
            "service",
        ).all()

        return visible_HelpRequests(self.request.user, qs)

    def get_serializer_class(self):

        if self.action == "create":
            return HelpRequestCreateSerializer

        if self.action in {"update", "partial_update"}:
            if self.request.user.groups.filter(
                name__in=["Technician", "Manager", "Administrator"]
            ).exists():
                return TechnicianHelpRequestUpdateSerializer

            return RequesterHelpRequestUpdateSerializer

        return HelpRequestReadSerializer

    def perform_create(self, serializer):
        create_HelpRequest_from_serializer(
            request=self.request,
            serializer=serializer,
        )

