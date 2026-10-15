import uuid
from django.conf import settings
from django.db import models


class SupportGroups(models.Model):
    """Operational queue that owns tickets. Not a security role."""

    name = models.CharField(max_length=120, unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="support_groups", blank=True)
    managers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="managed_support_groups", blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "support group"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PermissionGroups(models.Model):
    name = models.CharField(max_length=120, unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="permission_groups", blank=True)
    managers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="managed_permission_groups", blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=120)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return f"{self.parent} / {self.name}" if self.parent else self.name


class Services(models.Model):
    name = models.CharField(max_length=160, unique=True)
    managers = models.ForeignKey(SupportGroups, null=True, blank=True, on_delete=models.SET_NULL)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "service"
        ordering = ["name"]

    def __str__(self):
        return self.name


class HelpRequests(models.Model):
    objects = models.Manager()

    class RequestType(models.TextChoices):
        INCIDENT = "incident", "Incident"
        REQUEST = "request", "Request"

    class RequestStatus(models.TextChoices):
        NEW = "new", "New"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        PENDING_USER_RESPONSE = "pending_user_response", "Pending User Response"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    class Level(models.IntegerChoices):
        """Shared scale for impact and urgency; see priority.PRIORITY_MATRIX."""

        CRITICAL = 1, "Critical"
        HIGH = 2, "High"
        MEDIUM = 3, "Medium"

    OPEN_STATUSES = (
        RequestStatus.NEW,
        RequestStatus.ASSIGNED,
        RequestStatus.IN_PROGRESS,
        RequestStatus.PENDING_USER_RESPONSE,
    )

    class Meta:
        verbose_name = "help request"
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["assignment_group", "status"]),
            models.Index(fields=["requester", "-created_at"]),
            models.Index(fields=["-created_at"]),
        ]
        permissions = [
            ("export_helprequests", "Can export help requests to CSV"),
        ]

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    # Filled in after insert by services.create_help_request (INC-000123 / REQ-000124).
    request_number = models.CharField(max_length=24, unique=True, null=True, editable=False)
    request_type = models.CharField(max_length=30, choices=RequestType.choices)
    subject = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="open_requests")
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="my_assigned_requests")
    assignment_group = models.ForeignKey(SupportGroups, null=True, blank=True, on_delete=models.SET_NULL)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.PROTECT)
    service = models.ForeignKey(Services, null=True, blank=True, on_delete=models.PROTECT)
    impact = models.PositiveSmallIntegerField(choices=Level.choices, default=Level.MEDIUM)
    urgency = models.PositiveSmallIntegerField(choices=Level.choices, default=Level.MEDIUM)
    priority = models.PositiveSmallIntegerField(default=4)
    status = models.CharField(max_length=30, choices=RequestStatus.choices, default=RequestStatus.NEW)
    request_payload = models.JSONField(default=dict, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    resolution_code = models.CharField(max_length=60, blank=True)
    resolution_body = models.TextField(blank=True)
    first_response_time = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.request_number or str(self.public_id)

    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES


class HelpRequestsComment(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    help_request = models.ForeignKey(HelpRequests, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField()
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "comment"
        ordering = ["created_at"]


class Attachment(models.Model):
    help_request = models.ForeignKey(HelpRequests, on_delete=models.CASCADE, related_name="attachments")
    comment = models.ForeignKey(HelpRequestsComment, null=True, blank=True, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file = models.FileField(upload_to="request_attachments/%Y/%m/")
    original_name = models.CharField(max_length=255)
    size_bytes = models.BigIntegerField()
    content_type = models.CharField(max_length=120)
    sha256 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Approval(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    help_request = models.ForeignKey(HelpRequests, on_delete=models.CASCADE, related_name="approvals")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="approvals")
    state = models.CharField(max_length=12, choices=State.choices, default=State.PENDING)
    comment = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class FulfillmentTask(models.Model):
    """A unit of work on a request (usually created from a catalog item's task templates)."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    OPEN_STATUSES = (Status.OPEN, Status.IN_PROGRESS)

    help_request = models.ForeignKey(HelpRequests, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assignment_group = models.ForeignKey(SupportGroups, null=True, blank=True, on_delete=models.SET_NULL)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="fulfillment_tasks")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    position = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position", "pk"]


class TicketTemplate(models.Model):
    """Administrator-defined starting point for common tickets."""

    name = models.CharField(max_length=120, unique=True)
    help_text = models.CharField(max_length=240, blank=True)
    request_type = models.CharField(max_length=30, choices=HelpRequests.RequestType.choices, default=HelpRequests.RequestType.INCIDENT)
    subject = models.CharField(max_length=240, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    service = models.ForeignKey(Services, null=True, blank=True, on_delete=models.SET_NULL)
    assignment_group = models.ForeignKey(SupportGroups, null=True, blank=True, on_delete=models.SET_NULL)
    impact = models.PositiveSmallIntegerField(choices=HelpRequests.Level.choices, default=HelpRequests.Level.MEDIUM)
    urgency = models.PositiveSmallIntegerField(choices=HelpRequests.Level.choices, default=HelpRequests.Level.MEDIUM)
    available_to_requesters = models.BooleanField(default=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Queue(models.Model):
    """A saved, administrator-defined view of tickets (always intersected with the viewer's scope)."""

    class Ordering(models.TextChoices):
        PRIORITY = "priority", "Highest priority first"
        OLDEST = "created_at", "Oldest first"
        NEWEST = "-created_at", "Newest first"
        UPDATED = "-updated_at", "Recently updated"

    name = models.CharField(max_length=120, unique=True)
    description = models.CharField(max_length=240, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    ordering = models.CharField(max_length=20, choices=Ordering.choices, default=Ordering.PRIORITY)
    # Role names that see this queue; empty means every staff member.
    visible_to_roles = models.JSONField(default=list, blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "name"]

    def __str__(self):
        return self.name
