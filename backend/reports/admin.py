from django.contrib import admin

from .models import AuditEvent, ImportJob


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "activity_type", "object_type", "object_id", "initiated_by", "request_id")
    list_filter = ("activity_type", "object_type")
    search_fields = ("object_id", "request_id")
    readonly_fields = [field.name for field in AuditEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "state", "original_name", "uploaded_by", "confirmed_by")
    readonly_fields = [field.name for field in ImportJob._meta.fields]

    def has_add_permission(self, request):
        return False
