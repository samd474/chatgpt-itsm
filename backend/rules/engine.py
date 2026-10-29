"""Runs ticket rules once, when a ticket is created (helprequests.services.create_help_request)."""
from alerts.services import notify
from helprequests.models import Category, HelpRequests, HelpRequestsComment, Services, SupportGroups
from helprequests.priority import calculate_priority
from reports.audit import write_audit_event

from .models import TicketRule

# action key -> (ticket field, model that must still be active)
_SET_RELATION = {
    "set_assignment_group": ("assignment_group", SupportGroups),
    "set_category": ("category", Category),
    "set_service": ("service", Services),
}
_SET_LEVEL = {"set_impact": "impact", "set_urgency": "urgency"}


def matches(conditions, help_request):
    """Every given condition must hold; keywords match if any phrase appears in the subject or description."""
    c = conditions or {}
    if "request_type" in c and help_request.request_type != c["request_type"]:
        return False
    for key in ("category", "service"):
        if key in c and getattr(help_request, f"{key}_id") not in c[key]:
            return False
    for key in ("impact", "urgency"):
        if key in c and getattr(help_request, key) not in c[key]:
            return False
    if "keywords" in c:
        text = f"{help_request.subject}\n{help_request.description}".casefold()
        if not any(word.casefold() in text for word in c["keywords"]):
            return False
    return True


def apply_rules(help_request: HelpRequests, *, request=None):
    """Apply matching active rules in order. Later rules see earlier rules' changes. Returns matched rule ids."""
    changed, followups, matched = set(), [], []
    for rule in TicketRule.objects.filter(active=True):
        if not matches(rule.conditions, help_request):
            continue
        applied, skipped = {}, {}
        for key, value in rule.actions.items():
            if key in _SET_RELATION:
                field, model = _SET_RELATION[key]
                target = model.objects.filter(pk=value, active=True).first()
                if target is None:
                    skipped[key] = "target is missing or inactive"
                    continue
                setattr(help_request, field, target)
                changed.add(field)
            elif key in _SET_LEVEL:
                setattr(help_request, _SET_LEVEL[key], value)
                changed.add(_SET_LEVEL[key])
            elif key == "notify_group":
                group = SupportGroups.objects.filter(pk=value, active=True).first()
                if group is None:
                    skipped[key] = "group is missing or inactive"
                    continue
                followups.append(("notify", rule, group))
            elif key == "add_note":
                followups.append(("note", rule, value))
            applied[key] = value
        matched.append(rule.pk)
        write_audit_event(request, "rule.applied", obj=help_request, actor=None,
                          metadata={"rule_id": rule.pk, "rule": rule.name, "applied": applied, "skipped": skipped})
        if rule.stop_processing:
            break

    if changed:
        help_request.priority = calculate_priority(help_request.impact, help_request.urgency)
        help_request.save(update_fields=[*changed, "priority", "updated_at"])
    for kind, rule, value in followups:
        if kind == "note":
            # No author: the conversation shows it as added by automation. Private, so requesters never see it.
            HelpRequestsComment.objects.create(help_request=help_request, author=None, body=value,
                                               visibility=HelpRequestsComment.Visibility.PRIVATE)
        else:
            notify("ticket.rule_matched", help_request, recipients=list(value.members.filter(is_active=True)),
                   payload={"rule": rule.name})
    return matched
