from datetime import timedelta

import pytest
from django.utils import timezone

from helprequests.models import HelpRequests, SupportGroups
from slas.models import BusinessCalendar, SLAPolicy, TicketSLA

pytestmark = pytest.mark.django_db
URL = "/api/reports/sla/"
NOW = timezone.now()
H = timedelta(hours=1)


@pytest.fixture
def policy():
    calendar = BusinessCalendar.objects.create(name="24x7", timezone="UTC")
    return SLAPolicy.objects.create(name="P2 incident", ticket_type="incident", priority=2, calendar=calendar,
                                    response_minutes=60, resolution_minutes=480)


@pytest.fixture
def desk(make_user, client_for, network_team, policy):
    """A manager of the network team, and a helper that makes tickets with SLA timestamps."""
    manager = make_user("boss", "Manager")
    network_team.managers.add(manager)
    requester = make_user("req", "Requester")
    made = []

    def ticket(subject, *, status="in_progress", group=network_team, priority=2, response_due=2, resolution_due=8,
               warning_due=6, responded=None, resolved=None, sla=True, **sla_fields):
        """Times are hours from now (negative = in the past)."""
        help_request = HelpRequests.objects.create(
            requester=requester, subject=subject, description="d", assignment_group=group, status=status,
            priority=priority, first_response_time=NOW + responded * H if responded is not None else None,
            resolved_at=NOW + resolved * H if resolved is not None else None)
        if sla:
            TicketSLA.objects.create(help_request=help_request, policy=policy, response_due_at=NOW + response_due * H,
                                     resolution_due_at=NOW + resolution_due * H, warning_due_at=NOW + warning_due * H,
                                     **sla_fields)
        made.append(help_request)
        return help_request

    def get(**params):
        response = client_for(manager).get(URL, params)
        assert response.status_code == 200, response.data
        return response.data

    return ticket, get


def test_managers_and_admins_only(make_user, client_for):
    assert client_for(make_user("req", "Requester")).get(URL).status_code == 403
    assert client_for(make_user("tech", "Technician")).get(URL).status_code == 403
    assert client_for(make_user("boss", "Manager")).get(URL).status_code == 200
    assert client_for(make_user("admin", "Administrator")).get(URL).status_code == 200


def test_bad_parameters_are_refused(make_user, client_for):
    client = client_for(make_user("boss", "Manager"))
    assert client.get(URL, {"days": 12}).status_code == 400
    assert client.get(URL, {"days": "x"}).status_code == 400
    assert client.get(URL, {"group": "abc"}).status_code == 400


def test_live_states_use_due_dates_not_just_breach_flags(desk):
    ticket, get = desk
    ticket("flagged", resolution_breached=True)
    overdue = ticket("overdue, check hasn't run yet", resolution_due=-1, warning_due=-2)
    no_reply = ticket("no first response", response_due=-1, responded=None)
    replied = ticket("replied in time", response_due=-1, responded=-2)
    at_risk = ticket("past warning", warning_due=-1)
    ticket("paused, due date stale", resolution_due=-5, warning_due=-6, pause_started_at=NOW - 6 * H)
    ticket("on track")
    ticket("no policy", sla=False)
    ticket("resolved late, not open", status="resolved", resolution_due=-3, resolved=-1)

    data = get()
    assert data["now"] == {"breached": 3, "at_risk": 1, "paused": 1, "on_track": 2, "no_sla": 1}

    attention = {row["subject"]: row for row in data["attention"]}
    assert set(attention) == {"flagged", "overdue, check hasn't run yet", "no first response", "past warning"}
    assert attention[overdue.subject]["target"] == "resolution"
    assert attention[no_reply.subject]["target"] == "response"
    assert attention[no_reply.subject]["state"] == "breached"
    assert attention[at_risk.subject]["state"] == "at_risk"
    assert replied.subject not in attention
    # Breached first, then at risk.
    assert [row["state"] for row in data["attention"]] == ["breached"] * 3 + ["at_risk"]


def test_period_compliance_counts_late_finishes_without_a_flag(desk):
    ticket, get = desk
    ticket("on time", status="resolved", resolution_due=-1, resolved=-2, response_due=-5, responded=-6)
    ticket("late, unflagged", status="closed", resolution_due=-3, resolved=-2, response_due=-5, responded=-4)
    ticket("late, flagged", status="resolved", resolution_due=-1, resolved=-2, resolution_breached=True)
    ticket("long ago", status="closed", resolution_due=-24 * 40, resolved=-24 * 40 - 1)

    data = get(days=30)
    assert data["period"] == {"resolved": 3, "resolution_met_percent": 33.3,
                              "responded": 2, "response_met_percent": 50.0}
    assert len(data["trend"]) == 30
    assert sum(d["met"] for d in data["trend"]) == 1 and sum(d["breached"] for d in data["trend"]) == 2

    data = get(days=90)
    assert data["period"]["resolved"] == 4 and len(data["trend"]) == 90


def test_breakdowns_by_group_and_priority(desk, network_team):
    ticket, get = desk
    unassigned = None
    ticket("p1 met", priority=1, status="resolved", resolution_due=-1, resolved=-2)
    ticket("p2 late", status="resolved", resolution_due=-3, resolved=-2)
    ticket("p2 open breached", resolution_due=-1)
    ticket("nobody's", group=unassigned, priority=2, status="resolved", resolution_due=-1, resolved=-2)

    data = get()
    by_priority = {row["name"]: row for row in data["by_priority"]}
    assert by_priority["P1"]["resolution_met_percent"] == 100.0
    assert by_priority["P2"]["resolved"] == 1 and by_priority["P2"]["resolution_met_percent"] == 0.0  # "nobody's" is hidden
    assert by_priority["P2"]["open_breached"] == 1

    # A manager sees their own group's tickets; the unassigned one isn't visible to them.
    assert [(row["name"], row["resolved"], row["open_breached"]) for row in data["by_group"]] == [
        (network_team.name, 2, 1)]


def test_visibility_and_group_filter(desk, make_user, client_for, network_team):
    ticket, get = desk
    other = SupportGroups.objects.create(name="Desktop")
    ticket("ours", resolution_due=-1)
    ticket("theirs", group=other, resolution_due=-1)

    assert [row["subject"] for row in get()["attention"]] == ["ours"]
    assert get(group=other.pk)["attention"] == []

    admin = client_for(make_user("admin", "Administrator"))
    assert {row["subject"] for row in admin.get(URL).data["attention"]} == {"ours", "theirs"}
    assert [row["subject"] for row in admin.get(URL, {"group": other.pk}).data["attention"]] == ["theirs"]
    assert {row["name"] for row in admin.get(URL).data["by_group"]} == {network_team.name, "Desktop"}


def test_trend_buckets_by_local_day(desk):
    ticket, get = desk
    ticket("today", status="resolved", resolution_due=1, resolved=0)
    trend = get(days=7)["trend"]
    assert trend[-1]["date"] == str(timezone.localdate()) and trend[-1]["met"] == 1
