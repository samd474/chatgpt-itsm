from django.http import JsonResponse

from . import two_factor

# Reachable before two-factor is satisfied: enough to see who you are, set 2FA up, and sign out.
ALLOWED_PREFIXES = ("/api/auth/me/", "/api/auth/csrf/", "/api/auth/logout/", "/api/auth/2fa/")
MESSAGES = {
    "two_factor_setup_required": "Your role requires two-factor authentication. Set it up to continue.",
    "two_factor_verification_required": "This session hasn't been verified with a two-factor code. Sign in again.",
}


def block_reason(user):
    """Why this signed-in user can't use the API yet, or None."""
    if two_factor.is_enabled(user):
        # Sessions started before 2FA was turned on (e.g. in another browser) never entered a code.
        return None if user.is_verified() else "two_factor_verification_required"
    return "two_factor_setup_required" if two_factor.required_for(user) else None


class TwoFactorEnforcementMiddleware:
    """Holds API requests until the session satisfies two-factor authentication.

    Runs after django-otp's OTPMiddleware (which adds user.is_verified()). Django admin is
    protected separately by OTPAdminSite.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (request.path.startswith("/api/") and not request.path.startswith(ALLOWED_PREFIXES)
                and user is not None and user.is_authenticated):
            reason = block_reason(user)
            if reason:
                return JsonResponse({"detail": MESSAGES[reason], "code": reason}, status=403)
        return self.get_response(request)
