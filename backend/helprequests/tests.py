import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from helprequests.models import HelpRequests, HelpRequestsComment
from helprequests.priority import calculate_priority
from reports.models import AuditEvent

URL = "/api/help-requests/"


def create(client, **data):
    payload = {"request_type": "incident", "subject": "VPN drops", "description": "It disconnects every few minutes.",
               "impact": 2, "urgency": 1, **data}
    return client.post(URL, payload, format="json")


@pytest.fixture
def people(make_user, network_team):
    requester = make_user("req", "Requester")
    other = make_user("other", "Requester")
    tech = make_user("tech", "Technician")
    outsider = make_user("outsider", "Technician")
    auditor = make_user("auditor", "Auditor")
    manager = make_user("manager", "Manager")
    network_team.members.add(tech)
    return {"requester": requester, "other": other, "tech": tech, "outsider": outsider,
            "auditor": auditor, "manager": manager, "group": network_team}


def test_priority_matrix():
    assert calculate_priority(1, 1) == 1
    assert calculate_priority(2, 2) == 2
    assert calculate_priority(3, 3) == 4
    assert calculate_priority(1, 3) == 2


def test_requester_creates_incident_with_number_priority_and_audit(people, client_for):
    response = create(client_for(people["requester"]), priority=1)
    assert response.status_code == 201, response.data
    ticket = HelpRequests.objects.get(public_id=response.data["public_id"])
    assert ticket.requester == people["requester"]
    assert ticket.priority == 1  # calculated server-side; submitted priority ignored
    assert ticket.request_number == f"INC-{ticket.pk:06d}"
    assert AuditEvent.objects.filter(activity_type="ticket.created", object_id=str(ticket.public_id)).exists()


def test_requester_cannot_read_another_requesters_ticket(people, client_for):
    public_id = create(client_for(people["requester"])).data["public_id"]
    response = client_for(people["other"]).get(f"{URL}{public_id}/")
    assert response.status_code == 404
    assert client_for(people["other"]).get(URL).data["count"] == 0


def test_technician_scope_follows_assignment_group(people, client_for):
    public_id = create(client_for(people["requester"])).data["public_id"]
    HelpRequests.objects.filter(public_id=public_id).update(assignment_group=people["group"])
    assert client_for(people["tech"]).get(f"{URL}{public_id}/").status_code == 200
    assert client_for(people["outsider"]).get(f"{URL}{public_id}/").status_code == 404


def test_technician_assignment_moves_ticket_to_assigned(people, client_for):
    public_id = create(client_for(people["requester"])).data["public_id"]
    HelpRequests.objects.filter(public_id=public_id).update(assignment_group=people["group"])
    response = client_for(people["tech"]).patch(f"{URL}{public_id}/", {"technician": people["tech"].pk}, format="json")
    assert response.status_code == 200, response.data
    assert response.data["status"] == "assigned"
    assert response.data["technician"] == people["tech"].pk


def test_cannot_assign_a_requester_as_technician(people, client_for):
    public_id = create(client_for(people["requester"])).data["public_id"]
    HelpRequests.objects.filter(public_id=public_id).update(assignment_group=people["group"])
    response = client_for(people["tech"]).patch(f"{URL}{public_id}/", {"technician": people["other"].pk}, format="json")
    assert response.status_code == 400


def test_requester_never_receives_private_notes(people, client_for):
    public_id = create(client_for(people["requester"])).data["public_id"]
    HelpRequests.objects.filter(public_id=public_id).update(assignment_group=people["group"])
    tech = client_for(people["tech"])
    assert tech.post(f"{URL}{public_id}/comments/", {"body": "internal: router reboot", "visibility": "private"}, format="json").status_code == 201
    assert tech.post(f"{URL}{public_id}/comments/", {"body": "Looking into it", "visibility": "public"}, format="json").status_code == 201

    requester_view = client_for(people["requester"]).get(f"{URL}{public_id}/comments/").data
    assert [c["body"] for c in requester_view] == ["Looking into it"]
    assert len(tech.get(f"{URL}{public_id}/comments/").data) == 2


def test_requester_cannot_post_private_note(people, client_for):
    public_id = create(client_for(people["requester"])).data["public_id"]
    response = client_for(people["requester"]).post(f"{URL}{public_id}/comments/", {"body": "x", "visibility": "private"}, format="json")
    assert response.status_code == 403
    assert not HelpRequestsComment.objects.exists()


