"""Canonical ticket operations.

The API, admin actions, catalog submissions and background jobs all go through
these functions so timestamps, SLA state, audit events and notifications stay
consistent.
"""
import hashlib
import mimetypes
import os

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.roles import STAFF_ROLES, has_role
from alerts.services import notify
from reports.audit import write_audit_event
from slas import services as sla_services

from .access import works_ticket
from .models import Approval, Attachment, HelpRequests, HelpRequestsComment
from .priority import calculate_priority

Status = HelpRequests.RequestStatus

ALLOWED_TRANSITIONS = {
    Status.NEW: {Status.ASSIGNED, Status.IN_PROGRESS, Status.CANCELLED},
    Status.ASSIGNED: {Status.IN_PROGRESS, Status.PENDING_USER_RESPONSE, Status.RESOLVED, Status.CANCELLED},
    Status.IN_PROGRESS: {Status.PENDING_USER_RESPONSE, Status.RESOLVED, Status.CANCELLED},
    Status.PENDING_USER_RESPONSE: {Status.IN_PROGRESS, Status.RESOLVED, Status.CANCELLED},
    Status.RESOLVED: {Status.CLOSED, Status.IN_PROGRESS},
    Status.CLOSED: {Status.IN_PROGRESS},
    Status.CANCELLED: set(),
}

# What a requester may do to their own ticket without staff involvement.
REQUESTER_TRANSITIONS = {
    (Status.NEW, Status.CANCELLED),
    (Status.RESOLVED, Status.CLOSED),
    (Status.RESOLVED, Status.IN_PROGRESS),
}

SNAPSHOT_FIELDS = (
    "request_number", "request_type", "subject", "status", "impact", "urgency", "priority",
    "requester_id", "technician_id", "assignment_group_id", "category_id", "service_id",
    "resolution_code", "resolution_body", "first_response_time", "resolved_at", "closed_at",
)


def snapshot(help_request):
    return {field: getattr(help_request, field) for field in SNAPSHOT_FIELDS}


def _group_recipients(help_request):
    if help_request.technician_id:
        return [help_request.technician]
    if help_request.assignment_group_id:
        return list(help_request.assignment_group.members.filter(is_active=True))
    return []


def assign_request_number(help_request):
    prefix = "INC" if help_request.request_type == HelpRequests.RequestType.INCIDENT else "REQ"
    help_request.request_number = f"{prefix}-{help_request.pk:06d}"
    help_request.save(update_fields=["request_number"])


@transaction.atomic
def create_help_request(*, requester, request=None, **data):
    impact = data.pop("impact", HelpRequests.Level.MEDIUM)
    urgency = data.pop("urgency", HelpRequests.Level.MEDIUM)
    help_request = HelpRequests.objects.create(
        requester=requester,
        impact=impact,
        urgency=urgency,
        priority=calculate_priority(impact, urgency),
        **data,
    )
    assign_request_number(help_request)
    sla_services.attach_sla(help_request)
    write_audit_event(request, "ticket.created", obj=help_request, actor=requester, before={}, after=snapshot(help_request))
    notify("ticket.created", help_request, recipients=[requester])
    if help_request.assignment_group_id or help_request.technician_id:
        notify("ticket.assigned", help_request, recipients=_group_recipients(help_request))
    return help_request


@transaction.atomic
def update_help_request(help_request, *, actor, changes, request=None):
    help_request = HelpRequests.objects.select_for_update().get(pk=help_request.pk)
    before = snapshot(help_request)

    technician = changes.get("technician", help_request.technician)
    group = changes.get("assignment_group", help_request.assignment_group)
    if technician is not None and "technician" in changes:
        if not has_role(technician, *STAFF_ROLES):
            raise ValidationError({"technician": "Only technicians, managers or administrators can be assigned."})
        if group is not None and not group.members.filter(pk=technician.pk).exists():
            raise ValidationError({"technician": "The technician is not a member of the assignment group."})

    for field, value in changes.items():
        setattr(help_request, field, value)
    help_request.priority = calculate_priority(help_request.impact, help_request.urgency)

    # Assigning someone to a brand-new ticket moves it into the assigned state.
    if help_request.status == Status.NEW and (help_request.technician_id or help_request.assignment_group_id):
        help_request.status = Status.ASSIGNED

    help_request.save()
    after = snapshot(help_request)

    if before["priority"] != after["priority"]:
        sla_services.reapply_sla(help_request)
        write_audit_event(request, "ticket.priority_changed", obj=help_request, actor=actor,
                          before={"priority": before["priority"]}, after={"priority": after["priority"]})
    if (before["technician_id"], before["assignment_group_id"]) != (after["technician_id"], after["assignment_group_id"]):
        write_audit_event(request, "ticket.assigned", obj=help_request, actor=actor,
                          before={k: before[k] for k in ("technician_id", "assignment_group_id")},
                          after={k: after[k] for k in ("technician_id", "assignment_group_id")})
        notify("ticket.assigned", help_request, recipients=_group_recipients(help_request))
    write_audit_event(request, "ticket.updated", obj=help_request, actor=actor, before=before, after=after)
    return help_request


