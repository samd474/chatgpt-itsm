"""Who can see which tickets, private notes and their attachments, endpoint by endpoint.

One fixed world, every role checked against the same expectations, so a scope bug in any
endpoint shows up as a mismatch against `access.visible_HelpRequests` and `can_read_private_notes`.
"""
import csv
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from helprequests import services
from helprequests.models import FulfillmentTask, HelpRequests, HelpRequestsComment, Queue

URL = "/api/help-requests/"
PUBLIC_NOTE, PRIVATE_NOTE = "Public update", "Private: admin password is on the sticky note"
PUBLIC_FILE, PRIVATE_FILE = "screenshot.txt", "internal-dump.txt"

# Which tickets each person can see, and on which of those they also see private notes.
VISIBLE = {
    "requester": {"T1"},
    "other_requester": {"T2"},
    "member": {"T1", "T3"},
    "group_manager": {"T1", "T3"},
    "assigned_tech": {"T2"},
    "outsider": set(),
    "staff_requester": {"T3"},
    "auditor": {"T1", "T2", "T3"},
    "admin": {"T1", "T2", "T3"},
    "superuser": {"T1", "T2", "T3"},
}
PRIVATE = {
    "requester": set(),
    "other_requester": set(),
    "member": {"T1", "T3"},
    "group_manager": {"T1", "T3"},
    "assigned_tech": {"T2"},
    "outsider": set(),
    # Staff who raised a ticket themselves are its requester, not its worker.
    "staff_requester": set(),
    "auditor": {"T1", "T2", "T3"},
    "admin": {"T1", "T2", "T3"},
    "superuser": {"T1", "T2", "T3"},
}
PEOPLE = sorted(VISIBLE)
TICKETS = ("T1", "T2", "T3")


@pytest.fixture
def world(make_user, network_team):
    people = {
        "requester": make_user("requester", "Requester"),
        "other_requester": make_user("other_requester", "Requester"),
        "member": make_user("member", "Technician"),
        "group_manager": make_user("group_manager", "Manager"),
        "assigned_tech": make_user("assigned_tech", "Technician"),
        "outsider": make_user("outsider", "Technician"),
        "staff_requester": make_user("staff_requester", "Technician"),
        "auditor": make_user("auditor", "Auditor"),
        "admin": make_user("admin", "Administrator"),
        "superuser": make_user("superuser", is_superuser=True),
    }
    network_team.members.add(people["member"])
    network_team.managers.add(people["group_manager"])

    def ticket(subject, requester, **extra):
        return HelpRequests.objects.create(requester=requester, subject=subject, description="d", **extra)

    tickets = {
        # Routed to the group.
        "T1": ticket("T1", people["requester"], assignment_group=network_team),
        # Assigned straight to a technician outside any group.
        "T2": ticket("T2", people["other_requester"], technician=people["assigned_tech"]),
        # Raised by a technician, routed to the group.
        "T3": ticket("T3", people["staff_requester"], assignment_group=network_team),
    }
    tasks = {}
    for name, t in tickets.items():
        worker = people["assigned_tech"] if name == "T2" else people["member"]
        HelpRequestsComment.objects.create(help_request=t, author=worker, body=PUBLIC_NOTE)
        private = HelpRequestsComment.objects.create(help_request=t, author=worker, body=PRIVATE_NOTE,
                                                     visibility=HelpRequestsComment.Visibility.PRIVATE)
        services.add_attachment(t, uploaded_by=t.requester,
                                uploaded_file=SimpleUploadedFile(PUBLIC_FILE, b"public", content_type="text/plain"))
        services.add_attachment(t, uploaded_by=worker, comment=private,
                                uploaded_file=SimpleUploadedFile(PRIVATE_FILE, b"secret", content_type="text/plain"))
        tasks[name] = FulfillmentTask.objects.create(help_request=t, title=f"{name} internal step")
    return {"people": people, "tickets": tickets, "tasks": tasks, "group": network_team}


@pytest.fixture
def as_(world, client_for):
    return lambda who: client_for(world["people"][who])


def _detail(world, name):
    return f"{URL}{world['tickets'][name].public_id}/"


@pytest.mark.parametrize("who", PEOPLE)
def test_list_and_detail(world, as_, who):
    client = as_(who)
    listed = {row["subject"] for row in client.get(URL).data["results"]}
    assert listed == VISIBLE[who]
    for name in TICKETS:
        assert client.get(_detail(world, name)).status_code == (200 if name in VISIBLE[who] else 404), name


@pytest.mark.parametrize("who", PEOPLE)
def test_comments(world, as_, who):
    client = as_(who)
    for name in TICKETS:
        response = client.get(f"{_detail(world, name)}comments/")
        if name not in VISIBLE[who]:
            assert response.status_code == 404, name
            continue
        bodies = {c["body"] for c in response.data}
        assert bodies == ({PUBLIC_NOTE, PRIVATE_NOTE} if name in PRIVATE[who] else {PUBLIC_NOTE}), name


