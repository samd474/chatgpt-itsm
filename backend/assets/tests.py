import pytest

from assets.models import Asset, AssetType
from helprequests.models import HelpRequests


@pytest.fixture
def setup(make_user):
    laptop = AssetType.objects.create(name="Laptop")
    return {"type": laptop, "tech": make_user("tech", "Technician"), "req": make_user("req", "Requester"),
            "other": make_user("other", "Requester"), "auditor": make_user("aud", "Auditor")}


@pytest.mark.django_db
def test_staff_create_asset_with_generated_tag(setup, client_for):
    response = client_for(setup["tech"]).post("/api/assets/items/", {"name": "ThinkPad", "asset_type": setup["type"].pk,
                                                                     "assigned_to": setup["req"].pk, "purchase_cost": "1200.00"}, format="json")
    assert response.status_code == 201, response.data
    asset = Asset.objects.get()
    assert asset.asset_tag == f"AST-{asset.pk:06d}"


@pytest.mark.django_db
def test_requester_sees_only_own_assets_without_cost(setup, client_for):
    mine = Asset.objects.create(asset_tag="A1", name="Mine", asset_type=setup["type"], assigned_to=setup["req"], purchase_cost=999)
    Asset.objects.create(asset_tag="A2", name="Theirs", asset_type=setup["type"], assigned_to=setup["other"])
    data = client_for(setup["req"]).get("/api/assets/items/").data
    assert [a["asset_tag"] for a in data["results"]] == ["A1"]
    assert "purchase_cost" not in data["results"][0]
    assert client_for(setup["req"]).patch(f"/api/assets/items/{mine.pk}/", {"name": "x"}, format="json").status_code == 403


@pytest.mark.django_db
def test_auditor_read_only_and_no_delete(setup, client_for):
    asset = Asset.objects.create(asset_tag="A1", name="Srv", asset_type=setup["type"])
    auditor = client_for(setup["auditor"])
    assert auditor.get(f"/api/assets/items/{asset.pk}/").status_code == 200
    assert auditor.patch(f"/api/assets/items/{asset.pk}/", {"name": "x"}, format="json").status_code == 403
    assert client_for(setup["tech"]).delete(f"/api/assets/items/{asset.pk}/").status_code == 405


@pytest.mark.django_db
def test_relationships_and_history(setup, client_for):
    a = Asset.objects.create(asset_tag="APP", name="App", asset_type=setup["type"])
    b = Asset.objects.create(asset_tag="SRV", name="Server", asset_type=setup["type"])
    tech = client_for(setup["tech"])
    assert tech.post(f"/api/assets/items/{a.pk}/relationships/", {"target": a.pk, "kind": "runs_on"}, format="json").status_code == 400
    assert tech.post(f"/api/assets/items/{a.pk}/relationships/", {"target": b.pk, "kind": "runs_on"}, format="json").status_code == 201
    assert len(tech.get(f"/api/assets/items/{b.pk}/relationships/").data) == 1
    tech.patch(f"/api/assets/items/{a.pk}/", {"status": "retired"}, format="json")
    assert any(e["event_type"] == "asset.updated" for e in tech.get(f"/api/assets/items/{a.pk}/history/").data)


@pytest.mark.django_db
def test_link_ticket_respects_ticket_visibility(setup, client_for, network_team):
    asset = Asset.objects.create(asset_tag="A1", name="PC", asset_type=setup["type"])
    ticket = HelpRequests.objects.create(request_type="incident", subject="x", requester=setup["req"])
    tech = client_for(setup["tech"])
    # The technician can't see this ticket (not in its group), so can't link it.
    assert tech.post(f"/api/assets/items/{asset.pk}/link-ticket/", {"help_request": str(ticket.public_id)}, format="json").status_code == 400
    ticket.technician = setup["tech"]
    ticket.save()
    assert tech.post(f"/api/assets/items/{asset.pk}/link-ticket/", {"help_request": str(ticket.public_id)}, format="json").status_code == 200
