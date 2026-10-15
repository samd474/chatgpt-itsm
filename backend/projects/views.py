from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response

from accounts.roles import ADMINISTRATOR, AUDITOR, MANAGER, has_role
from alerts.services import notify
from core.viewsets import AuditedModelViewSet
from reports.audit import write_audit_event

from .access import can_contribute, can_manage, visible_projects
from .models import Milestone, Project, ProjectTask
from .serializers import MilestoneSerializer, ProjectSerializer, ProjectTaskSerializer


class NoAuditorWrites(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return not (has_role(request.user, AUDITOR) and not has_role(request.user, MANAGER, ADMINISTRATOR))


class ProjectViewSet(AuditedModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, NoAuditorWrites]
    audit_prefix = "project"
    filterset_fields = ["status", "manager"]
    search_fields = ["key", "name", "description"]
    ordering_fields = ["key", "name", "target_date", "updated_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Project.objects.select_related("manager").prefetch_related("memberships__user")
        return visible_projects(self.request.user, qs)

    def perform_create(self, serializer):
        if not has_role(self.request.user, MANAGER, ADMINISTRATOR):
            raise PermissionDenied("Only managers and administrators can create projects.")
        super().perform_create(serializer)

    def perform_update(self, serializer):
        if not can_manage(self.request.user, serializer.instance):
            raise PermissionDenied("Only the project manager or an administrator can edit this project.")
        new_status = serializer.validated_data.get("status")
        if new_status == Project.Status.COMPLETED and serializer.instance.completed_at is None:
            serializer.validated_data["completed_at"] = timezone.now()
        super().perform_update(serializer)


class ProjectScopedViewSet(AuditedModelViewSet):
    """Milestones and tasks: visible when the project is visible; writes need project rights."""

    permission_classes = [IsAuthenticated, NoAuditorWrites]
    model: Any = None
    write_check = staticmethod(can_contribute)

    def get_queryset(self):
        projects = visible_projects(self.request.user, Project.objects.all())
        return self.model.objects.filter(project__in=projects).select_related("project")

    def _check(self, project):
        if not visible_projects(self.request.user, Project.objects.filter(pk=project.pk)).exists():
            raise ValidationError({"project": "Project not found."})
        if not self.write_check(self.request.user, project):
            raise PermissionDenied("You don't have edit rights on this project.")

    def perform_create(self, serializer):
        self._check(serializer.validated_data["project"])
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._check(serializer.instance.project)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._check(instance.project)
        super().perform_destroy(instance)


class MilestoneViewSet(ProjectScopedViewSet):
    serializer_class = MilestoneSerializer
    model = Milestone
    audit_prefix = "project.milestone"
    filterset_fields = ["project", "completed"]
    pagination_class = None
    write_check = staticmethod(can_manage)


class ProjectTaskViewSet(ProjectScopedViewSet):
    serializer_class = ProjectTaskSerializer
    model = ProjectTask
    audit_prefix = "project.task"
    filterset_fields = ["project", "status", "assignee", "milestone"]
    search_fields = ["number", "title"]
    ordering_fields = ["position", "due_date", "priority"]

    def get_queryset(self):
        return super().get_queryset().select_related("assignee").prefetch_related("depends_on")

    def perform_create(self, serializer):
        self._check(serializer.validated_data["project"])
        with transaction.atomic():
            project = Project.objects.select_for_update().get(pk=serializer.validated_data["project"].pk)
            project.task_sequence += 1
            project.save(update_fields=["task_sequence"])
            task = serializer.save(created_by=self.request.user, number=f"{project.key}-{project.task_sequence}")
        write_audit_event(self.request, "project.task.created", obj=task, after=self._snapshot(task))
        if task.assignee_id and task.assignee_id != self.request.user.pk:
            notify("project.task_assigned", task, recipients=[task.assignee])

    def perform_update(self, serializer):
        task = serializer.instance
        user = self.request.user
        # Assignees may move their own task through its statuses even as viewers.
        only_status = set(serializer.validated_data) <= {"status"}
        if not (only_status and task.assignee_id == user.pk):
            self._check(task.project)
        new_status = serializer.validated_data.get("status")
        if new_status == ProjectTask.Status.DONE:
            blocking = task.depends_on.exclude(status=ProjectTask.Status.DONE)
            if blocking.exists():
                raise ValidationError({"status": f"Finish {', '.join(t.number for t in blocking)} first."})
            serializer.validated_data["completed_at"] = timezone.now()
        elif new_status is not None:
            serializer.validated_data["completed_at"] = None
        previous_assignee = task.assignee_id
        before = self._snapshot(task)
        task = serializer.save()
        write_audit_event(self.request, "project.task.updated", obj=task, before=before, after=self._snapshot(task))
        if task.assignee_id and task.assignee_id != previous_assignee and task.assignee_id != user.pk:
            notify("project.task_assigned", task, recipients=[task.assignee])

    @action(detail=False, methods=["get"])
    def mine(self, request):
        tasks = self.get_queryset().filter(assignee=request.user).exclude(status=ProjectTask.Status.DONE)
        return Response(self.get_serializer(tasks, many=True).data, status=status.HTTP_200_OK)
