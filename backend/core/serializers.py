from rest_framework import serializers

from .models import CustomFieldDefinition


class CustomFieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomFieldDefinition
        fields = ["id", "entity", "key", "label", "field_type", "options", "required", "visible_to_requester", "position", "active"]

    def validate(self, attrs):
        instance = CustomFieldDefinition(**{**({f: getattr(self.instance, f) for f in self.Meta.fields if f != "id"} if self.instance else {}), **attrs})
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        if self.instance is not None and "key" in attrs and attrs["key"] != self.instance.key:
            raise serializers.ValidationError({"key": "Keys can't change once data may be stored under them."})
        return attrs
