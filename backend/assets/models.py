from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from helprequests.models import HelpRequests, SupportGroups


class AssetType(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.CharField(max_length=240, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=160, unique=True)
    address = models.CharField(max_length=300, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Asset(models.Model):
    class Status(models.TextChoices):
        IN_STOCK = "in_stock", "In stock"
        IN_USE = "in_use", "In use"
        IN_REPAIR = "in_repair", "In repair"
        RETIRED = "retired", "Retired"
        DISPOSED = "disposed", "Disposed"
        LOST = "lost", "Lost/stolen"

    asset_tag = models.CharField(max_length=40, unique=True, blank=True)
    name = models.CharField(max_length=200)
    asset_type = models.ForeignKey(AssetType, on_delete=models.PROTECT, related_name="assets")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_STOCK)
    serial_number = models.CharField(max_length=120, blank=True)
    manufacturer = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=120, blank=True)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name="assets")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_assets")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_assets")
    support_group = models.ForeignKey(SupportGroups, null=True, blank=True, on_delete=models.SET_NULL)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    warranty_expires = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    help_requests = models.ManyToManyField(HelpRequests, blank=True, related_name="assets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["asset_tag"]
        indexes = [models.Index(fields=["status", "asset_type"]), models.Index(fields=["serial_number"])]

    def __str__(self):
        return f"{self.asset_tag} {self.name}"


class AssetRelationship(models.Model):
    class Kind(models.TextChoices):
        DEPENDS_ON = "depends_on", "Depends on"
        RUNS_ON = "runs_on", "Runs on"
        CONNECTED_TO = "connected_to", "Connected to"
        CONTAINS = "contains", "Contains"

    source = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="outgoing_relationships")
    target = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="incoming_relationships")
    kind = models.CharField(max_length=20, choices=Kind.choices)

    source_id: int
    target_id: int

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "target", "kind"], name="unique_asset_relationship"),
            models.CheckConstraint(condition=~models.Q(source=models.F("target")), name="asset_relationship_not_self"),
        ]

    def clean(self):
        if self.source_id == self.target_id:
            raise ValidationError("An asset can't relate to itself.")
