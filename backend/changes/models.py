from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager

from assets.models import Asset
from helprequests.models import HelpRequests, Services, SupportGroups


class ChangeRequest(models.Model):
    class Type(models.TextChoices):
        STANDARD = "standard", "Standard (pre-approved)"
        NORMAL = "normal", "Normal"
        EMERGENCY = "emergency", "Emergency"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting approval"
        APPROVED = "approved", "Approved"
        SCHEDULED = "scheduled", "Scheduled"
        IMPLEMENTING = "implementing", "Implementing"
        REVIEW = "review", "Post-implementation review"
        CLOSED = "closed", "Closed"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    class Risk(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class Outcome(models.TextChoices):
        SUCCESSFUL = "successful", "Successful"
        PARTIAL = "partial", "Partially successful"
        FAILED = "failed", "Failed"
        BACKED_OUT = "backed_out", "Backed out"

    # Changes that hold their planned window (approved-but-unscheduled changes don't block anyone).
    ACTIVE_WINDOW_STATUSES = (Status.SCHEDULED, Status.IMPLEMENTING)

    number = models.CharField(max_length=24, unique=True, blank=True)
    title = models.CharField(max_length=240)
    description = models.TextField()
    justification = models.TextField(blank=True)
    change_type = models.CharField(max_length=20, choices=Type.choices, default=Type.NORMAL)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    risk = models.CharField(max_length=10, choices=Risk.choices, default=Risk.MEDIUM)
    impact = models.PositiveSmallIntegerField(choices=HelpRequests.Level.choices, default=HelpRequests.Level.MEDIUM)
    service = models.ForeignKey(Services, null=True, blank=True, on_delete=models.SET_NULL)
    assignment_group = models.ForeignKey(SupportGroups, null=True, blank=True, on_delete=models.SET_NULL)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_changes")
    implementer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="implemented_changes")
    implementation_plan = models.TextField(blank=True)
    backout_plan = models.TextField(blank=True)
    test_plan = models.TextField(blank=True)
    planned_start = models.DateTimeField(null=True, blank=True)
    planned_end = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=20, choices=Outcome.choices, blank=True)
    closure_notes = models.TextField(blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    assets = models.ManyToManyField(Asset, blank=True, related_name="changes")
    help_requests = models.ManyToManyField(HelpRequests, blank=True, related_name="changes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Declared for the type checker (Django adds these at runtime).
    requested_by_id: int
    implementer_id: int | None
    service_id: int | None
    if TYPE_CHECKING:
        approvals: "RelatedManager[ChangeApproval]"

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "planned_start"])]

    def __str__(self):
        return f"{self.number} {self.title}"

    def notification_payload(self, base):
        return {
            "number": self.number,
            "subject": self.title,
            "change_type": ChangeRequest.Type(self.change_type).label,
            "risk": self.risk,
            "planned_start": self.planned_start.isoformat() if self.planned_start else "TBD",
            "link": f"{base}/changes/{self.pk}",
        }


class ChangeApproval(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    change = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, related_name="approvals")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="change_approvals")
    state = models.CharField(max_length=12, choices=State.choices, default=State.PENDING)
    comment = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    approver_id: int
    change_id: int

    class Meta:
        ordering = ["created_at"]
