from django.contrib import admin

from .models import Milestone, Project, ProjectMember, ProjectTask


class MemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "status", "manager", "target_date")
    list_filter = ("status",)
    search_fields = ("key", "name")
    inlines = [MemberInline]


@admin.register(ProjectTask)
class ProjectTaskAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "project", "status", "assignee", "due_date")
    list_filter = ("status", "project")


admin.site.register(Milestone)
