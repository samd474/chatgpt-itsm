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
