from django.db.models import Q

def visible_tickets(user, qs):
    if user.is_superuser or user.groups.filter(name="Administrator").exists():
        return qs
    if user.groups.filter(name="Auditor").exists():
        return qs
    if user.groups.filter(name__in=["Technician", "Manager"]).exists():
        return qs.filter(
            Q(assignment_group_member=user) |
            Q(assignee=user) |
            Q(requester=user)
        ).distinct()
    return qs.filter(requester=user)
    