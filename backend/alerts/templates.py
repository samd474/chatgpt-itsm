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
}
