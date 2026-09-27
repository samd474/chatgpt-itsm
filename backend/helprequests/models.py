from django.db import models

# Create your models here.

from django.conf import settings
from django.db import models


class PermissionGroups(models.Model):
    name = models.CharField(max_length=120, unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="support_groups", blank=True)
    managers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="managed_support_groups", blank=True)
    active = models.BooleanField(default=True)
