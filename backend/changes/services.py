from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.roles import ADMINISTRATOR, MANAGER, has_role
from alerts.services import notify
from reports.audit import write_audit_event

from .models import ChangeApproval, ChangeRequest

Status = ChangeRequest.Status
CAB_ROLE = "CAB"

TRANSITIONS = {
    Status.DRAFT: {Status.AWAITING_APPROVAL, Status.CANCELLED},
    Status.AWAITING_APPROVAL: {Status.CANCELLED},  # approve/reject happen through approvals
    Status.APPROVED: {Status.SCHEDULED, Status.CANCELLED},
    Status.SCHEDULED: {Status.IMPLEMENTING, Status.APPROVED, Status.CANCELLED},
    Status.IMPLEMENTING: {Status.REVIEW},
    Status.REVIEW: {Status.CLOSED},
    Status.REJECTED: {Status.DRAFT, Status.CANCELLED},
    Status.CLOSED: set(),
    Status.CANCELLED: set(),
}
# "submit" is the API word for draft -> awaiting approval.
EDITABLE_STATUSES = (Status.DRAFT, Status.REJECTED)


def is_change_manager(user):
    return has_role(user, MANAGER, ADMINISTRATOR)


def snapshot(change):
    return {f: getattr(change, f) for f in (
        "status", "change_type", "risk", "impact", "planned_start", "planned_end", "implementer_id", "outcome",
    )}


def approvers_for(change):
    users = get_user_model().objects.filter(is_active=True, is_enabled=True, groups__name=CAB_ROLE).distinct()
    if not users.exists():
        users = get_user_model().objects.filter(is_active=True, is_enabled=True, groups__name=MANAGER).distinct()
    # Nobody approves their own change.
    return list(users.exclude(pk=change.requested_by_id))


def _require_plans(change):
    missing = [label for field, label in (
        ("implementation_plan", "implementation plan"),
        ("backout_plan", "backout plan"),
        ("test_plan", "test plan"),
    ) if not getattr(change, field).strip()]
    if missing and change.change_type != ChangeRequest.Type.STANDARD:
        raise ValidationError({"detail": f"Add the {', '.join(missing)} before submitting."})


def _require_window(change):
    if not change.planned_start or not change.planned_end:
        raise ValidationError({"planned_start": "Set the planned window first."})
    if change.planned_end <= change.planned_start:
        raise ValidationError({"planned_end": "The window must end after it starts."})


def conflicts(change):
    """Other scheduled/implementing changes whose windows overlap and that touch
    the same assets or service."""
    if not change.planned_start or not change.planned_end:
        return ChangeRequest.objects.none()
    overlap = ChangeRequest.objects.filter(
        status__in=ChangeRequest.ACTIVE_WINDOW_STATUSES,
        planned_start__lt=change.planned_end,
        planned_end__gt=change.planned_start,
    ).exclude(pk=change.pk)
    shared = Q(assets__in=change.assets.all())
    if change.service_id:
        shared |= Q(service=change.service_id)
    return overlap.filter(shared).distinct()


