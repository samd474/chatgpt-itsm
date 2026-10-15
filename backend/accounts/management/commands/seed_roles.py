from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

ROLE_PERMISSIONS = {
    "Requester": ["add_helprequests", "view_helprequests", "change_helprequests", "add_helprequestscomment"],
    "Technician": ["view_helprequests", "change_helprequests", "add_helprequestscomment", "view_auditevent"],
    "Manager": ["view_helprequests", "change_helprequests", "add_helprequestscomment", "view_auditevent"],
    "Administrator": ["add_helprequests", "change_helprequests", "delete_helprequests", "view_helprequests"],
    "Auditor": ["view_helprequests", "view_auditevent"],
}


class Command(BaseCommand):
    help = "Create the default role groups and assign their permissions."

    def handle(self, *args, **kwargs):
        for role, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role)
            perms = Permission.objects.filter(codename__in=codenames)
            missing = set(codenames) - set(perms.values_list("codename", flat=True))
            if missing:
                self.stderr.write(f"{role}: unknown permissions {sorted(missing)}")
            group.permissions.set(perms)
            self.stdout.write(f"{role}: {perms.count()} permissions")
