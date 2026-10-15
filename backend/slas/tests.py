from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from slas.business_time import Schedule, add_business_minutes, business_minutes_between

NY = ZoneInfo("America/New_York")
WEEKDAYS_9_TO_5 = {d: [(time(9), time(17))] for d in range(5)}


def ny(*args):
    return datetime(*args, tzinfo=NY)


@pytest.fixture
def office():
    return Schedule(tz=NY, windows=WEEKDAYS_9_TO_5)


def test_start_during_business_hours(office):
    assert add_business_minutes(office, ny(2026, 10, 14, 10, 0), 60) == ny(2026, 10, 14, 11, 0)


def test_start_before_window(office):
    assert add_business_minutes(office, ny(2026, 10, 14, 7, 0), 30) == ny(2026, 10, 14, 9, 30)


def test_start_after_window_rolls_to_next_day(office):
    assert add_business_minutes(office, ny(2026, 10, 14, 18, 0), 30) == ny(2026, 10, 15, 9, 30)


def test_lunch_gap():
    schedule = Schedule(tz=NY, windows={d: [(time(9), time(12)), (time(13), time(17))] for d in range(5)})
    assert add_business_minutes(schedule, ny(2026, 10, 14, 11, 30), 60) == ny(2026, 10, 14, 13, 30)


def test_friday_into_monday(office):
    # 2026-10-16 is a Friday.
    assert add_business_minutes(office, ny(2026, 10, 16, 16, 0), 120) == ny(2026, 10, 19, 10, 0)


def test_holiday_is_skipped():
    schedule = Schedule(tz=NY, windows=WEEKDAYS_9_TO_5, holidays={date(2026, 10, 15)})
    assert add_business_minutes(schedule, ny(2026, 10, 14, 16, 0), 120) == ny(2026, 10, 16, 10, 0)


def test_daylight_saving_transition_24x7():
    # US DST ends 2026-11-01 at 02:00; that local day is 25 hours long.
    schedule = Schedule(tz=NY)
    start = ny(2026, 10, 31, 12, 0)
    assert add_business_minutes(schedule, start, 24 * 60) == start.astimezone(timezone.utc) + timedelta(hours=24)


def test_daylight_saving_business_window(office):
    # Business windows stay at 09:00 local time either side of the change.
    result = add_business_minutes(office, ny(2026, 10, 30, 16, 0), 120)
    assert result.astimezone(NY) == ny(2026, 11, 2, 10, 0)


def test_24x7_calendar():
    assert add_business_minutes(Schedule(tz=NY), ny(2026, 10, 17, 23, 0), 120) == ny(2026, 10, 18, 1, 0)


def test_zero_minutes_returns_start(office):
    start = ny(2026, 10, 17, 3, 0)
    assert add_business_minutes(office, start, 0) == start


def test_very_long_target(office):
    # 40 business hours = five full weekdays.
    assert add_business_minutes(office, ny(2026, 10, 12, 9, 0), 40 * 60) == ny(2026, 10, 16, 17, 0)


def test_business_minutes_between(office):
    assert business_minutes_between(office, ny(2026, 10, 16, 16, 0), ny(2026, 10, 19, 10, 0)) == 120
    assert business_minutes_between(office, ny(2026, 10, 17, 9, 0), ny(2026, 10, 17, 17, 0)) == 0


@pytest.mark.django_db
class TestSLALifecycle:
    @pytest.fixture
    def ticket(self, make_user, client_for):
        from django.core.management import call_command

        call_command("seed_slas", verbosity=0)
        requester = make_user("req", "Requester")
        response = client_for(requester).post("/api/help-requests/", {
            "request_type": "incident", "subject": "Down", "description": "Everything is down", "impact": 1, "urgency": 1,
        }, format="json")
        from helprequests.models import HelpRequests
        return HelpRequests.objects.get(public_id=response.data["public_id"])

    def test_sla_attached_from_priority(self, ticket):
        assert ticket.sla.policy.priority == 1
        assert ticket.sla.resolution_due_at > ticket.created_at

    def test_pause_resume_is_not_double_counted(self, ticket, make_user):
        from django.utils import timezone as dj_tz

        from helprequests.models import HelpRequests
        from slas import services
        from slas.models import TicketSLA

        tech = make_user("tech", "Technician")
        Status = HelpRequests.RequestStatus
        due_before = ticket.sla.resolution_due_at
        services.on_status_change(ticket, Status.IN_PROGRESS, Status.PENDING_USER_RESPONSE, actor=tech)
        TicketSLA.objects.filter(pk=ticket.sla.pk).update(pause_started_at=dj_tz.now() - timedelta(minutes=30))
        services.on_status_change(ticket, Status.PENDING_USER_RESPONSE, Status.IN_PROGRESS, actor=tech)
        services.on_status_change(ticket, Status.PENDING_USER_RESPONSE, Status.IN_PROGRESS, actor=tech)  # repeated request
        sla = TicketSLA.objects.get(pk=ticket.sla.pk)
        assert sla.pause_started_at is None
        assert sla.paused_business_minutes == 30
        assert sla.resolution_due_at == due_before + timedelta(minutes=30)  # P1 incidents use the 24x7 calendar

    def test_breach_check_is_idempotent(self, ticket):
        from django.utils import timezone as dj_tz

        from alerts.models import NotificationEvent
        from reports.models import AuditEvent
        from slas.models import TicketSLA
        from slas.tasks import check_sla_thresholds

        TicketSLA.objects.filter(pk=ticket.sla.pk).update(
            response_due_at=dj_tz.now() - timedelta(minutes=1),
            resolution_due_at=dj_tz.now() - timedelta(minutes=1),
        )
        check_sla_thresholds()
        check_sla_thresholds()
        assert AuditEvent.objects.filter(activity_type="sla.breached").count() == 2  # response + resolution, once each
        assert NotificationEvent.objects.filter(event_type="sla.breached").count() == 2
