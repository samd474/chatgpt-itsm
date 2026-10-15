import csv
import io
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from .csv_utils import escape_cell
from .models import ExportJob


def write_csv(header, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    count = 0
    for row in rows:
        writer.writerow([escape_cell(value) for value in row])
        count += 1
    return buffer.getvalue(), count


def run_export(job):
    from helprequests.exports import EXPORT_HEADER, export_queryset, export_rows

    ExportJob.objects.filter(pk=job.pk).update(state=ExportJob.State.RUNNING)
    user = job.requested_by
    try:
        if not (user.is_active and getattr(user, "is_enabled", True) and user.has_perm("helprequests.export_helprequests")):
            raise PermissionError("export permission was revoked before the export ran")
        content, count = write_csv(EXPORT_HEADER, export_rows(export_queryset(job.requested_by, job.params)).iterator(chunk_size=2000))
        job.file.save(f"{job.public_id}.csv", ContentFile(content.encode("utf-8")), save=False)
        job.row_count = count
        job.state = ExportJob.State.DONE
    except Exception as exc:
        job.state = ExportJob.State.FAILED
        job.error = str(exc)[:255]
    job.finished_at = timezone.now()
    job.expires_at = job.finished_at + timedelta(hours=settings.EXPORT_RETENTION_HOURS)
    job.save()
    return job
