from django.contrib import admin

from .models import ChangeApproval, ChangeRequest


class ApprovalInline(admin.TabularInline):
    model = ChangeApproval
    extra = 0
    readonly_fields = ("approver", "state", "comment", "decided_at")
    can_delete = False


@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    """Read-mostly: lifecycle changes go through the API so they are validated and audited."""

    list_display = ("number", "title", "change_type", "status", "risk", "planned_start", "requested_by")
    list_filter = ("status", "change_type", "risk")
    search_fields = ("number", "title")
    readonly_fields = ("status", "number", "requested_by", "actual_start", "actual_end", "outcome")
    inlines = [ApprovalInline]
