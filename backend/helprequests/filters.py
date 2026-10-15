import django_filters
from django.db.models import Q

from .models import HelpRequests


class HelpRequestsFilter(django_filters.FilterSet):
    """Shared by the list endpoint and background exports so both apply identical filters."""

    search = django_filters.CharFilter(method="filter_search")
    open = django_filters.BooleanFilter(method="filter_open")

    class Meta:
        model = HelpRequests
        fields = ["request_type", "status", "priority", "impact", "urgency", "technician",
                  "assignment_group", "category", "service"]

    def filter_search(self, queryset, name, value):
        value = value.strip()[:200]
        if not value:
            return queryset
        return queryset.filter(
            Q(request_number__icontains=value) | Q(subject__icontains=value) | Q(description__icontains=value)
        )

    def filter_open(self, queryset, name, value):
        if value is None:
            return queryset
        if value:
            return queryset.filter(status__in=HelpRequests.OPEN_STATUSES)
        return queryset.exclude(status__in=HelpRequests.OPEN_STATUSES)
