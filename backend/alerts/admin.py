from django.contrib import admin

from .models import NotificationDelivery, NotificationEvent


class DeliveryInline(admin.TabularInline):
    model = NotificationDelivery
    extra = 0
    readonly_fields = ("channel", "recipient", "status", "attempts", "last_error", "sent_at")
    can_delete = False


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event_type", "object_id")
    list_filter = ("event_type",)
    readonly_fields = ("event_key", "event_type", "object_type", "object_id", "payload", "created_at")
    inlines = [DeliveryInline]


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ("event", "recipient", "status", "attempts", "sent_at")
    list_filter = ("status", "channel")
    search_fields = ("recipient",)
