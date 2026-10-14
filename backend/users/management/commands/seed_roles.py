import django.db
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

ROLE_PERMISSIONS = {
    "Requester": ["add_HelpRequest", "view_own_HelpRequest", "update_own_HelpRequest"], 
    "Technician": ["view_HelpRequest", "update_HelpRequest", "add_comment", "view_audit_logs"], 
    "Administrator": ["add_HelpRequest", "change_HelpRequest", "delete_HelpRequest", "view_HelpRequest"],
    "Auditor": ["view_auditevent"]
}

class Command(BaseCommand):
    def handle( self, *args, **kwargs):
        for role, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role)
            perms = Permission.objects.filter(codenames__in=codenames)
            group.permissions.set(perms)