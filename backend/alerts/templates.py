"""Plain-text email templates.

Requester-facing templates only ever include public information. Private notes
have no template at all, so they can never be emailed to a requester.
"""

TEMPLATES = {
    "ticket.created": (
        "[{number}] We received your request",
        "Hello {recipient_name},\n\nYour ticket {number} \"{subject}\" has been created.\n\nView it: {link}\n",
    ),
    "ticket.assigned": (
        "[{number}] Assigned to you or your group",
        "Ticket {number} \"{subject}\" (P{priority}) has been assigned.\n\nOpen it: {staff_link}\n",
    ),
    "ticket.public_comment": (
        "[{number}] New reply",
        "There is a new reply on ticket {number} \"{subject}\".\n\nRead it: {link}\n",
    ),
    "ticket.resolved": (
        "[{number}] Resolved",
        "Ticket {number} \"{subject}\" has been resolved.\n\nIf the problem is not fixed, you can reopen it: {link}\n",
    ),
    "sla.warning": (
        "[{number}] SLA warning",
        "Ticket {number} \"{subject}\" (P{priority}) is approaching its {target} target.\n\nOpen it: {staff_link}\n",
    ),
    "sla.breached": (
        "[{number}] SLA breached",
        "Ticket {number} \"{subject}\" (P{priority}) has breached its {target} target.\n\nOpen it: {staff_link}\n",
    ),
    "approval.requested": (
        "[{number}] Approval requested",
        "Your approval is requested for {number} \"{subject}\".\n\nDecide: {approvals_link}\n",
    ),
    "approval.approved": (
        "[{number}] Request approved",
        "Your request {number} \"{subject}\" was approved.\n\nView it: {link}\n",
    ),
    "approval.rejected": (
        "[{number}] Request rejected",
        "Your request {number} \"{subject}\" was rejected.\n\nView it: {link}\n",
    ),
    "contract.renewal_due": (
        "[{number}] Contract ends {end_date}",
        "Contract {number} \"{subject}\" with {vendor} ends on {end_date}.\n\nReview it: {link}\n",
    ),
    "change.approval_requested": (
        "[{number}] Change approval requested",
        "Your approval is requested for change {number} \"{subject}\" ({change_type}, {risk} risk).\n\nReview it: {link}\n",
    ),
    "change.approved": (
        "[{number}] Change approved",
        "Change {number} \"{subject}\" was approved.\n\nView it: {link}\n",
    ),
    "change.rejected": (
        "[{number}] Change rejected",
        "Change {number} \"{subject}\" was rejected.\n\nView it: {link}\n",
    ),
    "change.scheduled": (
        "[{number}] Change scheduled",
        "Change {number} \"{subject}\" is scheduled to start {planned_start}.\n\nView it: {link}\n",
    ),
    "project.task_assigned": (
        "[{number}] Task assigned to you",
        "You have been assigned \"{subject}\" in project {project}.\n\nOpen it: {link}\n",
    ),
}


# Placeholders a template may use. Anything else (including attribute or index access
# such as {number.__class__}) is rejected, so templates can't reach Python internals.
PLACEHOLDERS = {
    "number", "subject", "priority", "link", "staff_link", "approvals_link", "recipient_name", "target",
    "comment_id", "end_date", "vendor", "change_type", "risk", "planned_start", "project",
}


def template_errors(text):
    import string

    errors = []
    try:
        parsed = list(string.Formatter().parse(text))
    except ValueError as exc:
        return [f"Invalid template: {exc}"]
    for _, field, spec, conversion in parsed:
        if field is None:
            continue
        if field not in PLACEHOLDERS:
            errors.append(f"Unknown placeholder {{{field}}}. Allowed: {', '.join(sorted(PLACEHOLDERS))}")
        if spec or conversion:
            errors.append(f"Formatting options are not allowed in {{{field}}}")
    return errors


def get_template(event_type):
    """(subject, body) honouring an enabled administrator override."""
    from .models import NotificationTemplate

    override = NotificationTemplate.objects.filter(event_type=event_type, enabled=True).first()
    if override is not None:
        return override.subject, override.body
    return TEMPLATES[event_type]
