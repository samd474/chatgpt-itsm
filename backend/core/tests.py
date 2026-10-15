import socket
import threading

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from accounts.models import User
from core.models import CustomFieldDefinition
from core.scanning import ScanUnavailable, scan_file
from helprequests.models import HelpRequests
from reports.models import AuditEvent


class FakeClamd:
    """Minimal clamd INSTREAM server: flags any stream containing EICAR."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen()
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                data = b""
                while not data.endswith(b"\0\0\0\0"):
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                verdict = b"stream: Eicar-Test-Signature FOUND\0" if b"EICAR" in data else b"stream: OK\0"
                conn.sendall(verdict)


@pytest.fixture
def clamd(settings):
    server = FakeClamd()
    settings.CLAMAV_HOST = "127.0.0.1"
    settings.CLAMAV_PORT = server.port
    settings.ATTACHMENT_SCAN_REQUIRED = True
    return server


def test_scanner_clean_and_infected(clamd):
    assert scan_file(SimpleUploadedFile("ok.txt", b"hello")).clean
    result = scan_file(SimpleUploadedFile("bad.txt", b"X5O!P%@AP EICAR test"))
    assert not result.clean
    assert "Eicar" in result.detail


def test_scanner_fails_closed_when_required(settings):
    settings.CLAMAV_HOST = ""
    settings.ATTACHMENT_SCAN_REQUIRED = True
    with pytest.raises(ScanUnavailable):
        scan_file(SimpleUploadedFile("ok.txt", b"hello"))
    settings.CLAMAV_HOST = "127.0.0.1"
    settings.CLAMAV_PORT = 1  # nothing listening
    with pytest.raises(ScanUnavailable):
        scan_file(SimpleUploadedFile("ok.txt", b"hello"))


@pytest.mark.django_db
def test_infected_upload_is_rejected_and_audited(clamd, make_user, client_for):
    requester = make_user("req", "Requester")
    client = client_for(requester)
    public_id = client.post("/api/help-requests/", {"request_type": "incident", "subject": "Malware?", "description": "Attached sample",
                                                    "impact": 3, "urgency": 3}, format="json").data["public_id"]
    bad = SimpleUploadedFile("invoice.pdf", b"%PDF EICAR payload")
    response = client.post(f"/api/help-requests/{public_id}/attachments/", {"file": bad}, format="multipart")
    assert response.status_code == 400
    assert AuditEvent.objects.filter(activity_type="attachment.malware_blocked").exists()


@pytest.mark.django_db
def test_disabled_user_session_stops_working(make_user):
    user = make_user("ada", "Requester")
    client = APIClient()
    assert client.login(username="ada", password="pw-123456!")
    assert client.get("/api/auth/me/").status_code == 200
    User.objects.filter(pk=user.pk).update(is_enabled=False)
    assert client.get("/api/auth/me/").status_code == 403


@pytest.mark.django_db
class TestAdminConsoleEscalation:
    def test_requires_administrator(self, make_user, client_for):
        assert client_for(make_user("tech", "Technician")).get("/api/admin/users/").status_code == 403

    def test_cannot_change_own_roles_or_disable_self(self, make_user, client_for):
        admin = make_user("admin", "Administrator")
        client = client_for(admin)
        assert client.patch(f"/api/admin/users/{admin.pk}/", {"roles": ["Administrator", "Auditor"]}, format="json").status_code == 400
        assert client.patch(f"/api/admin/users/{admin.pk}/", {"is_enabled": False}, format="json").status_code == 400

    def test_superuser_flag_is_never_writable(self, make_user, client_for):
        admin = make_user("admin", "Administrator")
        target = make_user("bob", "Requester")
        client_for(admin).patch(f"/api/admin/users/{target.pk}/", {"is_superuser": True}, format="json")
        target.refresh_from_db()
        assert not target.is_superuser

    def test_superusers_hidden_from_non_superuser_admins(self, make_user, client_for):
        admin = make_user("admin", "Administrator")
        root = User.objects.create_superuser("root", "root@example.test", "pw-123456!")
        client = client_for(admin)
        assert client.get(f"/api/admin/users/{root.pk}/").status_code == 404
        assert client.patch(f"/api/admin/users/{root.pk}/", {"password": "N3w-strong-pass!"}, format="json").status_code == 404

    def test_cannot_reset_another_admins_password(self, make_user, client_for):
        admin = make_user("admin", "Administrator")
        peer = make_user("peer", "Administrator")
        response = client_for(admin).patch(f"/api/admin/users/{peer.pk}/", {"password": "N3w-strong-pass!"}, format="json")
        assert response.status_code == 400

    def test_create_user_with_roles_is_audited(self, make_user, client_for):
        from django.contrib.auth.models import Group

        Group.objects.get_or_create(name="Technician")
        admin = make_user("admin", "Administrator")
        response = client_for(admin).post("/api/admin/users/", {
            "username": "newtech", "email": "newtech@example.test", "password": "Sufficiently-L0ng!", "roles": ["Technician"],
        }, format="json")
        assert response.status_code == 201, response.data
        assert "password" not in response.data
        user = User.objects.get(username="newtech")
        assert user.check_password("Sufficiently-L0ng!")
        assert AuditEvent.objects.filter(activity_type="admin.user.created").exists()
        assert "Sufficiently" not in str(AuditEvent.objects.values_list("after", flat=True))

    def test_weak_password_rejected(self, make_user, client_for):
        admin = make_user("admin", "Administrator")
        response = client_for(admin).post("/api/admin/users/", {"username": "x", "email": "x@example.test", "password": "password"}, format="json")
        assert response.status_code == 400

    def test_built_in_roles_protected(self, make_user, client_for):
        admin = make_user("admin", "Administrator")
        from django.contrib.auth.models import Group

        group = Group.objects.get(name="Administrator")
        assert client_for(admin).delete(f"/api/admin/roles/{group.pk}/").status_code == 400


@pytest.mark.django_db
def test_django_admin_cannot_grant_superuser(make_user, rf):
    from django.contrib.admin.sites import site

    from accounts.admin import ITSMUserAdmin

    staff = make_user("staffer", "Administrator", is_staff=True)
    request = rf.get("/admin/")
    request.user = staff
    model_admin = ITSMUserAdmin(User, site)
    assert "is_superuser" in model_admin.get_readonly_fields(request, staff)
    assert "groups" in model_admin.get_readonly_fields(request, staff)


@pytest.mark.django_db
def test_custom_fields_validated_and_hidden_from_requesters(make_user, client_for):
    CustomFieldDefinition.objects.create(entity="ticket", key="device", label="Device", field_type="select",
                                         options=["Laptop", "Desktop"], required=True)
    CustomFieldDefinition.objects.create(entity="ticket", key="root_cause", label="Root cause", visible_to_requester=False)
    requester = make_user("req", "Requester")
    tech = make_user("tech", "Technician")
    client = client_for(requester)
    base = {"request_type": "incident", "subject": "Broken screen", "description": "Screen flickers", "impact": 3, "urgency": 3}
    assert client.post("/api/help-requests/", base, format="json").status_code == 400  # device required
    bad = client.post("/api/help-requests/", {**base, "custom_fields": {"device": "Phone"}}, format="json")
    assert bad.status_code == 400
    sneaky = client.post("/api/help-requests/", {**base, "custom_fields": {"device": "Laptop", "root_cause": "user error"}}, format="json")
    assert sneaky.status_code == 400  # requesters can't write staff-only fields

    created = client.post("/api/help-requests/", {**base, "custom_fields": {"device": "Laptop"}}, format="json")
    assert created.status_code == 201
    ticket = HelpRequests.objects.get(public_id=created.data["public_id"])
    ticket.custom_fields["root_cause"] = "loose cable"
    ticket.save()
    assert "root_cause" not in client.get(f"/api/help-requests/{ticket.public_id}/").data["custom_fields"]
    ticket.technician = tech
    ticket.save()
    assert client_for(tech).get(f"/api/help-requests/{ticket.public_id}/").data["custom_fields"]["root_cause"] == "loose cable"


@pytest.mark.django_db
def test_notification_templates_reject_attribute_access(make_user, client_for):
    admin = client_for(make_user("admin", "Administrator"))
    bad = admin.post("/api/admin/notification-templates/", {"event_type": "ticket.created", "subject": "{number.__class__}",
                                                            "body": "x"}, format="json")
    assert bad.status_code == 400
    ok = admin.post("/api/admin/notification-templates/", {"event_type": "ticket.created", "subject": "[{number}] Thanks",
                                                           "body": "Hi {recipient_name}"}, format="json")
    assert ok.status_code == 201
