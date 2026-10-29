import pytest
from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APIClient

from accounts.models import User
from helprequests.models import SupportGroups


@pytest.fixture(autouse=True)
def _isolate(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    # The production hasher is deliberately slow (~0.6s per user); tests create many users.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    cache.clear()


@pytest.fixture
def make_user(db):
    def _make(username, *roles, **extra):
        user = User.objects.create_user(username=username, email=f"{username}@example.test", password="pw-123456!", **extra)
        for role in roles:
            user.groups.add(Group.objects.get_or_create(name=role)[0])
        return user
    return _make


@pytest.fixture
def client_for():
    def _client(user):
        client = APIClient()
        client.force_authenticate(user)
        return client
    return _client


@pytest.fixture
def network_team(db):
    return SupportGroups.objects.create(name="Network")
