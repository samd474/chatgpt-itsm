"""SLA dashboard figures: what needs attention now, and how well targets were met over a period.

"Met" and "breached" are worked out from the timestamps as well as the breach flags, because the
flags are only set by the periodic check (slas.tasks.check_sla_thresholds): a ticket resolved late
between two checks, or one that is overdue right now, still counts as breached.
"""
from datetime import timedelta

from django.db.models import BooleanField, Case, CharField, Count, F, Q, Value, When
from django.db.models.functions import TruncDate
from django.utils import timezone

from helprequests.models import HelpRequests
from slas.models import TicketSLA

PERIODS = (7, 30, 90)
ATTENTION_LIMIT = 50

# Open tickets. Paused (waiting on the requester) due dates are stale until the pause ends, so a
# paused ticket only counts as breached if a breach was already recorded.
_RUNNING = Q(pause_started_at__isnull=True)


def _response_late(now):
    return Q(response_breached=True) | (_RUNNING & Q(help_request__first_response_time__isnull=True, response_due_at__lte=now))


def _resolution_late(now):
    return Q(resolution_breached=True) | (_RUNNING & Q(resolution_due_at__lte=now))


# Finished targets within the period.
_RESPONDED_LATE = Q(response_breached=True) | Q(help_request__first_response_time__gt=F("response_due_at"))
_RESOLVED_LATE = Q(resolution_breached=True) | Q(help_request__resolved_at__gt=F("resolution_due_at"))


def _live_state(now):
    return Case(
        When(_response_late(now) | _resolution_late(now), then=Value("breached")),
        When(~_RUNNING, then=Value("paused")),
        When(warning_due_at__lte=now, then=Value("at_risk")),
        default=Value("on_track"),
        output_field=CharField(),
    )


def _rate(met, total):
    return round(100 * met / total, 1) if total else None


def _compliance(rows):
    """{key: {...}} rows with *_total / *_late counts -> response/resolution met rates."""
    out = []
    for row in rows:
        out.append({
            "key": row["key"],
            "name": row["name"],
            "resolved": row["resolved"],
            "resolution_met_percent": _rate(row["resolved"] - row["resolved_late"], row["resolved"]),
            "responded": row["responded"],
            "response_met_percent": _rate(row["responded"] - row["responded_late"], row["responded"]),
            "open_breached": row["open_breached"],
        })
    return out


def build(tickets, *, days, now=None):
    """`tickets` is the HelpRequests queryset the viewer may see (already filtered)."""
    now = now or timezone.now()
    tz = timezone.get_current_timezone()
    start = now - timedelta(days=days)
    slas = TicketSLA.objects.filter(help_request__in=tickets.values("pk"))

    # --- now ------------------------------------------------------------------------------------
    open_slas = slas.filter(help_request__status__in=HelpRequests.OPEN_STATUSES).annotate(state=_live_state(now))
    counts = {"breached": 0, "at_risk": 0, "paused": 0, "on_track": 0}
    counts.update({row["state"]: row["n"] for row in open_slas.values("state").annotate(n=Count("pk"))})
    open_without_sla = tickets.filter(status__in=HelpRequests.OPEN_STATUSES, sla__isnull=True).count()

    attention = []
    rows = (open_slas.filter(state__in=["breached", "at_risk"])
            .select_related("help_request__assignment_group", "help_request__technician")
            .annotate(resolution_late=Case(When(_resolution_late(now), then=Value(True)), default=Value(False),
                                           output_field=BooleanField()))
            .order_by(Case(When(state="breached", then=Value(0)), default=Value(1)), "resolution_due_at")
            [:ATTENTION_LIMIT])
    for sla in rows:
        ticket = sla.help_request
        state = getattr(sla, "state")  # annotated above
        # The target that was missed (resolution wins when both were), or the one about to be.
        if state == "breached" and not getattr(sla, "resolution_late"):
            target, due_at = "response", sla.response_due_at
        else:
            target, due_at = "resolution", sla.resolution_due_at
        attention.append({
            "public_id": ticket.public_id,
            "request_number": ticket.request_number,
            "subject": ticket.subject,
            "priority": ticket.priority,
            "status": ticket.status,
            "assignment_group": ticket.assignment_group.name if ticket.assignment_group else None,
            "technician": (ticket.technician.get_full_name() or ticket.technician.get_username()) if ticket.technician else None,
            "state": state,
            "target": target,
            "due_at": due_at,
            "paused": sla.pause_started_at is not None,
        })

    # --- the period ------------------------------------------------------------------------------
    resolved = slas.filter(help_request__resolved_at__gte=start, help_request__resolved_at__lte=now)
    responded = slas.filter(help_request__first_response_time__gte=start, help_request__first_response_time__lte=now)
    resolved_total, resolved_late = resolved.count(), resolved.filter(_RESOLVED_LATE).count()
    responded_total, responded_late = responded.count(), responded.filter(_RESPONDED_LATE).count()

    per_day = {
        row["day"]: row
        for row in resolved.annotate(day=TruncDate("help_request__resolved_at", tzinfo=tz))
        .values("day").annotate(total=Count("pk"), late=Count("pk", filter=_RESOLVED_LATE))
    }
    first_day = timezone.localtime(now, tz).date() - timedelta(days=days - 1)
    trend = []
    for offset in range(days):
        day = first_day + timedelta(days=offset)
        row = per_day.get(day, {"total": 0, "late": 0})
        trend.append({"date": day, "met": row["total"] - row["late"], "breached": row["late"]})

    def breakdown(key_field, label_field):
        stats = {}

        def bucket(key, label):
            return stats.setdefault(key, {"key": key, "name": label, "resolved": 0, "resolved_late": 0,
                                          "responded": 0, "responded_late": 0, "open_breached": 0})

        fields = [key_field] + ([label_field] if label_field else [])
        for row in resolved.values(*fields).annotate(n=Count("pk"), late=Count("pk", filter=_RESOLVED_LATE)):
            b = bucket(row[key_field], row.get(label_field))
            b["resolved"], b["resolved_late"] = row["n"], row["late"]
        for row in responded.values(*fields).annotate(n=Count("pk"), late=Count("pk", filter=_RESPONDED_LATE)):
            b = bucket(row[key_field], row.get(label_field))
            b["responded"], b["responded_late"] = row["n"], row["late"]
        for row in open_slas.filter(state="breached").values(*fields).annotate(n=Count("pk")):
            bucket(row[key_field], row.get(label_field))["open_breached"] = row["n"]
        return list(stats.values())

    by_group = breakdown("help_request__assignment_group_id", "help_request__assignment_group__name")
    for row in by_group:
        row["name"] = row["name"] or "No group"
    by_group.sort(key=lambda r: (r["key"] is None, r["name"].lower()))
    by_priority = breakdown("help_request__priority", None)
    for row in by_priority:
        row["name"] = f"P{row['key']}"
    by_priority.sort(key=lambda r: r["key"])

    return {
        "generated_at": now,
        "days": days,
        "now": {**counts, "no_sla": open_without_sla},
        "attention": attention,
        "period": {
            "resolved": resolved_total,
            "resolution_met_percent": _rate(resolved_total - resolved_late, resolved_total),
            "responded": responded_total,
            "response_met_percent": _rate(responded_total - responded_late, responded_total),
        },
        "trend": trend,
        "by_group": _compliance(by_group),
        "by_priority": _compliance(by_priority),
    }
