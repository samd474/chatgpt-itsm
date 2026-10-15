from typing import TYPE_CHECKING

from django.contrib.auth.models import AbstractUser
from django.db import models

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import ManyRelatedManager

    from helprequests.models import SupportGroups


class User(AbstractUser):
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=120, blank=True)
    is_enabled = models.BooleanField(default=True)

    if TYPE_CHECKING:
        # Reverse side of SupportGroups.members (declared for the type checker only).
        support_groups: "ManyRelatedManager[SupportGroups, models.Model]"

    def __str__(self):
        return self.get_full_name() or self.username