def test_first_public_staff_reply_records_first_response(people, client_for):
    public_id = create(client_for(people["requester"])).data["public_id"]
    HelpRequests.objects.filter(public_id=public_id).update(assignment_group=people["group"])
    client_for(people["tech"]).post(f"{URL}{public_id}/comments/", {"body": "On it", "visibility": "public"}, format="json")
    assert HelpRequests.objects.get(public_id=public_id).first_response_time is not None


def test_lifecycle_transitions(people, client_for):
    public_id = create(client_for(people["requester"])).data["public_id"]
    HelpRequests.objects.filter(public_id=public_id).update(assignment_group=people["group"], technician=people["tech"])
    tech = client_for(people["tech"])
    url = f"{URL}{public_id}/transition/"

    assert tech.post(url, {"status": "closed"}, format="json").status_code == 400  # new -> closed not allowed
    assert tech.post(url, {"status": "in_progress"}, format="json").status_code == 200
    assert tech.post(url, {"status": "resolved"}, format="json").status_code == 400  # needs resolution text
    response = tech.post(url, {"status": "resolved", "resolution_code": "fixed", "resolution_body": "Replaced cable"}, format="json")
    assert response.status_code == 200
    assert response.data["resolved_at"] is not None

    # The requester may reopen or confirm closure, but not resolve.
    requester = client_for(people["requester"])
    assert requester.post(url, {"status": "closed"}, format="json").status_code == 200


def test_requester_cannot_resolve_own_ticket(people, client_for):
    public_id = create(client_for(people["requester"])).data["public_id"]
    response = client_for(people["requester"]).post(f"{URL}{public_id}/transition/", {"status": "in_progress"}, format="json")
    assert response.status_code == 403


def test_auditor_is_read_only(people, client_for):
    public_id = create(client_for(people["requester"])).data["public_id"]
    auditor = client_for(people["auditor"])
    assert auditor.get(f"{URL}{public_id}/").status_code == 200
    assert create(auditor).status_code == 403
    assert auditor.post(f"{URL}{public_id}/comments/", {"body": "x"}, format="json").status_code == 403


def test_no_delete_endpoint(people, client_for):
    public_id = create(client_for(people["requester"])).data["public_id"]
    assert client_for(people["manager"]).delete(f"{URL}{public_id}/").status_code == 405


def test_export_requires_permission_and_escapes_formulas(people, client_for):
    from django.core.management import call_command

    call_command("seed_roles", verbosity=0)
    create(client_for(people["requester"]), subject="=HYPERLINK(\"http://evil\")")
    assert client_for(people["requester"]).get(f"{URL}export/").status_code == 403
    # Managers only export tickets in their scope; give the manager the group.
    people["group"].managers.add(people["manager"])
    HelpRequests.objects.update(assignment_group=people["group"])
    response = client_for(people["manager"]).get(f"{URL}export/")
    assert response.status_code == 200
    assert "'=HYPERLINK" in response.content.decode()
    assert AuditEvent.objects.filter(activity_type="export.help_requests").exists()


def test_attachment_rules_and_authorized_download(people, client_for):
    public_id = create(client_for(people["requester"])).data["public_id"]
    requester = client_for(people["requester"])
    url = f"{URL}{public_id}/attachments/"

    blocked = SimpleUploadedFile("run.exe", b"MZ....", content_type="application/octet-stream")
    assert requester.post(url, {"file": blocked}, format="multipart").status_code == 400

    ok = SimpleUploadedFile("log.txt", b"error 42", content_type="text/plain")
    response = requester.post(url, {"file": ok}, format="multipart")
    assert response.status_code == 201, response.data
    attachment_id = response.data["id"]
    assert len(response.data["sha256"]) == 64

    download = f"{url}{attachment_id}/download/"
    assert requester.get(download).status_code == 200
    assert client_for(people["other"]).get(download).status_code == 404


def test_ticket_list_query_count_does_not_grow_with_rows(people, client_for):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    from accounts.models import User

    def list_queries():
        # A fresh instance per call, as a real request would load.
        client = client_for(User.objects.get(pk=people["tech"].pk))
        with CaptureQueriesContext(connection) as ctx:
            assert client.get(URL).status_code == 200
        return len(ctx)

    HelpRequests.objects.create(requester=people["requester"], subject="s", description="d", assignment_group=people["group"])
    baseline = list_queries()
    for n in range(5):
        HelpRequests.objects.create(requester=people["requester"], subject=f"s{n}", description="d",
                                    assignment_group=people["group"])
    assert list_queries() == baseline
