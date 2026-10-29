"""Rule conditions and actions are data, checked against a fixed vocabulary (like queue filters).
Administrators never supply field names, lookups or code."""
from helprequests.models import Category, HelpRequests, Services, SupportGroups

LEVELS = set(HelpRequests.Level.values)
MAX_KEYWORDS = 20
MAX_NOTE = 2000


def _ids(value, name, model):
    if not isinstance(value, list) or not value or not all(isinstance(v, int) and not isinstance(v, bool) for v in value):
        raise ValueError(f"{name} must be a non-empty list of ids")
    missing = set(value) - set(model.objects.filter(pk__in=value).values_list("pk", flat=True))
    if missing:
        raise ValueError(f"{name}: unknown ids {sorted(missing)}")
    return value


def _id(value, name, model):
    if not isinstance(value, int) or isinstance(value, bool) or not model.objects.filter(pk=value).exists():
        raise ValueError(f"{name} must be the id of an existing {model._meta.verbose_name}")
    return value


def _levels(value, name):
    if not isinstance(value, list) or not value or not set(value) <= LEVELS:
        raise ValueError(f"{name} must be a non-empty list drawn from {sorted(LEVELS)}")
    return value


def validate_conditions(conditions):
    """Every condition given must match (AND); an empty object matches every new ticket."""
    if not isinstance(conditions, dict):
        raise ValueError("conditions must be an object")
    allowed = {"request_type", "category", "service", "impact", "urgency", "keywords"}
    unknown = set(conditions) - allowed
    if unknown:
        raise ValueError(f"unknown condition keys: {', '.join(sorted(unknown))}")
    cleaned = {}
    if "request_type" in conditions:
        if conditions["request_type"] not in HelpRequests.RequestType.values:
            raise ValueError("request_type must be incident or request")
        cleaned["request_type"] = conditions["request_type"]
    if "category" in conditions:
        cleaned["category"] = _ids(conditions["category"], "category", Category)
    if "service" in conditions:
        cleaned["service"] = _ids(conditions["service"], "service", Services)
    for key in ("impact", "urgency"):
        if key in conditions:
            cleaned[key] = _levels(conditions[key], key)
    if "keywords" in conditions:
        words = conditions["keywords"]
        if (not isinstance(words, list) or not words or len(words) > MAX_KEYWORDS
                or not all(isinstance(w, str) and 0 < len(w.strip()) <= 100 for w in words)):
            raise ValueError(f"keywords must be 1-{MAX_KEYWORDS} non-empty phrases of up to 100 characters")
        cleaned["keywords"] = [w.strip() for w in words]
    return cleaned


def validate_actions(actions):
    if not isinstance(actions, dict) or not actions:
        raise ValueError("a rule needs at least one action")
    allowed = {"set_assignment_group", "set_category", "set_service", "set_impact", "set_urgency", "notify_group", "add_note"}
    unknown = set(actions) - allowed
    if unknown:
        raise ValueError(f"unknown action keys: {', '.join(sorted(unknown))}")
    cleaned = {}
    for key in ("set_assignment_group", "notify_group"):
        if key in actions:
            cleaned[key] = _id(actions[key], key, SupportGroups)
    if "set_category" in actions:
        cleaned["set_category"] = _id(actions["set_category"], "set_category", Category)
    if "set_service" in actions:
        cleaned["set_service"] = _id(actions["set_service"], "set_service", Services)
    for key in ("set_impact", "set_urgency"):
        if key in actions:
            if actions[key] not in LEVELS:
                raise ValueError(f"{key} must be one of {sorted(LEVELS)}")
            cleaned[key] = actions[key]
    if "add_note" in actions:
        note = actions["add_note"]
        if not isinstance(note, str) or not note.strip() or len(note) > MAX_NOTE:
            raise ValueError(f"add_note must be 1-{MAX_NOTE} characters")
        cleaned["add_note"] = note.strip()
    return cleaned
