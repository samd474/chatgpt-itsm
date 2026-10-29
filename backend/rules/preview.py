"""Dry run: which recent tickets would a rule match, and what would it change on each?"""
from helprequests.models import Category, HelpRequests, Services, SupportGroups

from .engine import matches

SCAN = 200
SHOW = 25

_RELATIONS = {
    "set_assignment_group": ("assignment_group", SupportGroups),
    "set_category": ("category", Category),
    "set_service": ("service", Services),
}
_LEVELS = {"set_impact": "impact", "set_urgency": "urgency"}


def _would_change(ticket, actions, names):
    changes = []
    for key, value in actions.items():
        if key in _RELATIONS:
            field, _ = _RELATIONS[key]
            current = getattr(ticket, f"{field}_id")
            if current != value:
                changes.append({"field": field, "from": names[field].get(current), "to": names[field].get(value)})
        elif key in _LEVELS:
            field = _LEVELS[key]
            if getattr(ticket, field) != value:
                changes.append({"field": field, "from": getattr(ticket, field), "to": value})
        elif key == "notify_group":
            changes.append({"field": "notify", "from": None, "to": names["assignment_group"].get(value)})
        elif key == "add_note":
            changes.append({"field": "note", "from": None, "to": "private note"})
    return changes


def preview(conditions, actions):
    tickets = list(HelpRequests.objects.order_by("-created_at")[:SCAN])
    names = {
        "assignment_group": dict(SupportGroups.objects.values_list("pk", "name")),
        "category": dict(Category.objects.values_list("pk", "name")),
        "service": dict(Services.objects.values_list("pk", "name")),
    }
    # changed=None: history isn't stored, so a "changed" condition can't be judged here and is ignored.
    hits = [t for t in tickets if matches(conditions, t, changed=None)]
    return {
        "scanned": len(tickets),
        "matched": len(hits),
        "ignored_conditions": ["changed"] if "changed" in conditions else [],
        "tickets": [{
            "public_id": str(t.public_id), "request_number": t.request_number, "subject": t.subject,
            "status": t.status, "changes": _would_change(t, actions, names),
        } for t in hits[:SHOW]],
    }
