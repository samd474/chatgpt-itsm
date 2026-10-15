from rest_framework.exceptions import ValidationError

from catalog.validation import validate_answers

from .models import CustomFieldDefinition


def definitions(entity, *, for_requester=False):
    qs = CustomFieldDefinition.objects.filter(entity=entity, active=True)
    if for_requester:
        qs = qs.filter(visible_to_requester=True)
    return list(qs)


def clean_custom_fields(entity, values, *, existing=None, for_requester=False):
    """Validate submitted custom field values against the active definitions.

    Values for fields the caller may not edit are kept from `existing`, so a
    requester can never overwrite staff-only fields.
    """
    defs = definitions(entity, for_requester=for_requester)
    schema = [d.as_schema() for d in defs]
    cleaned, errors = validate_answers(schema, values or {})
    if errors:
        raise ValidationError({"custom_fields": errors})
    merged = dict(existing or {})
    allowed = {d.key for d in defs}
    for key in allowed:
        merged.pop(key, None)
    merged.update(cleaned)
    return merged


def filter_for_requester(values):
    hidden = set(CustomFieldDefinition.objects.filter(entity=CustomFieldDefinition.Entity.TICKET, visible_to_requester=False)
                 .values_list("key", flat=True))
    return {k: v for k, v in (values or {}).items() if k not in hidden}
