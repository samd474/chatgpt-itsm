from django.conf import settings
from django.db import models

class SupportGroups(models.Model):
    name = models.CharField(max_length=120, unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="support_groups", blank=True)
    managers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="managed_support_groups", blank=True)

class PermissionGroups(models.Model):
    name = models.CharField(max_length=120, unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="support_groups", blank=True)
    managers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="managed_support_groups", blank=True)
    active = models.BooleanField(default=True)
class Category(models.Model):
    name = models.CharField(max_length=120)
    parent = models.ForeignKey("self", null=True, Blank=True, on_delete=models.PROTECT)
    active = models.BooleanField(default=True)
class Services(models.Model): 
    name = models.CharField(max_length=160, unique=True)
    managers = models.ForeignKey(SupportGroups, null=True, blank=True, on_delete=models.SET_NULL)
    active = models.BooleanField(default=True)