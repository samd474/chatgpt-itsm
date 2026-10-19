"""Queue filters are data, so they are validated against a fixed vocabulary and turned into
explicit ORM lookups here. Users never control field names or lookup types."""
from django.db.models import Q

from accounts.roles import ADMINISTRATOR, AUDITOR, MANAGER, REQUESTER, TECHNICIAN

from .models import HelpRequests, SupportGroups

ROLE_NAMES = {REQUESTER, TECHNICIAN, MANAGER, ADMINISTRATOR, AUDITOR}


def _int_list(value, name):
    if not isinstance(value, list) or not all(isinstance(v, int) and not isinstance(v, bool) for v in value):
        raise ValueError(f"{name} must be a list of ids")
    return value


def validate_filters(filters):
    """Return a cleaned copy or raise ValueError."""
    if not isinstance(filters, dict):
        raise ValueError("filters must be an object")
    allowed = {"status", "priority", "request_type", "assignment_group", "my_groups", "technician", "category", "service", "sla"}
    unknown = set(filters) - allowed
    if unknown:
        raise ValueError(f"unknown filter keys: {', '.join(sorted(unknown))}")
    cleaned = {}
    if "status" in filters:
        statuses = filters["status"]
        if not isinstance(statuses, list) or not set(statuses) <= set(HelpRequests.RequestStatus.values):
            raise ValueError("status must be a list of ticket statuses")
        cleaned["status"] = statuses
    if "priority" in filters:
        priorities = filters["priority"]
        if not isinstance(priorities, list) or not set(priorities) <= {1, 2, 3, 4}:
            raise ValueError("priority must be a list of 1-4")
        cleaned["priority"] = priorities
    if "request_type" in filters:
        if filters["request_type"] not in HelpRequests.RequestType.values:
            raise ValueError("request_type must be incident or request")
        cleaned["request_type"] = filters["request_type"]
    for key in ("assignment_group", "category", "service"):
        if key in filters:
            cleaned[key] = _int_list(filters[key], key)
    if "my_groups" in filters:
        if not isinstance(filters["my_groups"], bool):
            raise ValueError("my_groups must be true or false")
        cleaned["my_groups"] = filters["my_groups"]
    if "technician" in filters:
        if filters["technician"] not in ("me", "unassigned"):
            raise ValueError("technician must be 'me' or 'unassigned'")
        cleaned["technician"] = filters["technician"]
    if "sla" in filters:
        if filters["sla"] not in ("breached", "at_risk"):
            raise ValueError("sla must be 'breached' or 'at_risk'")
        cleaned["sla"] = filters["sla"]
    return cleaned


def validate_roles(roles):
    if not isinstance(roles, list) or not set(roles) <= ROLE_NAMES:
        raise ValueError(f"visible_to_roles must be a list drawn from: {', '.join(sorted(ROLE_NAMES))}")
    return roles


def apply_filters(qs, filters, user):
    f = filters or {}
    if "status" in f:
        qs = qs.filter(status__in=f["status"])
    if "priority" in f:
        qs = qs.filter(priority__in=f["priority"])
    if "request_type" in f:
        qs = qs.filter(request_type=f["request_type"])
    if "assignment_group" in f:
        qs = qs.filter(assignment_group__in=f["assignment_group"])
    if f.get("my_groups"):
        qs = qs.filter(assignment_group__in=SupportGroups.objects.filter(members=user).values("pk"))
    if "category" in f:
        qs = qs.filter(category__in=f["category"])
    if "service" in f:
        qs = qs.filter(service__in=f["service"])
    if f.get("technician") == "me":
        qs = qs.filter(technician=user)
    elif f.get("technician") == "unassigned":
        qs = qs.filter(technician__isnull=True)
    if f.get("sla") == "breached":
        qs = qs.filter(Q(sla__response_breached=True) | Q(sla__resolution_breached=True))
    elif f.get("sla") == "at_risk":
        qs = qs.filter(sla__warning_sent_at__isnull=False, sla__response_breached=False, sla__resolution_breached=False)
    return qs
