from datetime import timedelta

import pytest
from django.utils import timezone

from assets.models import Asset, AssetType
from changes.models import ChangeApproval, ChangeRequest

URL = "/api/changes/items/"
PLANS = {"implementation_plan": "Apply patch", "backout_plan": "Restore snapshot", "test_plan": "Smoke test"}


@pytest.fixture
def setup(make_user):
    return {"tech": make_user("tech", "Technician"), "cab1": make_user("cab1", "CAB", "Technician"),
            "cab2": make_user("cab2", "CAB", "Technician"), "mgr": make_user("mgr", "Manager"), "req": make_user("req", "Requester")}


def create(client, **extra):
    return client.post(URL, {"title": "Patch firewall", "description": "Monthly patch", "change_type": "normal", **PLANS, **extra}, format="json")


@pytest.mark.django_db
def test_requesters_have_no_access(setup, client_for):
    assert client_for(setup["req"]).get(URL).status_code == 403


@pytest.mark.django_db
def test_normal_change_needs_every_cab_approval(setup, client_for):
    change = create(client_for(setup["tech"])).data
    assert change["number"].startswith("CHG-")
    tech = client_for(setup["tech"])
    assert tech.post(f"{URL}{change['id']}/transition/", {"status": "awaiting_approval"}, format="json").status_code == 200
    approvals = ChangeApproval.objects.filter(change_id=change["id"])
    assert set(approvals.values_list("approver__username", flat=True)) == {"cab1", "cab2"}

    first = approvals.get(approver=setup["cab1"])
    client_for(setup["cab1"]).post(f"/api/changes/approvals/{first.pk}/decide/", {"state": "approved"}, format="json")
    assert ChangeRequest.objects.get(pk=change["id"]).status == "awaiting_approval"
    second = approvals.get(approver=setup["cab2"])
    # Someone else can't use cab2's approval.
    assert client_for(setup["cab1"]).post(f"/api/changes/approvals/{second.pk}/decide/", {"state": "approved"}, format="json").status_code == 400
    client_for(setup["cab2"]).post(f"/api/changes/approvals/{second.pk}/decide/", {"state": "approved"}, format="json")
    assert ChangeRequest.objects.get(pk=change["id"]).status == "approved"


@pytest.mark.django_db
def test_requester_never_approves_own_change(setup, client_for):
    change = create(client_for(setup["cab1"])).data
    client_for(setup["cab1"]).post(f"{URL}{change['id']}/transition/", {"status": "awaiting_approval"}, format="json")
    assert not ChangeApproval.objects.filter(change_id=change["id"], approver=setup["cab1"]).exists()


@pytest.mark.django_db
def test_plans_required_and_content_locked_after_approval(setup, client_for):
    tech = client_for(setup["tech"])
    change = tech.post(URL, {"title": "No plan", "description": "x"}, format="json").data
    assert tech.post(f"{URL}{change['id']}/transition/", {"status": "awaiting_approval"}, format="json").status_code == 400
    standard = create(tech, change_type="standard").data
    assert tech.post(f"{URL}{standard['id']}/transition/", {"status": "awaiting_approval"}, format="json").data["status"] == "approved"
    assert tech.patch(f"{URL}{standard['id']}/", {"description": "sneaky edit"}, format="json").status_code == 403
    # Status can never be set directly.
    tech.patch(f"{URL}{change['id']}/", {"status": "closed"}, format="json")
    assert ChangeRequest.objects.get(pk=change["id"]).status == "draft"


@pytest.mark.django_db
def test_full_lifecycle_and_conflicts(setup, client_for):
    asset = Asset.objects.create(asset_tag="FW1", name="Firewall", asset_type=AssetType.objects.create(name="Network"))
    start = timezone.now() + timedelta(days=1)
    window = {"planned_start": start.isoformat(), "planned_end": (start + timedelta(hours=2)).isoformat()}
    tech, mgr = client_for(setup["tech"]), client_for(setup["mgr"])

    first = create(tech, change_type="standard", assets=[asset.pk]).data
    second = create(tech, change_type="standard", assets=[asset.pk]).data
    for change in (first, second):
        tech.post(f"{URL}{change['id']}/transition/", {"status": "awaiting_approval"}, format="json")
        mgr.patch(f"{URL}{change['id']}/", {**window, "implementer": setup["tech"].pk}, format="json")

    assert tech.post(f"{URL}{first['id']}/transition/", {"status": "scheduled"}, format="json").status_code == 403  # managers schedule
    assert mgr.post(f"{URL}{first['id']}/transition/", {"status": "scheduled"}, format="json").status_code == 200
    clash = mgr.post(f"{URL}{second['id']}/transition/", {"status": "scheduled"}, format="json")
    assert clash.status_code == 400 and first["number"] in str(clash.data)
    assert len(tech.get(f"{URL}{second['id']}/conflicts/").data) == 1

    assert tech.post(f"{URL}{first['id']}/transition/", {"status": "implementing"}, format="json").status_code == 200
    assert tech.post(f"{URL}{first['id']}/transition/", {"status": "review"}, format="json").status_code == 400  # needs outcome
    assert tech.post(f"{URL}{first['id']}/transition/", {"status": "review", "outcome": "successful"}, format="json").status_code == 200
    assert tech.post(f"{URL}{first['id']}/transition/", {"status": "closed", "closure_notes": "All good"}, format="json").status_code == 200

    calendar = tech.get(f"{URL}calendar/", {"start": (start - timedelta(days=1)).isoformat(), "end": (start + timedelta(days=1)).isoformat()})
    assert {c["number"] for c in calendar.data} == {first["number"], second["number"]}


@pytest.mark.django_db
def test_emergency_needs_single_approval_and_rejection(setup, client_for):
    tech = client_for(setup["tech"])
    emergency = create(tech, change_type="emergency").data
    tech.post(f"{URL}{emergency['id']}/transition/", {"status": "awaiting_approval"}, format="json")
    approval = ChangeApproval.objects.filter(change_id=emergency["id"], approver=setup["cab1"]).get()
    client_for(setup["cab1"]).post(f"/api/changes/approvals/{approval.pk}/decide/", {"state": "approved"}, format="json")
    assert ChangeRequest.objects.get(pk=emergency["id"]).status == "approved"

    normal = create(tech).data
    tech.post(f"{URL}{normal['id']}/transition/", {"status": "awaiting_approval"}, format="json")
    approval = ChangeApproval.objects.filter(change_id=normal["id"], approver=setup["cab2"]).get()
    client_for(setup["cab2"]).post(f"/api/changes/approvals/{approval.pk}/decide/", {"state": "rejected", "comment": "Too risky"}, format="json")
    assert ChangeRequest.objects.get(pk=normal["id"]).status == "rejected"
    assert tech.patch(f"{URL}{normal['id']}/", {"risk": "low"}, format="json").status_code == 200  # rework allowed
