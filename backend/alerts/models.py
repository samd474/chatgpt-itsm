import uuid

from django.db import models


class NotificationEvent(models.Model):
    """A business event worth telling someone about."""

    event_key = models.UUIDField(default=uuid.uuid4, unique=True)
    event_type = models.CharField(max_length=80)
    object_type = models.CharField(max_length=80)
    object_id = models.CharField(max_length=80)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class NotificationDelivery(models.Model):
    """One recipient/channel attempt for an event."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    event = models.ForeignKey(NotificationEvent, on_delete=models.CASCADE, related_name="deliveries")
    channel = models.CharField(max_length=20, default="email")
    recipient = models.CharField(max_length=254)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "notification deliveries"
        constraints = [
            models.UniqueConstraint(fields=["event", "channel", "recipient"], name="unique_delivery_per_recipient"),
        ]


class NotificationTemplate(models.Model):
    """Administrator override of a built-in email template (see alerts.templates)."""

    event_type = models.CharField(max_length=80, unique=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["event_type"]
