from datetime import timedelta

import pytest
from django.utils import timezone

from alerts.models import NotificationEvent
from contracts.models import Contract, Vendor
from contracts.tasks import send_renewal_reminders


@pytest.fixture
def setup(make_user):
    return {"vendor": Vendor.objects.create(name="Acme"), "tech": make_user("tech", "Technician"),
            "manager": make_user("boss", "Manager"), "req": make_user("req", "Requester")}


def payload(vendor, **extra):
    today = timezone.localdate()
    return {"name": "Firewall support", "vendor": vendor.pk, "contract_type": "support", "status": "active",
            "start_date": str(today), "end_date": str(today + timedelta(days=365)), "value": "12000.00", **extra}


@pytest.mark.django_db
def test_only_managers_write_and_technicians_never_see_money(setup, client_for):
    assert client_for(setup["tech"]).post("/api/contracts/items/", payload(setup["vendor"]), format="json").status_code == 403
    response = client_for(setup["manager"]).post("/api/contracts/items/", payload(setup["vendor"]), format="json")
    assert response.status_code == 201, response.data
    assert response.data["number"].startswith("CTR-")
    tech_view = client_for(setup["tech"]).get(f"/api/contracts/items/{response.data['id']}/").data
    assert "value" not in tech_view and tech_view["vendor_name"] == "Acme"
    assert client_for(setup["req"]).get("/api/contracts/items/").status_code == 403


@pytest.mark.django_db
def test_end_before_start_rejected(setup, client_for):
    today = timezone.localdate()
    bad = payload(setup["vendor"], end_date=str(today - timedelta(days=1)))
    assert client_for(setup["manager"]).post("/api/contracts/items/", bad, format="json").status_code == 400


@pytest.mark.django_db
def test_renewal_reminder_sent_once(setup):
    today = timezone.localdate()
    contract = Contract.objects.create(number="CTR-1", name="AV", vendor=setup["vendor"], contract_type="license",
                                       status="active", start_date=today - timedelta(days=300), end_date=today + timedelta(days=10),
                                       owner=setup["manager"])
    assert send_renewal_reminders() == 1
    assert send_renewal_reminders() == 0
    assert NotificationEvent.objects.filter(event_type="contract.renewal_due", object_id=str(contract.pk)).count() == 1


@pytest.mark.django_db
def test_lapsed_contracts_expire(setup):
    today = timezone.localdate()
    contract = Contract.objects.create(number="CTR-2", name="Old", vendor=setup["vendor"], contract_type="lease", status="active",
                                       start_date=today - timedelta(days=400), end_date=today - timedelta(days=1))
    send_renewal_reminders()
    contract.refresh_from_db()
    assert contract.status == "expired"
