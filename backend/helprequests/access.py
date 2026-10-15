from django.db.models import Q


def visible_HelpRequests(user, qs):
    if user.is_superuser or user.groups.filter(name="Administrator").exists():
        return qs
    if user.groups.filter(name="Auditor").exists():
        return qs
    if user.groups.filter(name__in=["Technician", "Manager"]).exists():
        visibility_filter = (
            Q(assignment_group__members=user)
            | Q(technician=user)
            | Q(requester=user)
        )
        return qs.filter(visibility_filter).distinct()
    return qs.filter(requester=user)
