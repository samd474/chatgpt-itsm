from django.db import models  # type: ignore
from django.contrib.auth.models import AbstractUser  # type: ignore
# Create your models here.

class User(AbstractUser):
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=120, blank=True)
    job_title = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.get_full_name() or self.username


