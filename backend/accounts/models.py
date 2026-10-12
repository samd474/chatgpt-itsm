from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email: models.EmailField(unique=True)#type:ignore
    department: models.CharField(max_length=120, blank=True)#type:ignore
    location: models.CharField(max_length=120, blank=True) #type: ignore
    title: models.CharField(max_length=120, blank=True) #type:ignore
    is_enabled: models.BooleanField(default=True) #type: ignore


    def __str__(self):
        return self.get_full_name() or self.username