@transaction.atomic
def transition_help_request(help_request, *, new_status, actor, reason="", resolution_code=None,
                            resolution_body=None, request=None):
    help_request = HelpRequests.objects.select_for_update().get(pk=help_request.pk)
    old_status = help_request.status

    if new_status not in Status.values:
        raise ValidationError({"status": "Unknown status."})
    if new_status not in ALLOWED_TRANSITIONS[old_status]:
        raise ValidationError({"status": f"Cannot move a ticket from {old_status} to {new_status}."})
    if not works_ticket(actor, help_request):
        if help_request.requester_id != actor.pk or (old_status, new_status) not in REQUESTER_TRANSITIONS:
            raise PermissionDenied("You cannot make this status change.")

    before = snapshot(help_request)
    if resolution_code is not None:
        help_request.resolution_code = resolution_code
    if resolution_body is not None:
        help_request.resolution_body = resolution_body

    if new_status in (Status.RESOLVED, Status.CLOSED) and not help_request.resolution_body.strip():
        raise ValidationError({"resolution_body": "Required when resolving or closing."})
    if new_status == Status.ASSIGNED and not (help_request.technician_id or help_request.assignment_group_id):
        raise ValidationError({"status": "Set a technician or assignment group before assigning."})

    now = timezone.now()
    if new_status == Status.RESOLVED:
        help_request.resolved_at = now
    elif new_status == Status.CLOSED:
        help_request.closed_at = now
        help_request.resolved_at = help_request.resolved_at or now
    elif new_status == Status.IN_PROGRESS and old_status in (Status.RESOLVED, Status.CLOSED):
        # Reopen.
        help_request.resolved_at = None
        help_request.closed_at = None

    help_request.status = new_status
    help_request.save()
    sla_services.on_status_change(help_request, old_status, new_status, actor=actor, request=request)

    event = "ticket.reopened" if old_status in (Status.RESOLVED, Status.CLOSED) else "ticket.status_changed"
    write_audit_event(request, event, obj=help_request, actor=actor, before=before, after=snapshot(help_request),
                      metadata={"reason": reason} if reason else None)
    if new_status == Status.RESOLVED:
        notify("ticket.resolved", help_request, recipients=[help_request.requester])
    return help_request


@transaction.atomic
def add_comment(help_request, *, author, body, visibility, request=None):
    body = (body or "").strip()
    if not body:
        raise ValidationError({"body": "Comment text is required."})
    staff = works_ticket(author, help_request)
    if visibility == HelpRequestsComment.Visibility.PRIVATE and not staff:
        raise PermissionDenied("Only staff working this ticket can add private notes.")

    comment = HelpRequestsComment.objects.create(
        help_request=help_request, author=author, body=body, visibility=visibility,
    )
    public = visibility == HelpRequestsComment.Visibility.PUBLIC

    if public and staff and help_request.first_response_time is None:
        help_request.first_response_time = comment.created_at
        help_request.save(update_fields=["first_response_time", "updated_at"])
        sla_services.on_first_response(help_request)

    event = "ticket.public_comment" if public else "ticket.private_note"
    write_audit_event(request, event, obj=help_request, actor=author,
                      metadata={"comment_id": comment.pk, "visibility": visibility})
    if public:
        if author.pk == help_request.requester_id:
            notify("ticket.public_comment", help_request, recipients=_group_recipients(help_request),
                   payload={"comment_id": comment.pk})
        else:
            notify("ticket.public_comment", help_request, recipients=[help_request.requester],
                   payload={"comment_id": comment.pk})
    # Private notes never use requester-facing notifications.
    return comment


