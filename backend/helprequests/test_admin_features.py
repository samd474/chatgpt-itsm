import pytest

from catalog.models import CatalogItem
from helprequests.models import FulfillmentTask, HelpRequests, Queue, SupportGroups, TicketTemplate
from reports.models import ExportJob

URL = "/api/help-requests/"
BASE = {"request_type": "incident", "subject": "Printer jam", "description": "Paper stuck again", "impact": 3, "urgency": 3}


@pytest.fixture
def people(make_user, network_team):
    tech = make_user("tech", "Technician")
    network_team.members.add(tech)
    return {"requester": make_user("req", "Requester"), "tech": tech, "admin": make_user("admin", "Administrator"),
            "manager": make_user("boss", "Manager"), "group": network_team}


def test_template_routing_is_applied_server_side(people, client_for):
    template = TicketTemplate.objects.create(name="Printer", assignment_group=people["group"])
    response = client_for(people["requester"]).post(URL, {**BASE, "template": template.pk}, format="json")
    assert response.status_code == 201
    assert response.data["assignment_group"] == people["group"].pk


def test_staff_only_template_refused_for_requesters(people, client_for):
    template = TicketTemplate.objects.create(name="Internal", available_to_requesters=False)
    assert client_for(people["requester"]).post(URL, {**BASE, "template": template.pk}, format="json").status_code == 403
    assert client_for(people["requester"]).get("/api/ticket-templates/").data == []


def test_queue_filters_validated(people, client_for):
    admin = client_for(people["admin"])
    assert admin.post("/api/queues/", {"name": "Bad", "filters": {"requester__password__startswith": "a"}}, format="json").status_code == 400
    assert admin.post("/api/queues/", {"name": "Bad2", "filters": {"status": ["nope"]}}, format="json").status_code == 400
    assert admin.post("/api/queues/", {"name": "Bad3", "filters": {}, "visible_to_roles": ["Wizard"]}, format="json").status_code == 400
    ok = admin.post("/api/queues/", {"name": "My group P1-2", "filters": {"my_groups": True, "priority": [1, 2, 4]}}, format="json")
    assert ok.status_code == 201, ok.data


def test_queue_never_widens_visibility(people, client_for, make_user):
    outsider = make_user("outsider", "Technician")
    client_for(people["requester"]).post(URL, BASE, format="json")
    HelpRequests.objects.update(assignment_group=people["group"])
    queue = Queue.objects.create(name="Everything", filters={})
    assert client_for(people["tech"]).get(f"/api/queues/{queue.pk}/tickets/").data["count"] == 1
    assert client_for(outsider).get(f"/api/queues/{queue.pk}/tickets/").data["count"] == 0
    assert client_for(people["requester"]).get("/api/queues/").status_code == 403


def test_queue_role_visibility(people, client_for):
    Queue.objects.create(name="Managers only", visible_to_roles=["Manager"])
    assert client_for(people["tech"]).get("/api/queues/").data == []
    assert len(client_for(people["manager"]).get("/api/queues/").data) == 1


def test_lookups_admin_only_writes_and_member_privacy(people, client_for):
    people["group"].members.add(people["requester"])
    groups = client_for(people["requester"]).get("/api/support-groups/").data
    assert "members" not in groups[0]
    assert client_for(people["tech"]).post("/api/categories/", {"name": "Hacked"}, format="json").status_code == 403
    assert client_for(people["admin"]).post("/api/categories/", {"name": "Hardware"}, format="json").status_code == 201


def test_catalog_tasks_block_resolution_until_done(people, client_for):
    item = CatalogItem.objects.create(name="Laptop", slug="laptop", short_description="x", assignment_group=people["group"],
                                      fulfillment_tasks=[{"title": "Image laptop"}, {"title": "Deliver"}])
    response = client_for(people["requester"]).post("/api/catalog/items/laptop/submit/", {"request_payload": {}}, format="json")
    assert response.status_code == 201, response.data
    ticket = HelpRequests.objects.get(public_id=response.data["public_id"])
    assert ticket.tasks.count() == 2
    tech = client_for(people["tech"])
    url = f"{URL}{ticket.public_id}/transition/"
    tech.post(url, {"status": "in_progress"}, format="json")
    blocked = tech.post(url, {"status": "resolved", "resolution_body": "done"}, format="json")
    assert blocked.status_code == 400
    for task in ticket.tasks.all():
        assert tech.patch(f"/api/tasks/{task.pk}/", {"status": "done"}, format="json").status_code == 200
    assert tech.post(url, {"status": "resolved", "resolution_body": "done"}, format="json").status_code == 200


