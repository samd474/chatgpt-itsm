from celery import shared_task
from django.db import transaction
from django.utils import timezone

from helprequests.models import HelpRequests

from .models import TicketSLA
from .services import check_ticket_sla


@shared_task
def check_sla_thresholds():
    now = timezone.now()
    active = (
        TicketSLA.objects.select_related("help_request__technician", "help_request__assignment_group", "policy")
        .filter(help_request__status__in=HelpRequests.OPEN_STATUSES, pause_started_at__isnull=True)
        .exclude(resolution_breached=True, response_breached=True)
    )
    checked = 0
    for sla in active.iterator(chunk_size=500):
        with transaction.atomic():
            check_ticket_sla(sla, now)
        checked += 1
    return checked