@transaction.atomic
def transition(change, *, new_status, actor, request=None, outcome=None, closure_notes=None):
    change = ChangeRequest.objects.select_for_update().get(pk=change.pk)
    old = change.status
    if new_status not in TRANSITIONS.get(old, set()):
        raise ValidationError({"status": f"Cannot move a change from {old} to {new_status}."})

    requester = change.requested_by_id == actor.pk
    implementer = change.implementer_id == actor.pk
    manager = is_change_manager(actor)
    if new_status in (Status.AWAITING_APPROVAL, Status.DRAFT) and not (requester or manager):
        raise PermissionDenied("Only the requester or a change manager can submit this change.")
    if new_status == Status.CANCELLED and not (requester or manager):
        raise PermissionDenied("Only the requester or a change manager can cancel this change.")
    if new_status in (Status.SCHEDULED, Status.APPROVED) and old in (Status.APPROVED, Status.SCHEDULED) and not manager:
        raise PermissionDenied("Only a change manager can schedule changes.")
    if new_status in (Status.IMPLEMENTING, Status.REVIEW, Status.CLOSED) and not (implementer or manager):
        raise PermissionDenied("Only the implementer or a change manager can do this.")

    before = snapshot(change)
    now = timezone.now()
    if new_status == Status.AWAITING_APPROVAL:
        _require_plans(change)
        if change.change_type == ChangeRequest.Type.STANDARD:
            new_status = Status.APPROVED  # pre-approved
        else:
            approvers = approvers_for(change)
            if not approvers:
                raise ValidationError({"detail": "No change approvers are configured. Add people to the CAB role."})
            change.approvals.filter(state=ChangeApproval.State.PENDING).update(state=ChangeApproval.State.CANCELLED)
            for approver in approvers:
                ChangeApproval.objects.create(change=change, approver=approver)
            notify("change.approval_requested", change, recipients=approvers)
    elif new_status == Status.SCHEDULED:
        _require_window(change)
        if not change.implementer_id:
            raise ValidationError({"implementer": "Assign an implementer before scheduling."})
        clashes = list(conflicts(change).values_list("number", flat=True))
        if clashes and change.change_type != ChangeRequest.Type.EMERGENCY:
            raise ValidationError({"planned_start": f"Conflicts with {', '.join(clashes)}. Adjust the window or affected items."})
        notify("change.scheduled", change, recipients=[change.implementer, change.requested_by])
    elif new_status == Status.IMPLEMENTING:
        change.actual_start = now
    elif new_status == Status.REVIEW:
        if outcome not in ChangeRequest.Outcome.values:
            raise ValidationError({"outcome": "Record the outcome."})
        change.outcome = outcome
        change.actual_end = now
    elif new_status == Status.CLOSED:
        notes = (closure_notes if closure_notes is not None else change.closure_notes).strip()
        if not notes:
            raise ValidationError({"closure_notes": "Add closure notes from the post-implementation review."})
        change.closure_notes = notes
    elif new_status == Status.CANCELLED:
        change.approvals.filter(state=ChangeApproval.State.PENDING).update(state=ChangeApproval.State.CANCELLED)

    change.status = new_status
    change.save()
    write_audit_event(request, "change.status_changed", obj=change, actor=actor, before=before, after=snapshot(change))
    return change


@transaction.atomic
def decide(approval, *, actor, state, comment="", request=None):
    approval = ChangeApproval.objects.select_for_update().select_related("change").get(pk=approval.pk)
    if approval.approver_id != actor.pk:
        raise PermissionDenied("Only the assigned approver can decide this approval.")
    if approval.state != ChangeApproval.State.PENDING:
        raise ValidationError({"state": "This approval has already been decided."})
    if state not in (ChangeApproval.State.APPROVED, ChangeApproval.State.REJECTED):
        raise ValidationError({"state": "Choose approved or rejected."})
    change = ChangeRequest.objects.select_for_update().get(pk=approval.change_id)
    if change.status != Status.AWAITING_APPROVAL:
        raise ValidationError({"state": "This change is no longer awaiting approval."})

    approval.state = state
    approval.comment = comment
    approval.decided_at = timezone.now()
    approval.save()
    write_audit_event(request, f"change.approval_{state}", obj=change, actor=actor, metadata={"comment": comment})

    pending = change.approvals.filter(state=ChangeApproval.State.PENDING)
    if state == ChangeApproval.State.REJECTED:
        pending.update(state=ChangeApproval.State.CANCELLED)
        change.status = Status.REJECTED
    elif change.change_type == ChangeRequest.Type.EMERGENCY or not pending.exists():
        # Emergency changes need one approval (ECAB); normal changes need everyone.
        pending.update(state=ChangeApproval.State.CANCELLED)
        change.status = Status.APPROVED
    if change.status != Status.AWAITING_APPROVAL:
        change.save(update_fields=["status", "updated_at"])
        write_audit_event(request, "change.status_changed", obj=change, actor=actor,
                          before={"status": Status.AWAITING_APPROVAL}, after={"status": change.status})
        notify(f"change.{'approved' if change.status == Status.APPROVED else 'rejected'}", change, recipients=[change.requested_by])
    return approval
