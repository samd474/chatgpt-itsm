import time

import pytest
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.test import APIClient

from accounts import two_factor
from reports.models import AuditEvent

pytestmark = pytest.mark.django_db
PASSWORD = "pw-123456!"


def code(device, steps_ahead=0):
    """The device's current TOTP code; steps_ahead=1 gives the next window (still within tolerance),
    for a second verification, since a device refuses a window it has already accepted."""
    totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
    totp.time = time.time() + steps_ahead * device.step
    return str(totp.token()).zfill(device.digits)


def enrol(user):
    """A confirmed authenticator plus recovery codes, as if the user had completed setup."""
    device = TOTPDevice.objects.create(user=user, name="Authenticator app", confirmed=True)
    return device, two_factor.new_recovery_codes(user)


def password_step(client, username):
    return client.post("/api/auth/login/", {"username": username, "password": PASSWORD}, format="json")


@pytest.fixture
def no_otp_throttle(settings):
    """django-otp locks a device for 1s, 2s, 4s... after each wrong code. Tests that follow a wrong
    code with a right one turn that off; test_wrong_codes_lock_the_device_briefly covers it."""
    settings.OTP_TOTP_THROTTLE_FACTOR = 0
    settings.OTP_STATIC_THROTTLE_FACTOR = 0


class TestLogin:
    def test_a_code_is_needed_after_the_password(self, make_user, no_otp_throttle):
        user = make_user("tech", "Technician")
        device, _ = enrol(user)
        client = APIClient()

        assert password_step(client, "tech").data == {"two_factor_required": True}
        assert client.get("/api/auth/me/").status_code == 403  # not signed in yet

        assert client.post("/api/auth/2fa/verify/", {"token": "000000"}, format="json").status_code == 400
        assert AuditEvent.objects.filter(activity_type="auth.2fa_failed").exists()

        response = client.post("/api/auth/2fa/verify/", {"token": code(device)}, format="json")
        assert response.status_code == 200 and response.data["two_factor_required"] is False
        me = client.get("/api/auth/me/").data
        assert me["username"] == "tech" and me["two_factor_enabled"] is True
        assert client.get("/api/help-requests/").status_code == 200
        assert AuditEvent.objects.get(activity_type="auth.login").metadata == {"two_factor": "authenticator"}

    def test_recovery_codes_work_once(self, make_user):
        user = make_user("tech", "Technician")
        _, codes = enrol(user)
        first = APIClient()
        password_step(first, "tech")
        assert first.post("/api/auth/2fa/verify/", {"token": codes[0]}, format="json").status_code == 200
        assert two_factor.recovery_codes_left(user) == 9

        second = APIClient()
        password_step(second, "tech")
        assert second.post("/api/auth/2fa/verify/", {"token": codes[0]}, format="json").status_code == 400

    def test_the_code_step_needs_a_recent_password_step(self, make_user, monkeypatch):
        user = make_user("tech", "Technician")
        device, _ = enrol(user)
        client = APIClient()
        assert client.post("/api/auth/2fa/verify/", {"token": code(device)}, format="json").status_code == 400

        password_step(client, "tech")
        monkeypatch.setattr(two_factor, "PENDING_TTL_SECONDS", -1)  # the pending login has expired
        assert client.post("/api/auth/2fa/verify/", {"token": code(device)}, format="json").status_code == 400
        assert client.get("/api/auth/me/").status_code == 403

    def test_accounts_without_2fa_sign_in_as_before(self, make_user):
        make_user("req", "Requester")
        client = APIClient()
        assert password_step(client, "req").data["two_factor_required"] is False
        assert client.get("/api/help-requests/").status_code == 200

    def test_wrong_codes_lock_the_device_briefly(self, make_user):
        """Guessing protection: right after a wrong code, even the right code is refused for a moment."""
        user = make_user("tech", "Technician")
        device, _ = enrol(user)
        client = APIClient()
        password_step(client, "tech")
        assert client.post("/api/auth/2fa/verify/", {"token": "000000"}, format="json").status_code == 400
        assert client.post("/api/auth/2fa/verify/", {"token": code(device)}, format="json").status_code == 400
        assert client.get("/api/auth/me/").status_code == 403

    def test_the_code_step_is_rate_limited(self, make_user):
        enrol(make_user("tech", "Technician"))
        client = APIClient()
        password_step(client, "tech")
        statuses = [client.post("/api/auth/2fa/verify/", {"token": "000000"}, format="json").status_code for _ in range(11)]
        assert statuses[-1] == 429


