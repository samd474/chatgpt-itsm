from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class ITSMUserAdmin(UserAdmin):
    fieldsets = (
        *(UserAdmin.fieldsets or ()),
        ("Organization", {"fields": ("department", "location", "title", "is_enabled")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "department", "is_enabled", "is_staff")
    list_filter = (*UserAdmin.list_filter, "is_enabled", "department")

    PRIVILEGED_FIELDS = ("is_superuser", "is_staff", "user_permissions", "groups")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if getattr(request.user, "is_superuser", False) else qs.filter(is_superuser=False)

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        if getattr(request.user, "is_superuser", False):
            return readonly
        # Role changes go through the audited admin console API with its escalation guards.
        return (*readonly, *self.PRIVILEGED_FIELDS, "last_login", "date_joined")
