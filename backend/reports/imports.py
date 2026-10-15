import csv
import io

from django.db import transaction
from django.utils import timezone

from helprequests.models import Category, Services, SupportGroups

from .audit import write_audit_event
from .models import ImportJob

MAX_ROWS = 5000

# Expected header for each import kind.
COLUMNS = {
    ImportJob.Kind.CATEGORIES: ["name", "parent", "active"],
    ImportJob.Kind.SERVICES: ["name", "owner_group", "active"],
}


def _parse_bool(value):
    value = (value or "").strip().lower()
    if value in ("", "1", "true", "yes", "y"):
        return True
    if value in ("0", "false", "no", "n"):
        return False
    raise ValueError("active must be true or false")


def validate(kind, content):
    """Parse without touching production rows. Returns a preview dict."""
    reader = csv.DictReader(io.StringIO(content))
    expected = COLUMNS[kind]
    header = [h.strip().lower() for h in (reader.fieldnames or [])]
    if header[: len(expected)] != expected:
        return {"valid": [], "errors": [{"row": 1, "error": f"Header must be: {','.join(expected)}"}], "warnings": []}

    valid, errors, warnings, seen = [], [], [], set()
    for line, raw in enumerate(reader, start=2):
        if line - 1 > MAX_ROWS:
            errors.append({"row": line, "error": f"Imports are limited to {MAX_ROWS} rows."})
            break
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}
        try:
            name = row["name"]
            if not name:
                raise ValueError("name is required")
            active = _parse_bool(row.get("active"))
            if kind == ImportJob.Kind.CATEGORIES:
                parent = row.get("parent", "")
                if parent and parent not in seen and not Category.objects.filter(name=parent).exists():
                    raise ValueError(f"parent '{parent}' does not exist")
                if Category.objects.filter(name=name).exists():
                    warnings.append({"row": line, "warning": f"'{name}' already exists and will be updated"})
                valid.append({"row": line, "name": name, "parent": parent, "active": active})
            else:
                group = row.get("owner_group", "")
                if group and not SupportGroups.objects.filter(name=group).exists():
                    raise ValueError(f"support group '{group}' does not exist")
                if Services.objects.filter(name=name).exists():
                    warnings.append({"row": line, "warning": f"'{name}' already exists and will be updated"})
                valid.append({"row": line, "name": name, "owner_group": group, "active": active})
            if name in seen:
                warnings.append({"row": line, "warning": f"'{name}' appears more than once; the last row wins"})
            seen.add(name)
        except (ValueError, KeyError) as exc:
            errors.append({"row": line, "error": str(exc)})
    return {"valid": valid, "errors": errors, "warnings": warnings}


@transaction.atomic
def apply(job, *, actor, request=None):
    created = updated = 0
    for row in job.preview.get("valid", []):
        if job.kind == ImportJob.Kind.CATEGORIES:
            parent = Category.objects.filter(name=row["parent"]).first() if row["parent"] else None
            _, was_created = Category.objects.update_or_create(
                name=row["name"], defaults={"parent": parent, "active": row["active"]},
            )
        else:
            group = SupportGroups.objects.filter(name=row["owner_group"]).first() if row["owner_group"] else None
            _, was_created = Services.objects.update_or_create(
                name=row["name"], defaults={"managers": group, "active": row["active"]},
            )
        created += was_created
        updated += not was_created

    job.state = ImportJob.State.APPLIED
    job.confirmed_by = actor
    job.applied_at = timezone.now()
    job.result = {"created": created, "updated": updated, "skipped_errors": len(job.preview.get("errors", []))}
    job.save()
    write_audit_event(request, "import.applied", obj=job, actor=actor, metadata={"kind": job.kind, **job.result})
    return job
