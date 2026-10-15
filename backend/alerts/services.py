from typing import cast

from celery import Task
from django.conf import settings
from django.db import transaction

from .models import NotificationDelivery, NotificationEvent
from .templates import TEMPLATES


def _ticket_payload(help_request):
    base = settings.FRONTEND_URL.rstrip("/")
    return {
        "number": help_request.request_number or "",
        "subject": help_request.subject,
        "priority": help_request.priority,
        "link": f"{base}/portal/tickets/{help_request.public_id}",
        "staff_link": f"{base}/tech/tickets/{help_request.public_id}",
        "approvals_link": f"{base}/approvals",
    }


def notify(event_type, help_request, *, recipients, payload=None):
    """Record an event plus one delivery per recipient and queue sending after commit."""
    if event_type not in TEMPLATES:
        raise ValueError(f"No notification template for {event_type}")
    emails = sorted({user.email for user in recipients if user is not None and user.email and user.is_active})
    event = NotificationEvent.objects.create(
        event_type=event_type,
        object_type="helprequests.helprequests",
        object_id=str(help_request.public_id),
        payload={**_ticket_payload(help_request), **(payload or {})},
    )
    NotificationDelivery.objects.bulk_create(
        [NotificationDelivery(event=event, recipient=email) for email in emails]
    )
    if emails:
        from .tasks import send_notification

        task = cast(Task, send_notification)
        # Never send for a transaction that later rolls back.
        transaction.on_commit(lambda: task.delay(str(event.event_key)))
    return event
