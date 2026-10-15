from django.http import QueryDict

from .access import visible_HelpRequests
from .filters import HelpRequestsFilter
from .models import HelpRequests

EXPORT_COLUMNS = [
    ("request_number", "Number"),
    ("request_type", "Type"),
    ("subject", "Subject"),
    ("status", "Status"),
    ("priority", "Priority"),
    ("impact", "Impact"),
    ("urgency", "Urgency"),
    ("requester__username", "Requester"),
    ("technician__username", "Technician"),
    ("assignment_group__name", "Assignment group"),
    ("category__name", "Category"),
    ("service__name", "Service"),
    ("created_at", "Created"),
    ("resolved_at", "Resolved"),
    ("closed_at", "Closed"),
]
ORDERINGS = {"created_at", "-created_at", "updated_at", "-updated_at", "priority", "-priority"}


def export_queryset(user, params):
    """Same scope and filters as the list API, rebuilt from plain params (used by background jobs)."""
    data = QueryDict(mutable=True)
    for key, value in (params or {}).items():
        data[key] = value
    qs = visible_HelpRequests(user, HelpRequests.objects.all())
    qs = HelpRequestsFilter(data, queryset=qs).qs
    ordering = data.get("ordering")
    return qs.order_by(ordering if ordering in ORDERINGS else "-created_at")


def export_rows(queryset):
    return queryset.values_list(*[column for column, _ in EXPORT_COLUMNS])


EXPORT_HEADER = [label for _, label in EXPORT_COLUMNS]
