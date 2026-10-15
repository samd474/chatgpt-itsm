from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.roles import ADMINISTRATOR, AUDITOR, MANAGER, STAFF_ROLES, TECHNICIAN, has_role, is_staff_user
from core.numbering import assign_number
from core.permissions import role_permission
from core.viewsets import AuditedModelViewSet
from helprequests.access import visible_HelpRequests
from helprequests.models import HelpRequests
from reports.audit import write_audit_event
from reports.models import AuditEvent
from reports.serializers import AuditEventSerializer

from .models import Asset, AssetRelationship, AssetType, Location
from .serializers import (
    AssetRelationshipSerializer,
    AssetSerializer,
    AssetTypeSerializer,
    LinkTicketSerializer,
    LocationSerializer,
    RequesterAssetSerializer,
)

ALL_ROLES = ("Requester",) + STAFF_ROLES + (AUDITOR,)
AssetReadWrite = role_permission(read_roles=ALL_ROLES, write_roles=(TECHNICIAN, MANAGER, ADMINISTRATOR))
AdminLookup = role_permission(read_roles=ALL_ROLES, write_roles=(ADMINISTRATOR,))


class AssetTypeViewSet(AuditedModelViewSet):
    serializer_class = AssetTypeSerializer
    permission_classes = [IsAuthenticated, AdminLookup]
    pagination_class = None
    queryset = AssetType.objects.all()
    audit_prefix = "config.asset_type"


class LocationViewSet(AuditedModelViewSet):
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated, AdminLookup]
    pagination_class = None
    queryset = Location.objects.all()
    audit_prefix = "config.location"


class AssetViewSet(AuditedModelViewSet):
    """Staff manage assets; requesters only see (read-only) the equipment assigned to them.

    No DELETE: assets are retired or disposed through their status so history is kept.
    """

    permission_classes = [IsAuthenticated, AssetReadWrite]
    http_method_names = ["get", "post", "patch", "head", "options"]
    audit_prefix = "asset"
    filterset_fields = ["status", "asset_type", "location", "assigned_to", "owner", "support_group"]
    search_fields = ["asset_tag", "name", "serial_number", "manufacturer", "model"]
    ordering_fields = ["asset_tag", "name", "updated_at", "warranty_expires"]

    def get_queryset(self):
        qs = Asset.objects.select_related("asset_type", "location", "owner", "assigned_to").prefetch_related("help_requests")
        user = self.request.user
        if is_staff_user(user) or has_role(user, AUDITOR):
            return qs
        return qs.filter(assigned_to=user)

    def get_serializer_class(self):
        user = self.request.user
        if is_staff_user(user) or has_role(user, AUDITOR):
            return AssetSerializer
        return RequesterAssetSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        assign_number(instance, "AST", field="asset_tag")
        write_audit_event(self.request, "asset.created", obj=instance, before={}, after=self._snapshot(instance))

    def perform_update(self, serializer):
        try:
            super().perform_update(serializer)
        except IntegrityError:
            raise ValidationError({"asset_tag": "That asset tag is already in use."})

    @action(detail=True, methods=["get", "post"])
    def relationships(self, request, pk=None):
        asset = self.get_object()
        if request.method == "POST":
            if not is_staff_user(request.user):
                raise PermissionDenied()
            serializer = AssetRelationshipSerializer(data={**request.data, "source": asset.pk})
            serializer.is_valid(raise_exception=True)
            try:
                relationship = serializer.save()
            except IntegrityError:
                raise ValidationError({"detail": "That relationship already exists."})
            write_audit_event(request, "asset.relationship_added", obj=asset, metadata=serializer.data)
            return Response(AssetRelationshipSerializer(relationship).data, status=status.HTTP_201_CREATED)
        rels = AssetRelationship.objects.filter(source=asset) | AssetRelationship.objects.filter(target=asset)
        return Response(AssetRelationshipSerializer(rels.select_related("source", "target"), many=True).data)

    @action(detail=True, methods=["delete"], url_path=r"relationships/(?P<relationship_id>\d+)")
    def remove_relationship(self, request, pk=None, relationship_id=None):
        asset = self.get_object()
        if not is_staff_user(request.user):
            raise PermissionDenied()
        relationship = AssetRelationship.objects.filter(pk=relationship_id, source=asset).first() or \
            AssetRelationship.objects.filter(pk=relationship_id, target=asset).first()
        if relationship is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        write_audit_event(request, "asset.relationship_removed", obj=asset, metadata=AssetRelationshipSerializer(relationship).data)
        relationship.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="link-ticket")
    def link_ticket(self, request, pk=None):
        asset = self.get_object()
        if not is_staff_user(request.user):
            raise PermissionDenied()
        serializer = LinkTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.validated_data["help_request"]
        # Only tickets the user can already see may be linked.
        if not visible_HelpRequests(request.user, HelpRequests.objects.filter(pk=ticket.pk)).exists():
            raise ValidationError({"help_request": "Ticket not found."})
        if serializer.validated_data["unlink"]:
            asset.help_requests.remove(ticket)
        else:
            asset.help_requests.add(ticket)
        write_audit_event(request, "asset.ticket_unlinked" if serializer.validated_data["unlink"] else "asset.ticket_linked",
                          obj=asset, metadata={"help_request": str(ticket.public_id)})
        return Response(AssetSerializer(asset, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        asset = self.get_object()
        if not (is_staff_user(request.user) or has_role(request.user, AUDITOR)):
            raise PermissionDenied()
        events = AuditEvent.objects.filter(object_type="assets.asset", object_id=str(asset.pk)).select_related("initiated_by")[:100]
        return Response(AuditEventSerializer(events, many=True).data)
