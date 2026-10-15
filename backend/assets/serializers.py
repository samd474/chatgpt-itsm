from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.customfields import clean_custom_fields
from helprequests.models import HelpRequests

from .models import Asset, AssetRelationship, AssetType, Location

User = get_user_model()


def _name(user):
    return (user.get_full_name() or user.get_username()) if user else None


class AssetTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetType
        fields = ["id", "name", "description", "active"]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "name", "address", "active"]


class AssetSerializer(serializers.ModelSerializer):
    asset_type_name = serializers.CharField(source="asset_type.name", read_only=True)
    location_name = serializers.CharField(source="location.name", default=None, read_only=True)
    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), allow_null=True, required=False)
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), allow_null=True, required=False)
    owner_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    custom_fields = serializers.DictField(required=False)
    linked_tickets = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = ["id", "asset_tag", "name", "asset_type", "asset_type_name", "status", "serial_number", "manufacturer",
                  "model", "location", "location_name", "owner", "owner_name", "assigned_to", "assigned_to_name",
                  "support_group", "purchase_date", "purchase_cost", "warranty_expires", "notes", "custom_fields",
                  "linked_tickets", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_owner_name(self, obj):
        return _name(obj.owner)

    def get_assigned_to_name(self, obj):
        return _name(obj.assigned_to)

    def get_linked_tickets(self, obj):
        return [{"public_id": str(t.public_id), "request_number": t.request_number, "subject": t.subject, "status": t.status}
                for t in obj.help_requests.all()[:20]]

    def validate_asset_tag(self, value):
        return value.strip().upper()

    def validate_custom_fields(self, value):
        existing = self.instance.custom_fields if self.instance else None
        return clean_custom_fields("asset", value, existing=existing)


class RequesterAssetSerializer(serializers.ModelSerializer):
    """What a requester may see about equipment assigned to them: no cost, notes or links."""

    asset_type_name = serializers.CharField(source="asset_type.name", read_only=True)
    location_name = serializers.CharField(source="location.name", default=None, read_only=True)

    class Meta:
        model = Asset
        fields = ["id", "asset_tag", "name", "asset_type_name", "status", "serial_number", "manufacturer", "model",
                  "location_name", "warranty_expires"]
        read_only_fields = fields


class AssetRelationshipSerializer(serializers.ModelSerializer):
    source_label = serializers.CharField(source="source.__str__", read_only=True)
    target_label = serializers.CharField(source="target.__str__", read_only=True)

    class Meta:
        model = AssetRelationship
        fields = ["id", "source", "source_label", "target", "target_label", "kind"]

    def validate(self, attrs):
        if attrs["source"] == attrs["target"]:
            raise serializers.ValidationError("An asset can't relate to itself.")
        return attrs


class LinkTicketSerializer(serializers.Serializer):
    help_request = serializers.SlugRelatedField(slug_field="public_id", queryset=HelpRequests.objects.all())
    unlink = serializers.BooleanField(default=False)
