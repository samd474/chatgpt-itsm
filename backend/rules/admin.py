from django.contrib import admin

from .models import TicketRule


@admin.register(TicketRule)
class TicketRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "active", "stop_processing", "updated_at")
    list_filter = ("active",)
    ordering = ("position", "pk")
