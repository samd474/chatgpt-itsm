import pytest
from django.core.management import call_command

from alerts.models import NotificationDelivery, NotificationEvent
from helprequests.models import Category, HelpRequests, HelpRequestsComment, SupportGroups
from helprequests.priority import calculate_priority
from reports.models import AuditEvent
from rules.models import TicketRule

URL = "/api/rules/ticket-rules/"
pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(make_user, network_team):
    member = make_user("netops", "Technician")
    network_team.members.add(member)
    return {"admin": make_user("root", "Administrator"), "auditor": make_user("aud", "Auditor"),
            "tech": make_user("tech", "Technician"), "manager": make_user("boss", "Manager"),
            "requester": make_user("req", "Requester"), "network": network_team, "member": member,
            "desk": SupportGroups.objects.create(name="Service desk")}


def raise_ticket(client_for, requester, **data):
    payload = {"request_type": "incident", "subject": "VPN keeps dropping", "description": "Error 809 since this morning.",
               "impact": 3, "urgency": 3, **data}
    response = client_for(requester).post("/api/help-requests/", payload, format="json")
    assert response.status_code == 201, response.data
    return HelpRequests.objects.get(public_id=response.data["public_id"])


def rule(name="VPN to network", position=0, conditions=None, actions=None, **extra):
    return TicketRule.objects.create(name=name, position=position, conditions=conditions or {}, actions=actions or {}, **extra)


class TestApi:
    def test_only_administrators_write_and_auditors_read(self, setup, client_for):
        body = {"name": "VPN", "conditions": {"keywords": ["vpn"]}, "actions": {"set_assignment_group": setup["network"].pk}}
        for who in ("tech", "manager", "requester", "auditor"):
            assert client_for(setup[who]).post(URL, body, format="json").status_code == 403, who
        created = client_for(setup["admin"]).post(URL, body, format="json")
        assert created.status_code == 201, created.data
        assert len(client_for(setup["auditor"]).get(URL).data) == 1
        assert client_for(setup["tech"]).get(URL).status_code == 403
        assert AuditEvent.objects.filter(activity_type="config.ticket_rule.created").exists()

    @pytest.mark.parametrize("field,value", [
        ("conditions", {"subject__regex": ".*"}),
        ("conditions", {"category": [999]}),
        ("conditions", {"impact": [4]}),
        ("conditions", {"keywords": []}),
        ("conditions", {"keywords": ["x" * 101]}),
        ("actions", {}),
        ("actions", {"set_assignment_group": 999}),
        ("actions", {"set_urgency": 0}),
        ("actions", {"run_python": "print(1)"}),
        ("actions", {"add_note": ""}),
    ])
    def test_conditions_and_actions_are_validated(self, setup, client_for, field, value):
        body = {"name": "x", "conditions": {}, "actions": {"set_impact": 1}, field: value}
        response = client_for(setup["admin"]).post(URL, body, format="json")
        assert response.status_code == 400 and field in response.data


