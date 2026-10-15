from celery import shared_task
from django.utils import timezone

from .exporting import run_export
from .models import ExportJob


@shared_task
def generate_export(job_id):
    job = ExportJob.objects.select_related("requested_by").filter(pk=job_id, state=ExportJob.State.QUEUED).first()
    if job is not None:  # already handled by an earlier delivery of this message
        run_export(job)


@shared_task
def delete_expired_exports():
    expired = ExportJob.objects.filter(expires_at__lt=timezone.now())
    count = 0
    for job in expired:
        if job.file:
            job.file.delete(save=False)
        job.delete()
        count += 1
    return count
