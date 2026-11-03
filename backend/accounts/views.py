from django.contrib.auth import authenticate, get_user_model, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from django_otp import login as otp_login

from core.schema import extend_schema
from reports.audit import write_audit_event

from . import two_factor


# Response/request shapes, for the OpenAPI schema the frontend's types are checked against.
class CsrfResponse(serializers.Serializer):
    csrfToken = serializers.CharField()


class LoginRequest(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class LoginResponse(serializers.Serializer):
    # When two_factor_required is true the session isn't signed in yet: POST the code to 2fa/verify/.
    id = serializers.IntegerField(required=False)
    username = serializers.CharField(required=False)
    two_factor_required = serializers.BooleanField()


class TokenRequest(serializers.Serializer):
    token = serializers.CharField(help_text="A code from the authenticator app, or an unused recovery code.")


class TwoFactorStatus(serializers.Serializer):
    enabled = serializers.BooleanField()
    required_by_role = serializers.BooleanField()  # not "required": that would shadow Field.required
    recovery_codes_left = serializers.IntegerField()


class TwoFactorSetup(serializers.Serializer):
    otpauth_url = serializers.CharField()
    secret = serializers.CharField()
    qr_svg = serializers.CharField(help_text="An SVG data: URI of the QR code.")


class RecoveryCodes(serializers.Serializer):
    recovery_codes = serializers.ListField(child=serializers.CharField())


class CurrentUser(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    name = serializers.CharField()
    groups = serializers.ListField(child=serializers.CharField())
    is_superuser = serializers.BooleanField()
    two_factor_enabled = serializers.BooleanField()
    two_factor_required = serializers.BooleanField()
    two_factor_setup_needed = serializers.BooleanField()


class LoginThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        # Rate-limit by client IP plus the submitted username.
        data = request.data if isinstance(request.data, dict) else {}
        username = str(data.get("username", "")).lower()[:150]
        return self.cache_format % {"scope": self.scope, "ident": f"{self.get_ident(request)}:{username}"}


@extend_schema(responses=CsrfResponse)
@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request):
    return Response({"csrfToken": get_token(request)})


@extend_schema(request=LoginRequest, responses=LoginResponse)
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def login_view(request):
    # DRF only enforces CSRF for already-authenticated sessions, so check it explicitly
    # here to block login CSRF.
    SessionAuthentication().enforce_csrf(request)
    data = request.data if isinstance(request.data, dict) else {}
    username = data.get("username")
    user = authenticate(request, username=username, password=data.get("password"))
    if not user or not user.is_active or not getattr(user, "is_enabled", True):
        # Never log the submitted password.
        write_audit_event(
            request,
            "auth.login_failed",
            object_type="user",
            object_id=str(username)[:80],
            actor=None,
        )
        return Response({"detail": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST)
    if two_factor.is_enabled(user):
        # Password is right, but the session isn't signed in until a code is verified.
        two_factor.start_pending_login(request, user)
        write_audit_event(request, "auth.login_password_ok", obj=user, actor=user)
        return Response({"two_factor_required": True})
    login(request, user)
    write_audit_event(request, "auth.login", obj=user, actor=user)
    return Response({"id": user.pk, "username": user.get_username(), "two_factor_required": False})


@extend_schema(request=None, responses={204: None})
@api_view(["POST"])
def logout_view(request):
    write_audit_event(request, "auth.logout", obj=request.user)
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(responses=CurrentUser)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    enabled, required = two_factor.is_enabled(user), two_factor.required_for(user)
    return Response({
        "id": user.pk,
        "username": user.get_username(),
        "name": user.get_full_name(),
        "groups": list(user.groups.values_list("name", flat=True)),
        "is_superuser": user.is_superuser,
        "two_factor_enabled": enabled,
        "two_factor_required": required,
        "two_factor_setup_needed": required and not enabled,
    })


# --- two-factor authentication ------------------------------------------------------------------

def _token(request):
    serializer = TokenRequest(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data["token"]


@extend_schema(request=TokenRequest, responses=LoginResponse)
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def two_factor_verify(request):
    """Second login step: a code (or recovery code) for the user who just passed the password step."""
    SessionAuthentication().enforce_csrf(request)
    pending = two_factor.pending_login(request)
    if pending is None:
        return Response({"detail": "Sign in with your password first."}, status=status.HTTP_400_BAD_REQUEST)
    user_id, backend = pending
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    device = two_factor.verify(user, _token(request)) if user is not None and getattr(user, "is_enabled", True) else None
    if user is None or device is None:
        write_audit_event(request, "auth.2fa_failed", object_type="user", object_id=str(user_id), actor=None)
        return Response({"detail": "That code isn't valid."}, status=status.HTTP_400_BAD_REQUEST)
    two_factor.clear_pending_login(request)
    login(request, user, backend=backend)
    otp_login(request, device)  # marks the session verified (also satisfies /admin/)
    write_audit_event(request, "auth.login", obj=user, actor=user,
                      metadata={"two_factor": "recovery_code" if device.name == "Recovery codes" else "authenticator"})
    return Response({"id": user.pk, "username": user.get_username(), "two_factor_required": False})


@extend_schema(responses=TwoFactorStatus)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def two_factor_status(request):
    user = request.user
    return Response({"enabled": two_factor.is_enabled(user), "required_by_role": two_factor.required_for(user),
                     "recovery_codes_left": two_factor.recovery_codes_left(user)})


@extend_schema(request=None, responses=TwoFactorSetup)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def two_factor_setup(request):
    """Start enrolment: a new secret to scan. Nothing changes until it's confirmed with a code."""
    if two_factor.is_enabled(request.user):
        return Response({"detail": "Two-factor authentication is already on."}, status=status.HTTP_400_BAD_REQUEST)
    return Response(two_factor.start_setup(request.user))


@extend_schema(request=TokenRequest, responses=RecoveryCodes)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([LoginThrottle])
def two_factor_confirm(request):
    """Finish enrolment with a code from the app; returns recovery codes (shown once)."""
    device = two_factor.pending_device(request.user)
    if device is None:
        return Response({"detail": "Start setup first."}, status=status.HTTP_400_BAD_REQUEST)
    if not device.verify_token(_token(request).replace(" ", "")):
        return Response({"detail": "That code isn't valid. Check the time on your phone and try again."},
                        status=status.HTTP_400_BAD_REQUEST)
    device.confirmed = True
    device.save(update_fields=["confirmed"])
    codes = two_factor.new_recovery_codes(request.user)
    otp_login(request, device)  # this session counts as verified
    write_audit_event(request, "auth.2fa_enabled", obj=request.user)
    return Response({"recovery_codes": codes})


@extend_schema(request=TokenRequest, responses=RecoveryCodes)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([LoginThrottle])
def two_factor_recovery_codes(request):
    """Replace the recovery codes; needs a current code."""
    if not two_factor.is_enabled(request.user) or two_factor.verify(request.user, _token(request)) is None:
        return Response({"detail": "That code isn't valid."}, status=status.HTTP_400_BAD_REQUEST)
    codes = two_factor.new_recovery_codes(request.user)
    write_audit_event(request, "auth.2fa_recovery_codes_replaced", obj=request.user)
    return Response({"recovery_codes": codes})


@extend_schema(request=TokenRequest, responses={204: None})
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([LoginThrottle])
def two_factor_disable(request):
    """Turn 2FA off; needs a current code, and isn't allowed for roles that require it."""
    if two_factor.required_for(request.user):
        return Response({"detail": "Your role requires two-factor authentication."}, status=status.HTTP_400_BAD_REQUEST)
    if not two_factor.is_enabled(request.user) or two_factor.verify(request.user, _token(request)) is None:
        return Response({"detail": "That code isn't valid."}, status=status.HTTP_400_BAD_REQUEST)
    two_factor.disable(request.user)
    write_audit_event(request, "auth.2fa_disabled", obj=request.user)
    return Response(status=status.HTTP_204_NO_CONTENT)
