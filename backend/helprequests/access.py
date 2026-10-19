from django.db.models import Q

from accounts.roles import ADMINISTRATOR, AUDITOR, MANAGER, TECHNICIAN, has_role, is_admin, is_staff_user


def visible_HelpRequests(user, qs):
    if user.is_superuser or has_role(user, ADMINISTRATOR, AUDITOR):
        return qs
    if has_role(user, TECHNICIAN, MANAGER):
        from .models import SupportGroups

        # A subquery rather than joining members/managers: no duplicate rows, so no DISTINCT
        # over every selected column on each list and count query.
        my_groups = SupportGroups.objects.filter(Q(members=user) | Q(managers=user)).values("pk")
        return qs.filter(Q(assignment_group__in=my_groups) | Q(technician=user) | Q(requester=user))
    return qs.filter(requester=user)


def works_ticket(user, help_request):
    """True when the user acts as staff on this ticket (may see private notes).

    A technician who raised the ticket themselves is a requester for it,
    unless they are an administrator.
    """
    if is_admin(user):
        return True
    return is_staff_user(user) and help_request.requester_id != user.pk


def can_read_private_notes(user, help_request):
    return works_ticket(user, help_request) or has_role(user, AUDITOR)
