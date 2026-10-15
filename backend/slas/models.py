from django.db import models

from helprequests.models import HelpRequests


class BusinessCalendar(models.Model):
    """A calendar with no BusinessHours rows is treated as 24x7."""

    name = models.CharField(max_length=120, unique=True)
    timezone = models.CharField(max_length=64, default="America/New_York")

    def __str__(self):
        return self.name


class BusinessHours(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0
        TUESDAY = 1
        WEDNESDAY = 2
        THURSDAY = 3
        FRIDAY = 4
        SATURDAY = 5
        SUNDAY = 6

    calendar = models.ForeignKey(BusinessCalendar, on_delete=models.CASCADE, related_name="hours")
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        verbose_name_plural = "business hours"
        ordering = ["weekday", "start_time"]
        constraints = [
            models.CheckConstraint(condition=models.Q(end_time__gt=models.F("start_time")), name="business_hours_end_after_start"),
        ]


class Holiday(models.Model):
    calendar = models.ForeignKey(BusinessCalendar, on_delete=models.CASCADE, related_name="holidays")
    date = models.DateField()
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date"], name="unique_holiday_per_calendar"),
        ]


class SLAPolicy(models.Model):
    name = models.CharField(max_length=120)
    ticket_type = models.CharField(max_length=30, choices=HelpRequests.RequestType.choices)
    priority = models.PositiveSmallIntegerField()
    calendar = models.ForeignKey(BusinessCalendar, on_delete=models.PROTECT)
    response_minutes = models.PositiveIntegerField()
    resolution_minutes = models.PositiveIntegerField()
    warn_percent = models.PositiveSmallIntegerField(default=80)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "SLA policy"
        verbose_name_plural = "SLA policies"
        ordering = ["ticket_type", "priority"]

    def __str__(self):
        return self.name


class TicketSLA(models.Model):
    help_request = models.OneToOneField(HelpRequests, on_delete=models.CASCADE, related_name="sla")
    policy = models.ForeignKey(SLAPolicy, on_delete=models.PROTECT)
    response_due_at = models.DateTimeField()
    resolution_due_at = models.DateTimeField()
    warning_due_at = models.DateTimeField()
    response_breached = models.BooleanField(default=False)
    resolution_breached = models.BooleanField(default=False)
    pause_started_at = models.DateTimeField(null=True, blank=True)
    paused_seconds = models.PositiveBigIntegerField(default=0)
    paused_business_minutes = models.PositiveIntegerField(default=0)
    warning_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "ticket SLA"
        indexes = [
            models.Index(fields=["resolution_due_at"]),
        ]