class TestEngine:
    def test_matching_rule_routes_and_reprioritises_before_sla_and_notification(self, setup, client_for):
        call_command("seed_slas", verbosity=0)
        rule(conditions={"keywords": ["error 809"]},
             actions={"set_assignment_group": setup["network"].pk, "set_impact": 1, "set_urgency": 1})
        ticket = raise_ticket(client_for, setup["requester"])
        assert ticket.assignment_group == setup["network"]
        assert (ticket.impact, ticket.urgency, ticket.priority) == (1, 1, 1)
        assert ticket.sla.policy.priority == 1  # the SLA follows the rule's priority, not the original one
        assigned = NotificationEvent.objects.get(event_type="ticket.assigned")
        assert set(NotificationDelivery.objects.filter(event=assigned).values_list("recipient", flat=True)) == {setup["member"].email}
        audit = AuditEvent.objects.get(activity_type="rule.applied")
        assert audit.metadata["applied"]["set_assignment_group"] == setup["network"].pk

    def test_non_matching_tickets_are_untouched(self, setup, client_for):
        rule(conditions={"keywords": ["printer"], "request_type": "incident"}, actions={"set_impact": 1})
        ticket = raise_ticket(client_for, setup["requester"])
        assert (ticket.impact, ticket.urgency, ticket.priority) == (3, 3, calculate_priority(3, 3))
        assert not AuditEvent.objects.filter(activity_type="rule.applied").exists()

    def test_rules_run_in_order_and_later_rules_win(self, setup, client_for):
        rule("first", 1, actions={"set_assignment_group": setup["desk"].pk})
        rule("second", 2, actions={"set_assignment_group": setup["network"].pk})
        assert raise_ticket(client_for, setup["requester"]).assignment_group == setup["network"]

    def test_stop_processing_skips_later_rules(self, setup, client_for):
        rule("first", 1, actions={"set_assignment_group": setup["desk"].pk}, stop_processing=True)
        rule("second", 2, actions={"set_assignment_group": setup["network"].pk})
        assert raise_ticket(client_for, setup["requester"]).assignment_group == setup["desk"]

    def test_later_rules_see_earlier_changes(self, setup, client_for):
        vpn = Category.objects.create(name="VPN")
        rule("categorise", 1, conditions={"keywords": ["vpn"]}, actions={"set_category": vpn.pk})
        rule("route", 2, conditions={"category": [vpn.pk]}, actions={"set_assignment_group": setup["network"].pk})
        ticket = raise_ticket(client_for, setup["requester"])
        assert (ticket.category, ticket.assignment_group) == (vpn, setup["network"])

    def test_inactive_rules_and_inactive_targets_are_skipped(self, setup, client_for):
        rule("off", 1, actions={"set_impact": 1}, active=False)
        retired = SupportGroups.objects.create(name="Retired team", active=False)
        rule("stale", 2, actions={"set_assignment_group": retired.pk, "set_urgency": 1})
        ticket = raise_ticket(client_for, setup["requester"])
        assert ticket.impact == 3 and ticket.assignment_group is None and ticket.urgency == 1
        audit = AuditEvent.objects.get(activity_type="rule.applied")
        assert "set_assignment_group" in audit.metadata["skipped"]

    def test_notes_are_private_and_unauthored(self, setup, client_for):
        rule(actions={"add_note": "Check the VPN status page first.", "set_assignment_group": setup["network"].pk})
        ticket = raise_ticket(client_for, setup["requester"])
        note = HelpRequestsComment.objects.get(help_request=ticket)
        assert note.author is None and note.visibility == HelpRequestsComment.Visibility.PRIVATE
        comments_url = f"/api/help-requests/{ticket.public_id}/comments/"
        assert client_for(setup["requester"]).get(comments_url).data == []
        staff_view = client_for(setup["member"]).get(comments_url).data
        assert [(c["body"], c["author_name"]) for c in staff_view] == [("Check the VPN status page first.", None)]

    def test_notify_group_emails_its_active_members(self, setup, client_for):
        rule(actions={"notify_group": setup["network"].pk})
        raise_ticket(client_for, setup["requester"])
        event = NotificationEvent.objects.get(event_type="ticket.rule_matched")
        assert event.payload["rule"] == "VPN to network"
        assert set(NotificationDelivery.objects.filter(event=event).values_list("recipient", flat=True)) == {setup["member"].email}


