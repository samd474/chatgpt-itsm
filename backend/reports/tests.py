import pytest
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile

from helprequests.models import Category
from reports.audit import write_audit_event
from reports.csv_utils import escape_cell
from reports.models import AuditEvent


@pytest.mark.parametrize("value,expected", [
    ("=1+1", "'=1+1"), ("+cmd", "'+cmd"), ("-2", "'-2"), ("@SUM(A1)", "'@SUM(A1)"), ("plain", "plain"), (None, ""),
])
def test_escape_cell(value, expected):
    assert escape_cell(value) == expected


@pytest.mark.django_db
def test_audit_events_are_append_only():
    event = write_audit_event(None, "test.event", object_type="x", object_id="1")
    event.metadata = {"tampered": True}
    with pytest.raises(PermissionDenied):
        event.save()
    with pytest.raises(PermissionDenied):
        event.delete()


@pytest.mark.django_db
def test_audit_api_permissions(make_user, client_for):
    write_audit_event(None, "test.event", object_type="x", object_id="1")
    assert client_for(make_user("req", "Requester")).get("/api/audit/").status_code == 403
    response = client_for(make_user("aud", "Auditor")).get("/api/audit/")
    assert response.status_code == 200
    assert response.data["results"][0]["event_type"] == "test.event"
    assert client_for(make_user("aud2", "Auditor")).delete(f"/api/audit/{response.data['results'][0]['id']}/").status_code == 405


@pytest.mark.django_db
def test_service_desk_report_requires_manager(make_user, client_for):
    assert client_for(make_user("req", "Requester")).get("/api/reports/service-desk/").status_code == 403
    data = client_for(make_user("boss", "Manager")).get("/api/reports/service-desk/").data
    assert set(data) >= {"open_tickets", "unassigned", "sla_at_risk", "sla_breached"}


@pytest.mark.django_db
def test_staged_category_import(make_user, client_for):
    admin = client_for(make_user("admin", "Administrator"))
    csv_file = SimpleUploadedFile("cats.csv", b"name,parent,active\nHardware,,true\nLaptops,Hardware,yes\nBad,Missing,true\n")
    response = admin.post("/api/imports/", {"kind": "categories", "file": csv_file}, format="multipart")
    assert response.status_code == 201, response.data
    assert len(response.data["preview"]["valid"]) == 2
    assert response.data["preview"]["errors"][0]["row"] == 4
    assert not Category.objects.exists()  # nothing changes before confirmation

    confirmed = admin.post(f"/api/imports/{response.data['id']}/confirm/")
    assert confirmed.status_code == 200
    assert Category.objects.get(name="Laptops").parent.name == "Hardware"
    assert admin.post(f"/api/imports/{response.data['id']}/confirm/").status_code == 400
    assert AuditEvent.objects.filter(activity_type="import.applied").exists()
