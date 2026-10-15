from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class CatalogItem(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    short_description = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    category = models.ForeignKey("helprequests.Category", null=True, blank=True, on_delete=models.PROTECT)
    service = models.ForeignKey("helprequests.Services", null=True, blank=True, on_delete=models.PROTECT)
    assignment_group = models.ForeignKey("helprequests.SupportGroups", null=True, blank=True, on_delete=models.SET_NULL)
    form_schema = models.JSONField(default=list, blank=True)
    default_impact = models.PositiveSmallIntegerField(default=3)
    default_urgency = models.PositiveSmallIntegerField(default=3)
    requires_approval = models.BooleanField(default=False)
    # Who approves. Empty means the assignment group's managers.
    approvers = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="catalog_items_to_approve")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        from .validation import validate_schema

        errors = validate_schema(self.form_schema)
        if errors:
            raise ValidationError({"form_schema": errors})
        for field in ("default_impact", "default_urgency"):
            if getattr(self, field) not in (1, 2, 3):
                raise ValidationError({field: "Use 1 (critical), 2 (high) or 3 (medium)."})
