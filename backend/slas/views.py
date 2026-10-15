from zoneinfo import available_timezones

from rest_framework import serializers

from core.permissions import IsAdministrator
from core.viewsets import AuditedModelViewSet

from .models import BusinessCalendar, BusinessHours, Holiday, SLAPolicy


class BusinessHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessHours
        fields = ["weekday", "start_time", "end_time"]

    def validate(self, attrs):
        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError("End time must be after start time.")
        return attrs


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["date", "name"]


class BusinessCalendarSerializer(serializers.ModelSerializer):
    """Hours and holidays are replaced wholesale on save. No hours = 24x7."""

    hours = BusinessHoursSerializer(many=True, required=False)
    holidays = HolidaySerializer(many=True, required=False)

    class Meta:
        model = BusinessCalendar
        fields = ["id", "name", "timezone", "hours", "holidays"]

    def validate_timezone(self, value):
        if value not in available_timezones():
            raise serializers.ValidationError("Unknown time zone.")
        return value

    def _save_children(self, calendar, hours, holidays):
        if hours is not None:
            calendar.hours.all().delete()
            BusinessHours.objects.bulk_create([BusinessHours(calendar=calendar, **h) for h in hours])
        if holidays is not None:
            calendar.holidays.all().delete()
            Holiday.objects.bulk_create([Holiday(calendar=calendar, **h) for h in holidays])

    def create(self, validated_data):
        hours = validated_data.pop("hours", None)
        holidays = validated_data.pop("holidays", None)
        calendar = BusinessCalendar.objects.create(**validated_data)
        self._save_children(calendar, hours, holidays)
        return calendar

    def update(self, instance, validated_data):
        hours = validated_data.pop("hours", None)
        holidays = validated_data.pop("holidays", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        self._save_children(instance, hours, holidays)
        return instance


class SLAPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SLAPolicy
        fields = ["id", "name", "ticket_type", "priority", "calendar", "response_minutes", "resolution_minutes", "warn_percent", "active"]

    def validate(self, attrs):
        priority = attrs.get("priority", getattr(self.instance, "priority", None))
        if priority not in (1, 2, 3, 4):
            raise serializers.ValidationError({"priority": "Priority must be 1-4."})
        warn = attrs.get("warn_percent", getattr(self.instance, "warn_percent", 80))
        if not 1 <= warn <= 99:
            raise serializers.ValidationError({"warn_percent": "Use a percentage between 1 and 99."})
        response = attrs.get("response_minutes", getattr(self.instance, "response_minutes", 0))
        resolution = attrs.get("resolution_minutes", getattr(self.instance, "resolution_minutes", 0))
        if response > resolution:
            raise serializers.ValidationError({"response_minutes": "Response target can't exceed the resolution target."})
        return attrs


class BusinessCalendarViewSet(AuditedModelViewSet):
    serializer_class = BusinessCalendarSerializer
    permission_classes = [IsAdministrator]
    pagination_class = None
    queryset = BusinessCalendar.objects.prefetch_related("hours", "holidays")
    audit_prefix = "config.business_calendar"


class SLAPolicyViewSet(AuditedModelViewSet):
    serializer_class = SLAPolicySerializer
    permission_classes = [IsAdministrator]
    pagination_class = None
    queryset = SLAPolicy.objects.select_related("calendar")
    audit_prefix = "config.sla_policy"
