from django.contrib.auth.backends import ModelBackend


class EnabledUserBackend(ModelBackend):
    """Disabled accounts can't log in, and their existing sessions stop working immediately
    (Django re-checks user_can_authenticate when it loads the session user)."""

    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and getattr(user, "is_enabled", True)
