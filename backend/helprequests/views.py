import uuid

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .access import visible_HelpRequests
from .models import HelpRequests
from .serializers import (
    HelpRequestsCreateSerializer,
    HelpRequestsReadSerializer,
    TechnicianHelpRequestsUpdateSerializer,
    RequesterHelpRequestsUpdateSerializer,
)


class HelpRequestsViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = "public_id"

    filterset_fields = [
        "request_type",
        "status",
        "impact",
        "urgency",
        "assignment_group",
        "category",
    ]

    search_fields = ["request_number", "subject"]

    ordering_fields = [
        "created_at",
        "updated_at",
        "urgency",
    ]

    def get_queryset(self):
        qs = HelpRequests.objects.select_related(
            "requester",
            "technician",
            "assignment_group",
            "category",
            "service",
        ).order_by("-created_at")

        return visible_HelpRequests(self.request.user, qs)

    def get_serializer_class(self):

        if self.action == "create":
            return HelpRequestsCreateSerializer

        if self.action in {"update", "partial_update"}:
            if self.request.user.groups.filter(
                name__in=["Technician", "Manager", "Administrator"]
            ).exists():
                return TechnicianHelpRequestsUpdateSerializer

            return RequesterHelpRequestsUpdateSerializer

        return HelpRequestsReadSerializer

    def perform_create(self, serializer):
        prefix = "INC" if serializer.validated_data["request_type"] == HelpRequests.RequestType.INCIDENT else "REQ"
        serializer.save(
            requester=self.request.user,
            request_number=f"{prefix}-{uuid.uuid4().hex[:8].upper()}",
        )
