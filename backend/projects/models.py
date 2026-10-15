from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from helprequests.models import HelpRequests

PROJECT_KEY = RegexValidator(r"^[A-Z][A-Z0-9]{1,9}$", "Use 2-10 capital letters or digits, starting with a letter.")


class Project(models.Model):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On hold"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    key = models.CharField(max_length=10, unique=True, validators=[PROJECT_KEY])
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROPOSED)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="managed_projects")
    start_date = models.DateField(null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    task_sequence = models.PositiveIntegerField(default=0, editable=False)
    custom_fields = models.JSONField(default=dict, blank=True)
    help_requests = models.ManyToManyField(HelpRequests, blank=True, related_name="projects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return f"{self.key} {self.name}"


class ProjectMember(models.Model):
    class Role(models.TextChoices):
        CONTRIBUTOR = "contributor", "Contributor"
        VIEWER = "viewer", "Viewer"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CONTRIBUTOR)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "user"], name="unique_project_member")]


class Milestone(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
    name = models.CharField(max_length=160)
    due_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["due_date", "pk"]

    def __str__(self):
        return self.name


class ProjectTask(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        BLOCKED = "blocked", "Blocked"
        DONE = "done", "Done"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    number = models.CharField(max_length=24, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    priority = models.PositiveSmallIntegerField(default=3)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="project_tasks")
    milestone = models.ForeignKey(Milestone, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    depends_on = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="blocks")
    due_date = models.DateField(null=True, blank=True)
    estimate_hours = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    position = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position", "pk"]

    def __str__(self):
        return f"{self.number} {self.title}"

    def notification_payload(self, base):
        return {"number": self.number, "subject": self.title, "project": self.project.name,
                "link": f"{base}/projects/{self.project.pk}"}
