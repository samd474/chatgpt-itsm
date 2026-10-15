from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import ValidationError

from accounts.roles import MANAGER
from helprequests import services as ticket_services
from helprequests.models import HelpRequests

from .validation import validate_answers


def approvers_for(item):
    approvers = list(item.approvers.filter(is_active=True))
    if not approvers and item.assignment_group_id:
        approvers = list(item.assignment_group.managers.filter(is_active=True))
    if not approvers:
        approvers = list(get_user_model().objects.filter(is_active=True, groups__name=MANAGER).distinct())
    return approvers


@transaction.atomic
def submit_catalog_item(item, *, requester, answers, request=None):
    if not item.active:
        raise ValidationError({"detail": "This catalog item is not available."})
    cleaned, errors = validate_answers(item.form_schema, answers)
    if errors:
        raise ValidationError({"request_payload": errors})

    help_request = ticket_services.create_help_request(
        requester=requester,
        request=request,
        request_type=HelpRequests.RequestType.REQUEST,
        subject=item.name,
        description=item.short_description,
        category=item.category,
        service=item.service,
        assignment_group=item.assignment_group,
        impact=item.default_impact,
        urgency=item.default_urgency,
        request_payload={"catalog_item": item.slug, "answers": cleaned},
    )
    if item.requires_approval:
        approvers = approvers_for(item)
        if not approvers:
            raise ValidationError({"detail": "No approver is configured for this item. Contact the service desk."})
        ticket_services.request_approvals(help_request, approvers, request=request)
    return help_request
