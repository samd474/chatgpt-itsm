from datetime import time

from django.core.management.base import BaseCommand

from helprequests.models import HelpRequests
from slas.models import BusinessCalendar, BusinessHours, SLAPolicy

# priority -> (response minutes, resolution minutes)
INCIDENT_TARGETS = {1: (15, 240), 2: (60, 480), 3: (240, 1440), 4: (480, 2880)}
REQUEST_TARGETS = {1: (60, 960), 2: (240, 1440), 3: (480, 2880), 4: (960, 4800)}


class Command(BaseCommand):
    help = "Create a starter business calendar and SLA policies (safe to run more than once)."

    def add_arguments(self, parser):
        parser.add_argument("--timezone", default="America/New_York")

    def handle(self, *args, **options):
        business, created = BusinessCalendar.objects.get_or_create(
            name="Standard business hours", defaults={"timezone": options["timezone"]},
        )
        if created:
            for weekday in range(5):
                BusinessHours.objects.create(calendar=business, weekday=weekday, start_time=time(8), end_time=time(17))
        always_on, _ = BusinessCalendar.objects.get_or_create(name="24x7", defaults={"timezone": "UTC"})

        for ticket_type, targets in (
            (HelpRequests.RequestType.INCIDENT, INCIDENT_TARGETS),
            (HelpRequests.RequestType.REQUEST, REQUEST_TARGETS),
        ):
            for priority, (response, resolution) in targets.items():
                calendar = always_on if (ticket_type == HelpRequests.RequestType.INCIDENT and priority == 1) else business
                _, made = SLAPolicy.objects.get_or_create(
                    ticket_type=ticket_type,
                    priority=priority,
                    defaults={
                        "name": f"{ticket_type.label} P{priority}",
                        "calendar": calendar,
                        "response_minutes": response,
                        "resolution_minutes": resolution,
                    },
                )
                self.stdout.write(f"{'created' if made else 'exists '} {ticket_type.label} P{priority}")
