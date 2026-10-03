from django.conf import settings
from django.db import models
import uuid

class SupportGroups(models.Model):
    name = models.CharField(max_length=120, unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="support_groups", blank=True)
    managers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="managed_support_groups", blank=True)

class PermissionGroups(models.Model):
    name = models.CharField(max_length=120, unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="support_groups", blank=True)
    managers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="managed_support_groups", blank=True)
    active = models.BooleanField(default=True)
class Category(models.Model):
    name = models.CharField(max_length=120)
    parent = models.ForeignKey("self", null=True, Blank=True, on_delete=models.PROTECT)
    active = models.BooleanField(default=True)
class Services(models.Model): 
    name = models.CharField(max_length=160, unique=True)
    managers = models.ForeignKey(SupportGroups, null=True, blank=True, on_delete=models.SET_NULL)
    active = models.BooleanField(default=True)



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

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    request_number = models.CharField(max_length=24)
    request_type = models.CharField(max_length=16, choices=RequestType.choices)
    subject = models.CharField(max_length=240)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="Open Requests")
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="My_Assigned_Requests")
    assignment_group = models.ForeignKey(SupportGroups, null=True, blank=True, on_delete=models.SET_NULL)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.PROTECT)
    service = models.ForeignKey(Services, null=True, blank=True, on_delete=models.PROTECT)
    impact = models.Choices("User", "Department", "Customer", "Business")
    urgency = models.Choices("High", "Normal", "Low")
    status = models.ForeignKey(max_length=20, choices=RequestStatus.choices, default=RequestStatus.NEW)
    request_payload = models.JSONField(default=dict, blank=True)
    resolution_code = models.CharField(max_length=60, blank=True)
    resolution_body = models.TextField(blank=True)
    first_response_time = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
class Meta:
    indexes = [
        models.Index(fields=["status", "priority"]), 
        models.Index(fields=[SupportGroups]),
        models.Index(fields=["-created_at"])
    ]






