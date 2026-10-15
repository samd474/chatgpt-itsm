from rest_framework import serializers

from .models import CatalogItem


class CatalogItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogItem
        fields = ["id", "name", "slug", "short_description", "description", "form_schema", "requires_approval", "active"]
        read_only_fields = fields


class CatalogSubmitSerializer(serializers.Serializer):
    request_payload = serializers.DictField()