@pytest.mark.parametrize("who", PEOPLE)
def test_attachments_and_downloads(world, as_, who):
    client = as_(who)
    for name in TICKETS:
        ticket = world["tickets"][name]
        url = f"{_detail(world, name)}attachments/"
        response = client.get(url)
        if name not in VISIBLE[who]:
            assert response.status_code == 404, name
        else:
            names = {a["original_name"] for a in response.data}
            assert names == ({PUBLIC_FILE, PRIVATE_FILE} if name in PRIVATE[who] else {PUBLIC_FILE}), name
        for attachment in ticket.attachments.all():
            allowed = name in VISIBLE[who] and (attachment.comment_id is None or name in PRIVATE[who])
            status = client.get(f"{url}{attachment.pk}/download/").status_code
            assert status == (200 if allowed else 404), (name, attachment.original_name)


@pytest.mark.parametrize("who", PEOPLE)
def test_fulfilment_tasks(world, as_, who):
    client = as_(who)
    for name in TICKETS:
        listed = client.get(f"{_detail(world, name)}tasks/")
        detail = client.get(f"/api/tasks/{world['tasks'][name].pk}/")
        if name not in VISIBLE[who]:
            assert listed.status_code == 404, name
            assert detail.status_code == 404, name
            continue
        # Requesters see no tasks, even on their own ticket; auditors see them read-only.
        expects_tasks = name in PRIVATE[who]
        assert bool(listed.data) == expects_tasks, name


@pytest.mark.parametrize("who", ["requester", "other_requester", "outsider", "staff_requester", "assigned_tech"])
def test_writes_to_invisible_tickets_are_not_found(world, as_, who):
    """An unrelated user learns nothing: every write on a ticket they can't see is a 404, never a 403."""
    client = as_(who)
    for name in set(TICKETS) - VISIBLE[who]:
        base = _detail(world, name)
        assert client.patch(base, {"subject": "x"}, format="json").status_code == 404
        assert client.post(f"{base}comments/", {"body": "x"}, format="json").status_code == 404
        assert client.post(f"{base}transition/", {"status": "cancelled"}, format="json").status_code == 404
        upload = SimpleUploadedFile("x.txt", b"x", content_type="text/plain")
        assert client.post(f"{base}attachments/", {"file": upload}, format="multipart").status_code == 404
        assert client.patch(f"/api/tasks/{world['tasks'][name].pk}/", {"status": "done"},
                            format="json").status_code == 404
    assert HelpRequests.objects.filter(subject="x").count() == 0


def test_staff_requester_cannot_post_private_note_on_own_ticket(world, as_):
    response = as_("staff_requester").post(f"{_detail(world, 'T3')}comments/",
                                           {"body": "x", "visibility": "private"}, format="json")
    assert response.status_code == 403


def test_export_is_scoped_to_visible_tickets(world, as_):
    call_command("seed_roles", stdout=io.StringIO())
    response = as_("group_manager").get(f"{URL}export/")
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.content.decode())))
    subject_col = rows[0].index("Subject")
    assert {row[subject_col] for row in rows[1:]} == VISIBLE["group_manager"]


@pytest.mark.parametrize("who", ["member", "group_manager", "assigned_tech", "outsider", "staff_requester", "admin"])
def test_queue_tickets_are_scoped(world, as_, who):
    queue = Queue.objects.create(name="Everything", filters={})
    subjects = {row["subject"] for row in as_(who).get(f"/api/queues/{queue.pk}/tickets/").data["results"]}
    assert subjects == VISIBLE[who]


def test_service_desk_report_is_scoped(world, as_):
    data = as_("group_manager").get("/api/reports/service-desk/").data
    assert data["open_tickets"] == len(VISIBLE["group_manager"])


def test_leaving_the_group_revokes_access(world, client_for):
    from accounts.models import User

    world["group"].members.remove(world["people"]["member"])
    # A fresh instance, as the next request would load.
    client = client_for(User.objects.get(pk=world["people"]["member"].pk))
    assert client.get(URL).data["count"] == 0
    assert client.get(_detail(world, "T1")).status_code == 404


@pytest.mark.parametrize("who", ["member", "group_manager", "assigned_tech", "outsider", "staff_requester", "auditor", "admin"])
def test_assets_only_show_visible_linked_tickets(world, as_, who):
    from assets.models import Asset, AssetType

    asset = Asset.objects.create(asset_tag="L1", name="Laptop", asset_type=AssetType.objects.create(name="Laptop"))
    asset.help_requests.set(world["tickets"].values())
    client = as_(who)

    def subjects(row):
        return {t["subject"] for t in row["linked_tickets"]}

    assert subjects(client.get(f"/api/assets/items/{asset.pk}/").data) == VISIBLE[who]
    assert subjects(client.get("/api/assets/items/").data["results"][0]) == VISIBLE[who]


def test_asset_link_response_only_shows_visible_tickets(world, as_):
    from assets.models import Asset, AssetType

    asset = Asset.objects.create(asset_tag="L1", name="Laptop", asset_type=AssetType.objects.create(name="Laptop"))
    asset.help_requests.set([world["tickets"]["T1"], world["tickets"]["T2"]])
    response = as_("member").post(f"/api/assets/items/{asset.pk}/link-ticket/",
                                  {"help_request": str(world["tickets"]["T3"].public_id)}, format="json")
    assert response.status_code == 200, response.data
    assert {t["subject"] for t in response.data["linked_tickets"]} == {"T1", "T3"}
