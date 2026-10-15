from rest_framework.throttling import SimpleRateThrottle


class _PerUserThrottle(SimpleRateThrottle):
    """Per-user (or per-IP when anonymous) limit that only counts write requests."""

    methods = ("POST", "PUT", "PATCH", "DELETE")

    def allow_request(self, request, view):
        if self.methods and request.method not in self.methods:
            return True
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        ident = request.user.pk if request.user and request.user.is_authenticated else self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class UploadThrottle(_PerUserThrottle):
    scope = "uploads"


class ExportThrottle(_PerUserThrottle):
    scope = "exports"
    methods = ()  # exports are GETs; count every one
