import pytest
from rest_framework.test import APIClient

from reports.models import AuditEvent


@pytest.mark.django_db
def test_session_login_flow_with_csrf(make_user):
    user = make_user("ada", "Requester")
    client = APIClient(enforce_csrf_checks=True)

    assert client.get("/api/auth/me/").status_code == 403  # not authenticated
    token = client.get("/api/auth/csrf/").data["csrfToken"]

    assert client.post("/api/auth/login/", {"username": "ada", "password": "pw-123456!"}, format="json").status_code == 403  # no CSRF header
    response = client.post("/api/auth/login/", {"username": "ada", "password": "pw-123456!"}, format="json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200

    me = client.get("/api/auth/me/").data
    assert me["username"] == "ada"
    assert me["groups"] == ["Requester"]
    assert AuditEvent.objects.filter(activity_type="auth.login", initiated_by=user).exists()


@pytest.mark.django_db
def test_failed_and_disabled_logins(make_user):
    make_user("ada", "Requester")
    make_user("gone", "Requester", is_enabled=False)
    client = APIClient()
    assert client.post("/api/auth/login/", {"username": "ada", "password": "wrong"}, format="json").status_code == 400
    assert client.post("/api/auth/login/", {"username": "gone", "password": "pw-123456!"}, format="json").status_code == 400
    failed = AuditEvent.objects.filter(activity_type="auth.login_failed")
    assert failed.count() == 2
    assert "wrong" not in str(list(failed.values()))  # passwords are never recorded


@pytest.mark.django_db
def test_login_is_rate_limited(make_user):
    make_user("ada", "Requester")
    client = APIClient()
    codes = [client.post("/api/auth/login/", {"username": "ada", "password": "wrong"}, format="json").status_code for _ in range(11)]
    assert codes[-1] == 429