def scan_file(uploaded_file):
    """Malware-scanning hook. Replace with a real scanner (e.g. ClamAV) before production."""
    return True


def _sniff_content_type(uploaded_file, filename):
    try:
        import magic

        head = uploaded_file.read(2048)
        uploaded_file.seek(0)
        return magic.from_buffer(head, mime=True)
    except Exception:
        return mimetypes.guess_type(filename)[0] or "application/octet-stream"


@transaction.atomic
def add_attachment(help_request, *, uploaded_by, uploaded_file, comment=None, request=None):
    filename = os.path.basename(uploaded_file.name or "upload")
    extension = os.path.splitext(filename)[1].lower()
    if extension in settings.ATTACHMENT_BLOCKED_EXTENSIONS:
        raise ValidationError({"file": f"Files of type {extension} are not allowed."})
    if uploaded_file.size > settings.ATTACHMENT_MAX_BYTES:
        raise ValidationError({"file": f"Files must be {settings.ATTACHMENT_MAX_BYTES // (1024 * 1024)} MB or smaller."})

    content_type = _sniff_content_type(uploaded_file, filename)
    if content_type in ("application/x-dosexec", "application/x-msdownload", "application/x-executable"):
        raise ValidationError({"file": "Executable content is not allowed."})

    digest = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(0)

    if not scan_file(uploaded_file):
        raise ValidationError({"file": "The file failed the malware scan."})

    attachment = Attachment.objects.create(
        help_request=help_request,
        comment=comment,
        uploaded_by=uploaded_by,
        file=uploaded_file,
        original_name=filename[:255],
        size_bytes=uploaded_file.size,
        content_type=content_type[:120],
        sha256=digest.hexdigest(),
    )
    write_audit_event(request, "attachment.uploaded", obj=help_request, actor=uploaded_by,
                      metadata={"attachment_id": attachment.pk, "name": attachment.original_name,
                                "sha256": attachment.sha256, "size_bytes": attachment.size_bytes})
    return attachment


def request_approvals(help_request, approvers, *, request=None):
    approvals = []
    for approver in {a.pk: a for a in approvers}.values():
        approvals.append(Approval.objects.create(help_request=help_request, approver=approver))
    if approvals:
        write_audit_event(request, "approval.requested", obj=help_request, actor=None,
                          metadata={"approver_ids": [a.approver.pk for a in approvals]})
        notify("approval.requested", help_request, recipients=[a.approver for a in approvals])
    return approvals


@transaction.atomic
def decide_approval(approval, *, actor, state, comment="", request=None):
    approval = Approval.objects.select_for_update().select_related("help_request").get(pk=approval.pk)
    if approval.approver.pk != actor.pk:
        raise PermissionDenied("Only the assigned approver can decide this approval.")
    if approval.state != Approval.State.PENDING:
        raise ValidationError({"state": "This approval has already been decided."})
    if state not in (Approval.State.APPROVED, Approval.State.REJECTED):
        raise ValidationError({"state": "Choose approved or rejected."})

    approval.state = state
    approval.comment = comment
    approval.decided_at = timezone.now()
    approval.save()

    help_request = approval.help_request
    # Phase 1 rule: the first decision wins; other pending approvals are cancelled.
    Approval.objects.filter(help_request=help_request, state=Approval.State.PENDING).update(
        state=Approval.State.CANCELLED, decided_at=approval.decided_at,
    )
    write_audit_event(request, f"approval.{state}", obj=help_request, actor=actor,
                      metadata={"approval_id": approval.pk, "comment": comment})
    if state == Approval.State.REJECTED and help_request.status in ALLOWED_TRANSITIONS and \
            Status.CANCELLED in ALLOWED_TRANSITIONS[help_request.status]:
        help_request.status = Status.CANCELLED
        help_request.save(update_fields=["status", "updated_at"])
        write_audit_event(request, "ticket.status_changed", obj=help_request, actor=actor,
                          metadata={"reason": "Approval rejected"})
    notify(f"approval.{state}", help_request, recipients=[help_request.requester])
    return approval
