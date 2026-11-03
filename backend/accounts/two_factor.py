"""Two-factor authentication (TOTP authenticator apps, plus one-time recovery codes).

Built on django-otp: a confirmed TOTPDevice is the authenticator app, a StaticDevice holds the
recovery codes, and django_otp.login() marks a session as verified (which also protects /admin/).
"""
import time
from base64 import b32encode

import segno
from django.conf import settings
from django_otp import match_token
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from .roles import has_role

PENDING_KEY = "two_factor_pending"  # session: a user who passed the password step but not the code
PENDING_TTL_SECONDS = 5 * 60
RECOVERY_CODE_COUNT = 10


def required_for(user):
    """Whether this user's roles require 2FA (settings.TWO_FACTOR_REQUIRED_ROLES; superusers count as
    Administrators)."""
    roles = getattr(settings, "TWO_FACTOR_REQUIRED_ROLES", ())
    return bool(roles) and has_role(user, *roles)


def is_enabled(user):
    return TOTPDevice.objects.filter(user=user, confirmed=True).exists()


def recovery_codes_left(user):
    return StaticToken.objects.filter(device__user=user, device__confirmed=True).count()


def verify(user, token):
    """The device that accepts `token` (an authenticator code or an unused recovery code), else None.

    django-otp throttles repeated failures per device, and a recovery code is consumed when used.
    """
    token = (token or "").strip().replace(" ", "")
    if not token:
        return None
    return match_token(user, token)


# --- the login step -----------------------------------------------------------------------------

def start_pending_login(request, user):
    request.session[PENDING_KEY] = {"user_id": user.pk, "backend": user.backend, "at": time.time()}


def pending_login(request):
    """(user_id, backend) of a login waiting for its code, or None if there's none or it expired."""
    pending = request.session.get(PENDING_KEY)
    if not pending or time.time() - pending.get("at", 0) > PENDING_TTL_SECONDS:
        request.session.pop(PENDING_KEY, None)
        return None
    return pending["user_id"], pending["backend"]


def clear_pending_login(request):
    request.session.pop(PENDING_KEY, None)


# --- enrolment ----------------------------------------------------------------------------------

def start_setup(user):
    """A fresh, unconfirmed authenticator device; any earlier unconfirmed attempt is discarded."""
    TOTPDevice.objects.filter(user=user, confirmed=False).delete()
    device = TOTPDevice.objects.create(user=user, name="Authenticator app", confirmed=False)
    url = device.config_url
    return {
        "otpauth_url": url,
        "secret": b32encode(device.bin_key).decode().rstrip("="),
        # A data: URI, so the browser shows it as an <img> without inserting markup.
        "qr_svg": segno.make(url, error="m").svg_data_uri(scale=5, border=2),
    }


def pending_device(user):
    return TOTPDevice.objects.filter(user=user, confirmed=False).order_by("-pk").first()


def new_recovery_codes(user):
    """Replace the user's recovery codes; returns the plain codes (shown once)."""
    StaticDevice.objects.filter(user=user).delete()
    device = StaticDevice.objects.create(user=user, name="Recovery codes", confirmed=True)
    codes = [StaticToken.random_token() for _ in range(RECOVERY_CODE_COUNT)]
    StaticToken.objects.bulk_create([StaticToken(device=device, token=code) for code in codes])
    return codes


def disable(user):
    TOTPDevice.objects.filter(user=user).delete()
    StaticDevice.objects.filter(user=user).delete()
