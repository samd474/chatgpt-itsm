import re
import uuid

from .request_context import set_request_id

_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestIDMiddleware:
    """Accept a safe incoming X-Request-ID or generate one, and echo it back."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if _SAFE_REQUEST_ID.match(incoming) else str(uuid.uuid4())
        request.request_id = request_id
        set_request_id(request_id)
        try:
            response = self.get_response(request)
        finally:
            set_request_id(None)
        response["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware:
    """Defence-in-depth headers for API and admin responses (NGINX adds the same in production)."""

    CSP = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", self.CSP)
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if request.path.startswith("/api/"):
            # API data (tickets, notes, contracts) must not sit in shared caches.
            response.setdefault("Cache-Control", "no-store")
        return response