class TestUpdateRules:
    def ticket_in_network(self, client_for, setup, **data):
        ticket = raise_ticket(client_for, setup["requester"], **data)
        HelpRequests.objects.filter(pk=ticket.pk).update(assignment_group=setup["network"])
        return HelpRequests.objects.get(pk=ticket.pk)

    def patch(self, client, ticket, **changes):
        response = client.patch(f"/api/help-requests/{ticket.public_id}/", changes, format="json")
        assert response.status_code == 200, response.data
        return HelpRequests.objects.get(pk=ticket.pk)

    def applied(self, event="updated"):
        return [e.metadata["rule"] for e in AuditEvent.objects.filter(activity_type="rule.applied").order_by("pk")
                if e.metadata.get("event") == event]

    @pytest.mark.parametrize("body,field", [
        ({"runs_on": "updated", "conditions": {}}, "conditions"),  # would fire on every edit
        ({"runs_on": "created", "conditions": {"changed": ["status"]}}, "conditions"),
        ({"runs_on": "updated", "conditions": {"changed": ["subject"]}}, "conditions"),
        ({"runs_on": "both", "conditions": {"status": ["done"]}}, "conditions"),
    ])
    def test_update_rules_are_validated(self, setup, client_for, body, field):
        response = client_for(setup["admin"]).post(URL, {"name": "x", "actions": {"set_impact": 1}, **body}, format="json")
        assert response.status_code == 400 and field in response.data

    def test_status_change_triggers_a_rule(self, setup, client_for):
        rule("resolved -> notify", runs_on="updated", conditions={"changed": ["status"], "status": ["resolved"]},
             actions={"notify_group": setup["network"].pk})
        ticket = self.ticket_in_network(client_for, setup)
        member = client_for(setup["member"])
        member.post(f"/api/help-requests/{ticket.public_id}/transition/", {"status": "in_progress"}, format="json")
        assert not NotificationEvent.objects.filter(event_type="ticket.rule_matched").exists()  # status isn't resolved yet
        response = member.post(f"/api/help-requests/{ticket.public_id}/transition/",
                               {"status": "resolved", "resolution_body": "Replaced the cable."}, format="json")
        assert response.status_code == 200, response.data
        assert NotificationEvent.objects.filter(event_type="ticket.rule_matched").count() == 1

    def test_edits_to_unwatched_fields_do_not_trigger(self, setup, client_for):
        rule(runs_on="updated", conditions={"changed": ["category"]}, actions={"set_impact": 1})
        ticket = self.ticket_in_network(client_for, setup)
        assert self.patch(client_for(setup["member"]), ticket, subject="New subject").impact == 3
        assert self.applied() == []

    def test_category_change_reroutes_reprioritises_and_notifies(self, setup, client_for):
        call_command("seed_slas", verbosity=0)
        vpn = Category.objects.create(name="VPN")
        rule("vpn -> network", runs_on="updated", conditions={"changed": ["category"], "category": [vpn.pk]},
             actions={"set_assignment_group": setup["network"].pk, "set_impact": 1, "set_urgency": 1})
        ticket = raise_ticket(client_for, setup["requester"])
        ticket = self.patch(client_for(setup["admin"]), ticket, category=vpn.pk)
        assert (ticket.assignment_group, ticket.priority) == (setup["network"], 1)
        assert ticket.sla.policy.priority == 1
        assigned = NotificationEvent.objects.filter(event_type="ticket.assigned").last()
        assert set(NotificationDelivery.objects.filter(event=assigned).values_list("recipient", flat=True)) == {setup["member"].email}

    def test_rules_only_run_for_their_event(self, setup, client_for):
        rule("on create", 1, runs_on="created", actions={"set_impact": 1})
        rule("on update", 2, runs_on="updated", conditions={"changed": ["urgency"]}, actions={"set_impact": 2})
        ticket = raise_ticket(client_for, setup["requester"])
        assert ticket.impact == 1 and self.applied("created") == ["on create"]
        HelpRequests.objects.filter(pk=ticket.pk).update(assignment_group=setup["network"])  # so the member works it
        ticket = self.patch(client_for(setup["member"]), ticket, urgency=2)
        assert ticket.impact == 2 and self.applied("updated") == ["on update"]

    def test_a_rules_own_changes_do_not_trigger_more_rules(self, setup, client_for):
        vpn = Category.objects.create(name="VPN")
        rule("route sets category", 1, runs_on="updated", conditions={"changed": ["assignment_group"]},
             actions={"set_category": vpn.pk})
        rule("category watcher", 2, runs_on="updated", conditions={"changed": ["category"]}, actions={"set_impact": 1})
        ticket = raise_ticket(client_for, setup["requester"])
        ticket = self.patch(client_for(setup["admin"]), ticket, assignment_group=setup["network"].pk)
        assert ticket.category == vpn and ticket.impact == 3
        assert self.applied() == ["route sets category"]


class TestPreview:
    URL = f"{URL}preview/"

    def test_shows_matches_and_changes_without_changing_anything(self, setup, client_for):
        for subject in ("VPN down", "VPN slow", "Printer jam"):
            raise_ticket(client_for, setup["requester"], subject=subject, description="Please help.")
        # A live rule that would change every ticket: previewing must not run it either.
        rule("live", actions={"set_urgency": 1})
        body = {"conditions": {"keywords": ["vpn"]}, "actions": {"set_assignment_group": setup["network"].pk, "set_impact": 3}}
        result = client_for(setup["admin"]).post(self.URL, body, format="json").data
        assert (result["scanned"], result["matched"]) == (3, 2)
        assert {t["subject"] for t in result["tickets"]} == {"VPN down", "VPN slow"}
        # Impact is already 3, so only the routing would change.
        assert result["tickets"][0]["changes"] == [{"field": "assignment_group", "from": None, "to": "Network"}]
        assert not HelpRequests.objects.filter(assignment_group__isnull=False).exists()
        assert not HelpRequests.objects.filter(urgency=1).exists()
        assert not AuditEvent.objects.filter(activity_type="rule.applied").exists()

    def test_changed_conditions_are_ignored_and_reported(self, setup, client_for):
        raise_ticket(client_for, setup["requester"])
        body = {"conditions": {"changed": ["status"]}, "actions": {"set_impact": 1}}
        result = client_for(setup["admin"]).post(self.URL, body, format="json").data
        assert result["matched"] == 1 and result["ignored_conditions"] == ["changed"]

    def test_validated_and_administrators_only(self, setup, client_for):
        body = {"conditions": {"keywords": ["vpn"]}}
        assert client_for(setup["admin"]).post(self.URL, {"conditions": {"bogus": 1}}, format="json").status_code == 400
        for who in ("tech", "auditor"):
            assert client_for(setup[who]).post(self.URL, body, format="json").status_code == 403
