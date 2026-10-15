import pytest

from catalog.models import CatalogItem
from catalog.validation import validate_answers, validate_schema
from helprequests.models import Approval, HelpRequests

SCHEMA = [
    {"key": "employee_name", "label": "Employee name", "type": "text", "required": True},
    {"key": "start_date", "label": "Start date", "type": "date", "required": True},
    {"key": "needs_laptop", "label": "Laptop required", "type": "boolean"},
    {"key": "laptop_type", "label": "Laptop type", "type": "select", "options": ["Standard", "Developer"],
     "required": True, "show_when": {"field": "needs_laptop", "equals": True}},
]


def test_schema_validation():
    assert validate_schema(SCHEMA) == []
    assert validate_schema([{"key": "a", "type": "select"}])  # select without options
    assert validate_schema([{"key": "a", "type": "text", "show_when": {"field": "missing", "equals": 1}}])


def test_required_fields_and_types():
    _, errors = validate_answers(SCHEMA, {"start_date": "not a date"})
    assert set(errors) == {"employee_name", "start_date"}


def test_conditional_field_only_required_when_visible():
    cleaned, errors = validate_answers(SCHEMA, {"employee_name": "Ada", "start_date": "2026-11-02", "needs_laptop": False,
                                                "laptop_type": "Gaming"})
    assert errors == {}
    assert "laptop_type" not in cleaned  # hidden answers are dropped
    _, errors = validate_answers(SCHEMA, {"employee_name": "Ada", "start_date": "2026-11-02", "needs_laptop": True,
                                          "laptop_type": "Gaming"})
    assert errors == {"laptop_type": "Choose one of the listed options."}


def test_unknown_fields_rejected():
    _, errors = validate_answers(SCHEMA, {"employee_name": "Ada", "start_date": "2026-11-02", "salary": 1})
    assert "salary" in errors


@pytest.mark.django_db
def test_submit_creates_request_with_approval(make_user, client_for):
    requester = make_user("req", "Requester")
    approver = make_user("boss", "Manager")
    item = CatalogItem.objects.create(name="New starter", slug="new-starter", short_description="x",
                                      form_schema=SCHEMA, requires_approval=True)
    item.approvers.add(approver)

    client = client_for(requester)
    bad = client.post("/api/catalog/items/new-starter/submit/", {"request_payload": {}}, format="json")
    assert bad.status_code == 400

    response = client.post("/api/catalog/items/new-starter/submit/", {
        "request_payload": {"employee_name": "Ada", "start_date": "2026-11-02", "needs_laptop": True, "laptop_type": "Developer"},
    }, format="json")
    assert response.status_code == 201, response.data
    ticket = HelpRequests.objects.get(public_id=response.data["public_id"])
    assert ticket.request_type == "request"
    assert ticket.request_number.startswith("REQ-")
    assert ticket.request_payload["answers"]["laptop_type"] == "Developer"
    approval = Approval.objects.get(help_request=ticket)

    # Only the assigned approver may decide.
    assert client.post(f"/api/approvals/{approval.pk}/decide/", {"state": "approved"}, format="json").status_code == 404
    decided = client_for(approver).post(f"/api/approvals/{approval.pk}/decide/", {"state": "rejected", "comment": "No budget"}, format="json")
    assert decided.status_code == 200
    ticket.refresh_from_db()
    assert ticket.status == "cancelled"
