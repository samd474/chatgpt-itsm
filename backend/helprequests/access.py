from django.db.models import Q

def visible_HelpRequest(user, qs):
    if user.is_superuser or user.groups.filter(name="Administrator").exists():
        return qs
    if user.groups.filter(name="Auditor").exists():
        return qs
    if user.groups.filter(name__in=["Technician", "Manager"]).exists():
        visibility_filter = Q(
            Q(assignment_group_member=user),
            Q(assignee=user),
            Q(requester=user),
            _connector=Q.OR,
        )
        return qs.filter(visibility_filter).distinct()
    return qs.filter(requester=user)
    