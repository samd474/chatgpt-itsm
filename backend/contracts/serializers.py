from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.customfields import clean_custom_fields

from .models import Contract, Vendor

User = get_user_model()
FINANCIAL_FIELDS = ("value", "currency", "billing_frequency")


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ["id", "name", "contact_name", "email", "phone", "website", "notes", "active"]


class ContractSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), allow_null=True, required=False)
    owner_name = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    custom_fields = serializers.DictField(required=False)

    class Meta:
        model = Contract
        fields = ["id", "number", "name", "vendor", "vendor_name", "contract_type", "status", "start_date", "end_date",
                  "days_remaining", "value", "currency", "billing_frequency", "auto_renew", "renewal_notice_days",
                  "owner", "owner_name", "notes", "custom_fields", "assets", "services", "created_at", "updated_at"]
        read_only_fields = ["id", "number", "created_at", "updated_at"]

    def __init__(self, *args, show_financials=True, **kwargs):
        super().__init__(*args, **kwargs)
        if not show_financials:
            for field in FINANCIAL_FIELDS:
                self.fields.pop(field, None)

    def get_owner_name(self, obj):
        return (obj.owner.get_full_name() or obj.owner.get_username()) if obj.owner else None

    def get_days_remaining(self, obj):
        from django.utils import timezone

        return (obj.end_date - timezone.localdate()).days

    def validate_currency(self, value):
        value = value.upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Use a three-letter currency code.")
        return value

    def validate_custom_fields(self, value):
        return clean_custom_fields("contract", value, existing=self.instance.custom_fields if self.instance else None)

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "The end date can't be before the start date."})
        if "value" in attrs and attrs["value"] is not None and attrs["value"] < 0:
            raise serializers.ValidationError({"value": "Value can't be negative."})
        return attrs
