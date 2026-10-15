import django_filters

from .models import ChangeRequest

FINISHED = (ChangeRequest.Status.CLOSED, ChangeRequest.Status.CANCELLED, ChangeRequest.Status.REJECTED)


class ChangeFilter(django_filters.FilterSet):
    in_flight = django_filters.BooleanFilter(method="filter_in_flight")

    class Meta:
        model = ChangeRequest
        fields = ["status", "change_type", "risk", "service", "assignment_group", "implementer", "requested_by"]

    def filter_in_flight(self, queryset, name, value):
        if value is None:
            return queryset
        return queryset.exclude(status__in=FINISHED) if value else queryset.filter(status__in=FINISHED)
