from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from reports.audit import write_audit_event


class LoginThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        # Rate-limit by client IP plus the submitted username.
        data = request.data if isinstance(request.data, dict) else {}
        username = str(data.get("username", "")).lower()[:150]
        return self.cache_format % {"scope": self.scope, "ident": f"{self.get_ident(request)}:{username}"}


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request):
    return Response({"csrfToken": get_token(request)})


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
    login(request, user)
    write_audit_event(request, "auth.login", obj=user, actor=user)
    return Response({"id": user.pk, "username": user.get_username()})


@api_view(["POST"])
def logout_view(request):
    write_audit_event(request, "auth.logout", obj=request.user)
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    return Response({
        "id": user.pk,
        "username": user.get_username(),
        "name": user.get_full_name(),
        "groups": list(user.groups.values_list("name", flat=True)),
        "is_superuser": user.is_superuser,
    })
