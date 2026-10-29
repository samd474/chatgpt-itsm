from django.db import models


class TicketRule(models.Model):
    """Automation that runs when a ticket is created and/or updated. Rules run in position order;
    every matching rule applies its actions (later ones win) unless a match has stop_processing set."""

    class RunsOn(models.TextChoices):
        CREATED = "created", "When a ticket is created"
        UPDATED = "updated", "When a ticket is updated"
        BOTH = "both", "Both"

    name = models.CharField(max_length=120)
    runs_on = models.CharField(max_length=10, choices=RunsOn.choices, default=RunsOn.CREATED)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    stop_processing = models.BooleanField(default=False, help_text="Skip later rules once this one matches.")
    conditions = models.JSONField(default=dict, blank=True)
    actions = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "pk"]

    def __str__(self):
        return self.name
