import django.db
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

ROLE_PERMISSIONS = {
    "Requester": ["add_HelpRequests", "view_own_HelpRequests", "update_own_HelpRequests"], 
    "Technician": ["view_HelpRequests", "update_HelpRequests", "add_comment", "view_audit_logs"], 
    "Administrator": ["add_HelpRequests", "change_HelpRequests", "delete_HelpRequests", "view_HelpRequests"],
    "Auditor": ["view_auditevent"]
}

class Command(BaseCommand):
    def handle( self, *args, **kwargs):
        for role, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role)
            perms = Permission.objects.filter(codenames__in=codenames)
            group.permissions.set(perms)