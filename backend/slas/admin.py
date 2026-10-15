from django.contrib import admin

from .models import BusinessCalendar, BusinessHours, Holiday, SLAPolicy, TicketSLA


class BusinessHoursInline(admin.TabularInline):
    model = BusinessHours
    extra = 0


class HolidayInline(admin.TabularInline):
    model = Holiday
    extra = 0


@admin.register(BusinessCalendar)
class BusinessCalendarAdmin(admin.ModelAdmin):
    list_display = ("name", "timezone")
    inlines = [BusinessHoursInline, HolidayInline]


@admin.register(SLAPolicy)
class SLAPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "ticket_type", "priority", "calendar", "response_minutes", "resolution_minutes", "warn_percent", "active")
    list_filter = ("ticket_type", "priority", "active")


@admin.register(TicketSLA)
class TicketSLAAdmin(admin.ModelAdmin):
    list_display = ("help_request", "policy", "response_due_at", "resolution_due_at", "response_breached", "resolution_breached", "pause_started_at")
    list_filter = ("response_breached", "resolution_breached")
    readonly_fields = [field.name for field in TicketSLA._meta.fields]

    def has_add_permission(self, request):
        return False