class TestEnforcement:
    def test_required_roles_must_set_up_2fa_before_anything_else(self, make_user, no_otp_throttle):
        make_user("admin", "Administrator")
        client = APIClient()
        assert password_step(client, "admin").data["two_factor_required"] is False

        blocked = client.get("/api/help-requests/")
        assert blocked.status_code == 403 and blocked.json()["code"] == "two_factor_setup_required"
        assert client.get("/api/auth/me/").data["two_factor_setup_needed"] is True

        setup = client.post("/api/auth/2fa/setup/").data
        assert setup["otpauth_url"].startswith("otpauth://totp/") and setup["qr_svg"].startswith("data:image/svg+xml")
        assert client.post("/api/auth/2fa/confirm/", {"token": "000000"}, format="json").status_code == 400
        device = two_factor.pending_device(client.get("/api/auth/me/").wsgi_request.user)
        assert device is not None
        confirmed = client.post("/api/auth/2fa/confirm/", {"token": code(device)}, format="json")
        assert confirmed.status_code == 200 and len(confirmed.data["recovery_codes"]) == 10

        assert client.get("/api/help-requests/").status_code == 200  # this session is now verified
        assert AuditEvent.objects.filter(activity_type="auth.2fa_enabled").exists()

    def test_superusers_count_as_administrators(self, make_user):
        make_user("root", is_superuser=True)
        client = APIClient()
        password_step(client, "root")
        assert client.get("/api/help-requests/").json()["code"] == "two_factor_setup_required"

    def test_other_roles_are_not_forced(self, make_user):
        make_user("tech", "Technician")
        client = APIClient()
        password_step(client, "tech")
        assert client.get("/api/help-requests/").status_code == 200

    def test_sessions_from_before_2fa_was_enabled_are_held(self, make_user):
        make_user("tech", "Technician")
        old_session, new_session = APIClient(), APIClient()
        password_step(old_session, "tech")
        password_step(new_session, "tech")

        new_session.post("/api/auth/2fa/setup/")
        device = TOTPDevice.objects.get(user__username="tech", confirmed=False)
        assert new_session.post("/api/auth/2fa/confirm/", {"token": code(device)}, format="json").status_code == 200

        assert new_session.get("/api/help-requests/").status_code == 200
        held = old_session.get("/api/help-requests/")
        assert held.status_code == 403 and held.json()["code"] == "two_factor_verification_required"

    def test_django_admin_needs_a_verified_session(self, make_user):
        admin = make_user("admin", "Administrator", is_staff=True, is_superuser=True)
        password_only = APIClient()
        password_only.force_login(admin)
        assert password_only.get("/admin/").status_code == 302  # sent to the admin login (which asks for a code)

        device, _ = enrol(admin)
        verified = APIClient()
        password_step(verified, "admin")
        verified.post("/api/auth/2fa/verify/", {"token": code(device)}, format="json")
        assert verified.get("/admin/").status_code == 200


class TestManagement:
    def signed_in(self, make_user, role="Technician"):
        user = make_user("tech", role)
        device, codes = enrol(user)
        client = APIClient()
        password_step(client, "tech")
        assert client.post("/api/auth/2fa/verify/", {"token": code(device)}, format="json").status_code == 200
        return user, device, codes, client

    def test_status_and_setup_rules(self, make_user):
        user, _, _, client = self.signed_in(make_user)
        assert client.get("/api/auth/2fa/").data == {"enabled": True, "required_by_role": False, "recovery_codes_left": 10}
        assert client.post("/api/auth/2fa/setup/").status_code == 400  # already on

        fresh = APIClient()
        make_user("req", "Requester")
        password_step(fresh, "req")
        assert fresh.post("/api/auth/2fa/confirm/", {"token": "123456"}, format="json").status_code == 400  # no setup yet

    def test_recovery_codes_can_be_replaced_with_a_current_code(self, make_user, no_otp_throttle):
        user, device, old_codes, client = self.signed_in(make_user)
        assert client.post("/api/auth/2fa/recovery-codes/", {"token": "000000"}, format="json").status_code == 400
        response = client.post("/api/auth/2fa/recovery-codes/", {"token": code(device, steps_ahead=1)}, format="json")
        assert response.status_code == 200
        assert not StaticToken.objects.filter(token__in=old_codes).exists()
        assert set(StaticToken.objects.values_list("token", flat=True)) == set(response.data["recovery_codes"])

    def test_disabling_needs_a_code(self, make_user, no_otp_throttle):
        user, _, codes, client = self.signed_in(make_user)
        assert client.post("/api/auth/2fa/disable/", {"token": "000000"}, format="json").status_code == 400
        assert client.post("/api/auth/2fa/disable/", {"token": codes[1]}, format="json").status_code == 204
        assert not two_factor.is_enabled(user) and two_factor.recovery_codes_left(user) == 0
        assert AuditEvent.objects.filter(activity_type="auth.2fa_disabled").exists()
        assert client.get("/api/help-requests/").status_code == 200

    def test_required_roles_cannot_disable(self, make_user):
        user, _, codes, client = self.signed_in(make_user, role="Administrator")
        response = client.post("/api/auth/2fa/disable/", {"token": codes[0]}, format="json")
        assert response.status_code == 400 and two_factor.is_enabled(user)
