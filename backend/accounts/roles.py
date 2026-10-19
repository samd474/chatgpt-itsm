REQUESTER = "Requester"
TECHNICIAN = "Technician"
MANAGER = "Manager"
ADMINISTRATOR = "Administrator"
AUDITOR = "Auditor"

STAFF_ROLES = (TECHNICIAN, MANAGER, ADMINISTRATOR)


def role_names(user):
    """The user's group names, cached on the instance like Django's own permission cache.

    Serializers and permission classes check roles once per row, so without this a
    list page of N tickets costs N extra queries.
    """
    cached = getattr(user, "_role_names_cache", None)
    if cached is None:
        cached = frozenset(user.groups.values_list("name", flat=True))
        user._role_names_cache = cached
    return cached


def has_role(user, *roles):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser and ADMINISTRATOR in roles:
        return True
    return not role_names(user).isdisjoint(roles)


def is_staff_user(user):
    """Technicians, managers and administrators work tickets."""
    return has_role(user, *STAFF_ROLES)


def is_admin(user):
    return has_role(user, ADMINISTRATOR)
