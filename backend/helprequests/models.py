import uuid

from django.conf import settings
from django.db import models


class SupportGroups(models.Model):
    name = models.CharField(max_length=120, unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="support_groups", blank=True)
    managers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="managed_support_groups", blank=True)


class PermissionGroups(models.Model):
    name = models.CharField(max_length=120, unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="permission_groups", blank=True)
    managers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="managed_permission_groups", blank=True)
    active = models.BooleanField(default=True)


class Category(models.Model):
    name = models.CharField(max_length=120)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT)
    active = models.BooleanField(default=True)


class Services(models.Model):
    name = models.CharField(max_length=160, unique=True)
    managers = models.ForeignKey(SupportGroups, null=True, blank=True, on_delete=models.SET_NULL)
    active = models.BooleanField(default=True)


def create_help_request(**data):
    return HelpRequests.objects.create(**data)


class HelpRequests(models.Model):
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

    class Impact(models.TextChoices):
        USER = "user", "User"
        DEPARTMENT = "department", "Department"
        CUSTOMER = "customer", "Customer"
        BUSINESS = "business", "Business"

    class Urgency(models.TextChoices):
        HIGH = "high", "High"
        NORMAL = "normal", "Normal"
        LOW = "low", "Low"
    
    class Meta:
        indexes = [
            models.Index(fields=["status", "impact"]),
            models.Index(fields=["assignment_group"]),
            models.Index(fields=["-created_at"]),
        ]

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    request_number = models.CharField(max_length=24)
    request_type = models.CharField(max_length=30, choices=RequestType.choices)
    subject = models.CharField(max_length=240)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="open_requests")
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="my_assigned_requests")
    assignment_group = models.ForeignKey(SupportGroups, null=True, blank=True, on_delete=models.SET_NULL)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.PROTECT)
    service = models.ForeignKey(Services, null=True, blank=True, on_delete=models.PROTECT)
    impact = models.CharField(max_length=20, choices=Impact.choices, default=Impact.USER)
    urgency = models.CharField(max_length=20, choices=Urgency.choices, default=Urgency.NORMAL)
    status = models.CharField(max_length=30, choices=RequestStatus.choices, default=RequestStatus.NEW)
    request_payload = models.JSONField(default=dict, blank=True)
    resolution_code = models.CharField(max_length=60, blank=True)
    resolution_body = models.TextField(blank=True)
    first_response_time = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class HelpRequestComment(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "PUBLIC"
        PRIVATE = "private", "PRIVATE"

    help_request = models.ForeignKey(HelpRequests, on_delete=models.CASCADE, related_name="comments")
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField()
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(null=True, blank=True)
class Attachment(models.Model):
    HelpRequests = models.ForeignKey(HelpRequests, on_delete=models.CASCADE, related_name="attachments")
    comment = models.ForeignKey(HelpRequestComment, null=True, blank=True, on_delete=models.CASCADE, related_name="attachment")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file_name = models.FileField(upload_to="request_attachments/%Y/%M")
    original_name = models.CharField(max_length=255)
    size_bytes = models.BigIntegerField()
    content_type = models.CharField(max_length=120)
    sha256 = models.CharField(64)
    created_at = models.DateTimeField(auto_now_add=True)









