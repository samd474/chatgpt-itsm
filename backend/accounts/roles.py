REQUESTER = "Requester"
TECHNICIAN = "Technician"
MANAGER = "Manager"
ADMINISTRATOR = "Administrator"
AUDITOR = "Auditor"

STAFF_ROLES = (TECHNICIAN, MANAGER, ADMINISTRATOR)


def has_role(user, *roles):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser and ADMINISTRATOR in roles:
        return True
    return user.groups.filter(name__in=roles).exists()


def is_staff_user(user):
    """Technicians, managers and administrators work tickets."""
    return has_role(user, *STAFF_ROLES)


def is_admin(user):
    return has_role(user, ADMINISTRATOR)
