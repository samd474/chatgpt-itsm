import type { TicketStatus } from "../types";
import { statusLabel } from "../utils/format";

export function StatusBadge({ status }: { status: TicketStatus }) {
  return <span className={`badge badge--status badge--${status}`}>{statusLabel(status)}</span>;
}

export function PriorityBadge({ priority }: { priority: number }) {
  return <span className={`badge badge--priority badge--p${priority}`}>P{priority}</span>;
}
