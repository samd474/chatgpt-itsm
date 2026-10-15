from rest_framework import serializers

from .models import CatalogItem


class CatalogItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogItem
        fields = ["id", "name", "slug", "short_description", "description", "form_schema", "requires_approval", "active"]
        read_only_fields = fields


class CatalogSubmitSerializer(serializers.Serializer):
    request_payload = serializers.DictField()


class CatalogItemAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogItem
        fields = ["id", "name", "slug", "short_description", "description", "category", "service", "assignment_group",
                  "form_schema", "fulfillment_tasks", "default_impact", "default_urgency", "requires_approval",
                  "approvers", "active"]

    def validate(self, attrs):
        from django.core.exceptions import ValidationError as DjangoValidationError

        approvers = attrs.pop("approvers", None)
        candidate = CatalogItem(**{**({f.name: getattr(self.instance, f.name) for f in CatalogItem._meta.concrete_fields} if self.instance else {}), **attrs})
        try:
            candidate.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        if approvers is not None:
            attrs["approvers"] = approvers
        return attrs
