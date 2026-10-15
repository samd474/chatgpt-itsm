from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models


class AuditEvent(models.Model):
    """Append-only record of a meaningful change. Never updated or deleted by the app."""

    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    activity_type = models.CharField(max_length=80)
    object_type = models.CharField(max_length=80)
    object_id = models.CharField(max_length=80)
    request_id = models.CharField(max_length=64, blank=True, default="")
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["object_type", "object_id"]),
            models.Index(fields=["activity_type", "-created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionDenied("Audit events are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Audit events are append-only.")


class ImportJob(models.Model):
    """A staged CSV import: upload -> validate/preview -> confirm -> apply."""

    class Kind(models.TextChoices):
        CATEGORIES = "categories", "Categories"
        SERVICES = "services", "Services"

    class State(models.TextChoices):
        VALIDATED = "validated", "Validated"
        APPLIED = "applied", "Applied"
        FAILED = "failed", "Failed"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    state = models.CharField(max_length=20, choices=State.choices, default=State.VALIDATED)
    original_name = models.CharField(max_length=255)
    content = models.TextField()
    preview = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
