import logging
from collections import defaultdict

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from accounts.models import User

from .models import NotificationDelivery, NotificationEvent
from .templates import TEMPLATES

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5


@shared_task(bind=True, max_retries=MAX_ATTEMPTS, default_retry_delay=60)
def send_notification(self, event_key):
    """Retry-safe: only deliveries still queued are sent, each row is locked while sending."""
    event = NotificationEvent.objects.get(event_key=event_key)
    subject_template, body_template = TEMPLATES[event.event_type]
    deliveries = NotificationDelivery.objects.filter(event=event)
    names = {
        user.email: user.get_full_name() or user.get_username()
        for user in User.objects.filter(email__in=deliveries.values("recipient"))
    }
    failed = False
    for delivery_id in deliveries.filter(status=NotificationDelivery.Status.QUEUED).values_list("id", flat=True):
        with transaction.atomic():
            delivery = NotificationDelivery.objects.select_for_update(skip_locked=True).filter(
                pk=delivery_id, status=NotificationDelivery.Status.QUEUED
            ).first()
            if delivery is None:
                continue
            context = defaultdict(str, event.payload, recipient_name=names.get(delivery.recipient, "there"))
            delivery.attempts += 1
            try:
                send_mail(
                    subject_template.format_map(context),
                    body_template.format_map(context),
                    settings.DEFAULT_FROM_EMAIL,
                    [delivery.recipient],
                )
                delivery.status = NotificationDelivery.Status.SENT
                delivery.sent_at = timezone.now()
                delivery.last_error = ""
            except Exception as exc:  # SMTP errors vary by backend
                logger.warning("notification delivery %s failed: %s", delivery.pk, exc)
                delivery.last_error = str(exc)[:2000]
                if delivery.attempts >= MAX_ATTEMPTS:
                    delivery.status = NotificationDelivery.Status.FAILED
                else:
                    failed = True
            delivery.save()
    if failed:
        raise self.retry()
