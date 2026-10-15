from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db.models import F
from django.utils import timezone

from accounts.roles import MANAGER
from alerts.services import notify
from reports.audit import write_audit_event

from .models import Contract


@shared_task
def send_renewal_reminders():
    """Daily: remind owners (and managers) once per term about contracts nearing their end date."""
    today = timezone.localdate()
    managers = list(get_user_model().objects.filter(groups__name=MANAGER, is_active=True).distinct())
    sent = 0
    due = Contract.objects.select_related("vendor", "owner").filter(status=Contract.Status.ACTIVE, end_date__gte=today)
    for contract in due:
        if contract.end_date - timedelta(days=contract.renewal_notice_days) > today:
            continue
        # Claim the reminder first so retries never send duplicates.
        claimed = Contract.objects.filter(pk=contract.pk).exclude(reminder_sent_for=F("end_date")).update(reminder_sent_for=contract.end_date)
        if not claimed:
            continue
        notify("contract.renewal_due", contract, recipients=[contract.owner, *managers])
        write_audit_event(None, "contract.renewal_reminder", obj=contract, actor=None, metadata={"end_date": contract.end_date})
        sent += 1
    # Contracts whose end date has passed become expired (unless auto-renewing).
    Contract.objects.filter(status=Contract.Status.ACTIVE, end_date__lt=today, auto_renew=False).update(status=Contract.Status.EXPIRED)
    return sent
