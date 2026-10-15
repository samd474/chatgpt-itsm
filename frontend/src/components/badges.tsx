import type { ChangeStatus, SlaSummary, TicketStatus } from "../types";
import { formatDate, humanize, relativeTime, statusLabel } from "../utils/format";
import { Badge, type Tone } from "./ui";

const TICKET_TONES: Record<TicketStatus, Tone> = {
  new: "blue", assigned: "violet", in_progress: "accent", pending_user_response: "amber",
  resolved: "green", closed: "gray", cancelled: "gray",
};

export function StatusBadge({ status }: { status: TicketStatus }) {
  return <Badge tone={TICKET_TONES[status]} dot>{statusLabel(status)}</Badge>;
}

export function PriorityBadge({ priority }: { priority: number }) {
  return <span className={`priority p${priority}`} title={`Priority ${priority}`}><span className="bars"><i /><i /><i /></span>P{priority}</span>;
}

export function SlaBadge({ sla, compact }: { sla: SlaSummary | null; compact?: boolean }) {
  if (!sla) return <span className="subtle">—</span>;
  if (sla.response_breached || sla.resolution_breached) return <Badge tone="red" dot>Breached</Badge>;
  if (sla.paused) return <Badge tone="gray" dot>Paused</Badge>;
  if (sla.warning) return <Badge tone="amber" dot>At risk</Badge>;
  return <span className="subtle" title={formatDate(sla.resolution_due_at)}>Due {compact ? relativeTime(sla.resolution_due_at) : formatDate(sla.resolution_due_at)}</span>;
}

const CHANGE_TONES: Record<ChangeStatus, Tone> = {
  draft: "gray", awaiting_approval: "amber", approved: "blue", scheduled: "violet", implementing: "accent",
  review: "amber", closed: "green", rejected: "red", cancelled: "gray",
};

export function ChangeStatusBadge({ status }: { status: ChangeStatus }) {
  return <Badge tone={CHANGE_TONES[status]} dot>{humanize(status)}</Badge>;
}

const GENERIC: Record<string, Tone> = {
  active: "green", in_use: "green", done: "green", approved: "green", completed: "green",
  in_stock: "blue", todo: "gray", proposed: "blue", draft: "gray",
  in_progress: "accent", in_repair: "amber", on_hold: "amber", blocked: "red", pending: "amber",
  expired: "red", terminated: "gray", retired: "gray", disposed: "gray", lost: "red", cancelled: "gray", rejected: "red",
  open: "blue", low: "green", medium: "amber", high: "red",
};

export function Pill({ value }: { value: string }) {
  return <Badge tone={GENERIC[value] ?? "gray"} dot>{humanize(value)}</Badge>;
}
