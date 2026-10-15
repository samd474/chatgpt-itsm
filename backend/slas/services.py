from zoneinfo import ZoneInfo

from django.utils import timezone

from alerts.services import notify
from helprequests.models import HelpRequests
from reports.audit import write_audit_event

from .business_time import Schedule, add_business_minutes, business_minutes_between
from .models import SLAPolicy, TicketSLA

PAUSING_STATUSES = {HelpRequests.RequestStatus.PENDING_USER_RESPONSE}
FINISHED_STATUSES = {
    HelpRequests.RequestStatus.RESOLVED,
    HelpRequests.RequestStatus.CLOSED,
    HelpRequests.RequestStatus.CANCELLED,
}


def schedule_for(calendar):
    windows = {}
    for hours in calendar.hours.all():
        windows.setdefault(hours.weekday, []).append((hours.start_time, hours.end_time))
    return Schedule(
        tz=ZoneInfo(calendar.timezone),
        windows=windows,
        holidays=set(calendar.holidays.values_list("date", flat=True)),
    )


def find_policy(help_request):
    return (
        SLAPolicy.objects.select_related("calendar")
        .filter(active=True, ticket_type=help_request.request_type, priority=help_request.priority)
        .order_by("pk")
        .first()
    )


def _due_dates(policy, start, paused_business_minutes=0):
    schedule = schedule_for(policy.calendar)
    warn_minutes = policy.resolution_minutes * policy.warn_percent // 100
    return {
        "response_due_at": add_business_minutes(schedule, start, policy.response_minutes + paused_business_minutes),
        "resolution_due_at": add_business_minutes(schedule, start, policy.resolution_minutes + paused_business_minutes),
        "warning_due_at": add_business_minutes(schedule, start, warn_minutes + paused_business_minutes),
    }


def attach_sla(help_request):
    policy = find_policy(help_request)
    if policy is None:
        return None
    sla = TicketSLA.objects.create(help_request=help_request, policy=policy, **_due_dates(policy, help_request.created_at))
    write_audit_event(None, "sla.attached", obj=help_request, actor=None,
                      metadata={"policy": policy.name, "resolution_due_at": sla.resolution_due_at})
    return sla


def reapply_sla(help_request):
    """Priority or type changed: switch to the matching policy, keeping paused time."""
    sla = TicketSLA.objects.filter(help_request=help_request).first()
    if sla is None:
        return attach_sla(help_request)
    policy = find_policy(help_request)
    if policy is None or policy.pk == sla.policy.pk:
        return sla
    sla.policy = policy
    for field, value in _due_dates(policy, help_request.created_at, sla.paused_business_minutes).items():
        setattr(sla, field, value)
    sla.save()
    write_audit_event(None, "sla.reapplied", obj=help_request, actor=None,
                      metadata={"policy": policy.name, "resolution_due_at": sla.resolution_due_at})
    return sla


def _resume(sla, now):
    schedule = schedule_for(sla.policy.calendar)
    minutes = business_minutes_between(schedule, sla.pause_started_at, now)
    sla.paused_seconds += int((now - sla.pause_started_at).total_seconds())
    sla.paused_business_minutes += minutes
    sla.resolution_due_at = add_business_minutes(schedule, sla.resolution_due_at, minutes)
    sla.warning_due_at = add_business_minutes(schedule, sla.warning_due_at, minutes)
    sla.pause_started_at = None
    return minutes


def on_status_change(help_request, old_status, new_status, *, actor=None, request=None):
    sla = TicketSLA.objects.select_for_update().select_related("policy__calendar").filter(help_request=help_request).first()
    if sla is None:
        return
    now = timezone.now()
    if new_status in PAUSING_STATUSES and sla.pause_started_at is None:
        sla.pause_started_at = now
        sla.save(update_fields=["pause_started_at"])
        write_audit_event(request, "sla.paused", obj=help_request, actor=actor)
    elif new_status not in PAUSING_STATUSES and sla.pause_started_at is not None:
        # The pause_started_at guard means repeated requests never double-count.
        minutes = _resume(sla, now)
        sla.save()
        write_audit_event(request, "sla.resumed", obj=help_request, actor=actor,
                          metadata={"paused_business_minutes": minutes, "resolution_due_at": sla.resolution_due_at})


def on_first_response(help_request):
    """A late first response still records the response breach."""
    sla = TicketSLA.objects.filter(help_request=help_request).first()
    if sla and help_request.first_response_time > sla.response_due_at:
        if TicketSLA.objects.filter(pk=sla.pk, response_breached=False).update(response_breached=True):
            _breach_events(help_request, "response")


def sla_recipients(help_request):
    recipients = set()
    if help_request.technician_id:
        recipients.add(help_request.technician)
    if help_request.assignment_group_id:
        group = help_request.assignment_group
        recipients.update(group.managers.all())
        if not help_request.technician_id:
            recipients.update(group.members.all())
    return list(recipients)


def _breach_events(help_request, target):
    write_audit_event(None, "sla.breached", obj=help_request, actor=None, metadata={"target": target})
    notify("sla.breached", help_request, recipients=sla_recipients(help_request), payload={"target": target})


def check_ticket_sla(sla, now):
    """Idempotent: each state change is claimed with a guarded UPDATE before any event is emitted."""
    help_request = sla.help_request
    if help_request.status in FINISHED_STATUSES or sla.pause_started_at is not None:
        return
    if help_request.first_response_time is None and now >= sla.response_due_at:
        if TicketSLA.objects.filter(pk=sla.pk, response_breached=False).update(response_breached=True):
            _breach_events(help_request, "response")
    if now >= sla.resolution_due_at:
        if TicketSLA.objects.filter(pk=sla.pk, resolution_breached=False).update(resolution_breached=True):
            _breach_events(help_request, "resolution")
    elif now >= sla.warning_due_at:
        if TicketSLA.objects.filter(pk=sla.pk, warning_sent_at__isnull=True).update(warning_sent_at=now):
            write_audit_event(None, "sla.warning", obj=help_request, actor=None, metadata={"target": "resolution"})
            notify("sla.warning", help_request, recipients=sla_recipients(help_request), payload={"target": "resolution"})