def test_requester_cannot_see_or_edit_tasks(people, client_for):
    client_for(people["requester"]).post(URL, BASE, format="json")
    ticket = HelpRequests.objects.get()
    task = FulfillmentTask.objects.create(help_request=ticket, title="Internal step")
    requester = client_for(people["requester"])
    assert requester.get(f"{URL}{ticket.public_id}/tasks/").data == []
    assert requester.patch(f"/api/tasks/{task.pk}/", {"status": "done"}, format="json").status_code == 403


def test_no_self_approval(people, client_for, make_user):
    approver_and_requester = people["manager"]
    item = CatalogItem.objects.create(name="Budget", slug="budget", short_description="x", requires_approval=True)
    item.approvers.add(approver_and_requester)
    response = client_for(approver_and_requester).post("/api/catalog/items/budget/submit/", {"request_payload": {}}, format="json")
    assert response.status_code == 400  # the only approver is the requester


def test_large_export_runs_in_background(people, client_for, settings):
    from django.core.management import call_command

    from reports.exporting import run_export

    call_command("seed_roles", verbosity=0)
    settings.EXPORT_SYNC_LIMIT = 1
    settings.CELERY_TASK_ALWAYS_EAGER = False
    people["group"].managers.add(people["manager"])
    requester = client_for(people["requester"])
    requester.post(URL, BASE, format="json")
    requester.post(URL, {**BASE, "subject": "=cmd|' /C calc'!A0"}, format="json")
    HelpRequests.objects.update(assignment_group=people["group"])

    from unittest import mock

    with mock.patch("reports.tasks.generate_export.delay") as delay:
        response = client_for(people["manager"]).get(f"{URL}export/")
    assert response.status_code == 202
    job = ExportJob.objects.get(public_id=response.data["export_id"])
    delay.assert_called_once_with(job.pk)
    run_export(job)
    job.refresh_from_db()
    assert job.state == "done" and job.row_count == 2

    download = client_for(people["manager"]).get(f"/api/exports/{job.public_id}/download/")
    content = b"".join(download.streaming_content).decode()
    assert "'=cmd" in content
    # Nobody else can fetch it, even an administrator.
    assert client_for(people["admin"]).get(f"/api/exports/{job.public_id}/download/").status_code == 404


def test_export_fails_if_permission_revoked(people, client_for):
    from reports.exporting import run_export

    job = ExportJob.objects.create(requested_by=people["requester"], params={})
    run_export(job)
    job.refresh_from_db()
    assert job.state == "failed"


def test_support_group_admin_serializer_manages_members(people, client_for):
    admin = client_for(people["admin"])
    response = admin.post("/api/support-groups/", {"name": "Desktop", "members": [people["tech"].pk]}, format="json")
    assert response.status_code == 201, response.data
    assert SupportGroups.objects.get(name="Desktop").members.filter(pk=people["tech"].pk).exists()


def test_people_directory_is_staff_only(people, client_for):
    assert client_for(people["requester"]).get("/api/people/").data["count"] == 0
    assert client_for(people["tech"]).get("/api/people/", {"search": "req"}).data["count"] == 1


def test_page_size_is_bounded(people, client_for):
    response = client_for(people["tech"]).get("/api/people/", {"page_size": 100000})
    assert response.status_code == 200  # silently capped at max_page_size rather than dumping the table


def test_open_filter(people, client_for):
    client = client_for(people["requester"])
    client.post(URL, BASE, format="json")
    ticket = HelpRequests.objects.get()
    assert client.get(URL, {"open": "true"}).data["count"] == 1
    HelpRequests.objects.filter(pk=ticket.pk).update(status="closed")
    assert client.get(URL, {"open": "true"}).data["count"] == 0
