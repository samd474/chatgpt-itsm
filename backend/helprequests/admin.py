from django.contrib import admin

from .models import Approval, Attachment, Category, HelpRequests, HelpRequestsComment, PermissionGroups, Services, SupportGroups


@admin.register(SupportGroups)
class SupportGroupsAdmin(admin.ModelAdmin):
    list_display = ("name", "active")
    list_filter = ("active",)
    search_fields = ("name",)
    filter_horizontal = ("members", "managers")


@admin.register(PermissionGroups)
class PermissionGroupsAdmin(admin.ModelAdmin):
    list_display = ("name", "active")
    filter_horizontal = ("members", "managers")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "active")
    list_filter = ("active",)
    search_fields = ("name",)


@admin.register(Services)
class ServicesAdmin(admin.ModelAdmin):
    list_display = ("name", "managers", "active")
    list_filter = ("active",)
    search_fields = ("name",)


class CommentInline(admin.TabularInline):
    model = HelpRequestsComment
    extra = 0
    readonly_fields = ("author", "body", "visibility", "created_at")
    can_delete = False


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = ("original_name", "content_type", "size_bytes", "sha256", "uploaded_by", "created_at")
    exclude = ("file",)
    can_delete = False


@admin.register(HelpRequests)
class HelpRequestsAdmin(admin.ModelAdmin):
    """Read-mostly view. Status and assignment changes go through the API so they are audited."""

    list_display = ("request_number", "subject", "request_type", "status", "priority", "requester", "technician", "assignment_group", "created_at")
    list_filter = ("request_type", "status", "priority", "assignment_group")
    search_fields = ("request_number", "subject", "description")
    readonly_fields = [field.name for field in HelpRequests._meta.fields]
    inlines = [CommentInline, AttachmentInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ("help_request", "approver", "state", "decided_at", "created_at")
    list_filter = ("state",)
    readonly_fields = ("help_request", "approver", "state", "comment", "decided_at", "created_at")
