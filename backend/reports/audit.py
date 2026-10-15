import json

from django.core.serializers.json import DjangoJSONEncoder

from config.request_context import get_request_id

_UNSET = object()


def _json_safe(value):
    if not value:
        return {}
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def write_audit_event(request, event_type, obj=None, *, object_type=None, object_id=None,
                      before=None, after=None, metadata=None, actor=_UNSET):
    """Append an AuditEvent. `request` may be None (background jobs)."""
    from .models import AuditEvent

    if actor is _UNSET:
        user = getattr(request, "user", None)
        actor = user if getattr(user, "is_authenticated", False) else None
    if obj is not None:
        object_type = object_type or obj._meta.label_lower
        object_id = object_id or str(getattr(obj, "public_id", None) or obj.pk)

    return AuditEvent.objects.create(
        initiated_by=actor,
        activity_type=event_type,
        object_type=object_type or "",
        object_id=(object_id or "")[:80],
        request_id=(getattr(request, "request_id", None) or get_request_id() or "")[:64],
        source_ip=request.META.get("REMOTE_ADDR") if request is not None else None,
        before=_json_safe(before),
        after=_json_safe(after),
        metadata=_json_safe(metadata),
    )
