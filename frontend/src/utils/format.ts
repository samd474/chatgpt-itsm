import type { TicketStatus } from "../types";

export function formatDate(value: string | null | undefined) {
  if (!value) return "-";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

const STATUS_LABELS: Record<TicketStatus, string> = {
  new: "New",
  assigned: "Assigned",
  in_progress: "In progress",
  pending_user_response: "Pending user response",
  resolved: "Resolved",
  closed: "Closed",
  cancelled: "Cancelled",
};

export function statusLabel(status: TicketStatus) {
  return STATUS_LABELS[status] ?? status;
}

export const LEVELS = [
  { value: 1, label: "1 - Critical" },
  { value: 2, label: "2 - High" },
  { value: 3, label: "3 - Medium" },
];

export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Mirrors helprequests.services.ALLOWED_TRANSITIONS so the UI only offers valid
// moves. Django still validates every transition.
export const ALLOWED_TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  new: ["assigned", "in_progress", "cancelled"],
  assigned: ["in_progress", "pending_user_response", "resolved", "cancelled"],
  in_progress: ["pending_user_response", "resolved", "cancelled"],
  pending_user_response: ["in_progress", "resolved", "cancelled"],
  resolved: ["closed", "in_progress"],
  closed: ["in_progress"],
  cancelled: [],
};
