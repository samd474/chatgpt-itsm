import django.db
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

ROLE_PERMISSIONS = {
    "Requester": ["add_ticket", "view_own_ticket", "update_own_ticket"], 
    "Technician": ["view_ticket", "update_ticket", "add_comment", "view_audit_logs"], 
    "Administrator": ["add_ticket", "change_ticket", "delete_ticket", "view_ticket"],
    "Auditor": ["view_auditevent"]
}

class Command(BaseCommand):
    def handle( self, *args, **kwargs):
        for role, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role)
            perms = Permission.objects.filter(codenames__in=codenames)
            group.permissions.set(perms)