from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

FIELD_KEY = RegexValidator(r"^[a-z][a-z0-9_]{0,49}$", "Use lowercase letters, digits and underscores, starting with a letter.")


class CustomFieldDefinition(models.Model):
    """Administrator-defined extra fields, stored in each record's `custom_fields` JSON."""

    class Entity(models.TextChoices):
        TICKET = "ticket", "Ticket"
        ASSET = "asset", "Asset"
        CHANGE = "change", "Change"
        PROJECT = "project", "Project"
        CONTRACT = "contract", "Contract"

    class FieldType(models.TextChoices):
        TEXT = "text", "Text"
        TEXTAREA = "textarea", "Long text"
        DATE = "date", "Date"
        BOOLEAN = "boolean", "Yes/no"
        SELECT = "select", "Choice"

    entity = models.CharField(max_length=20, choices=Entity.choices)
    key = models.CharField(max_length=50, validators=[FIELD_KEY])
    label = models.CharField(max_length=120)
    field_type = models.CharField(max_length=20, choices=FieldType.choices, default=FieldType.TEXT)
    options = models.JSONField(default=list, blank=True)
    required = models.BooleanField(default=False)
    # Ticket fields only: whether requesters see and fill this field.
    visible_to_requester = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["entity", "position", "label"]
        constraints = [models.UniqueConstraint(fields=["entity", "key"], name="unique_custom_field_key")]

    def __str__(self):
        return f"{self.Entity(self.entity).label}: {self.label}"

    def clean(self):
        if self.field_type == self.FieldType.SELECT:
            if not isinstance(self.options, list) or not self.options or not all(isinstance(o, str) and o for o in self.options):
                raise ValidationError({"options": "Choice fields need a list of option labels."})
        elif self.options:
            raise ValidationError({"options": "Only choice fields have options."})

    def as_schema(self):
        field = {"key": self.key, "label": self.label, "type": self.field_type, "required": self.required}
        if self.field_type == self.FieldType.SELECT:
            field["options"] = self.options
        return field
