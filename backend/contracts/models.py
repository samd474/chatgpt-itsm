from django.conf import settings
from django.db import models

from assets.models import Asset
from helprequests.models import Services


class Vendor(models.Model):
    name = models.CharField(max_length=160, unique=True)
    contact_name = models.CharField(max_length=160, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=60, blank=True)
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Contract(models.Model):
    class Type(models.TextChoices):
        SUPPORT = "support", "Support"
        LICENSE = "license", "Software license"
        LEASE = "lease", "Lease"
        MAINTENANCE = "maintenance", "Maintenance"
        WARRANTY = "warranty", "Warranty"
        SERVICE = "service", "Service agreement"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        TERMINATED = "terminated", "Terminated"

    class Billing(models.TextChoices):
        ONE_TIME = "one_time", "One-time"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUAL = "annual", "Annual"

    number = models.CharField(max_length=40, unique=True, blank=True)
    name = models.CharField(max_length=200)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="contracts")
    contract_type = models.CharField(max_length=20, choices=Type.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    start_date = models.DateField()
    end_date = models.DateField()
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    billing_frequency = models.CharField(max_length=20, choices=Billing.choices, default=Billing.ANNUAL)
    auto_renew = models.BooleanField(default=False)
    renewal_notice_days = models.PositiveSmallIntegerField(default=30)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_contracts")
    notes = models.TextField(blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    assets = models.ManyToManyField(Asset, blank=True, related_name="contracts")
    services = models.ManyToManyField(Services, blank=True, related_name="contracts")
    # The end date a renewal reminder was last sent for, so reminders are sent once per term.
    reminder_sent_for = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["end_date"]
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")), name="contract_end_after_start"),
        ]

    def __str__(self):
        return f"{self.number} {self.name}"

    def notification_payload(self, base):
        return {
            "number": self.number,
            "subject": self.name,
            "vendor": self.vendor.name,
            "end_date": self.end_date.isoformat(),
            "link": f"{base}/contracts/{self.pk}",
        }
