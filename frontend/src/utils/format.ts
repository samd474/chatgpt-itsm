import type { TicketStatus } from "../types";

export function formatDate(value: string | null | undefined) {
  if (!value) return "-";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatDay(value: string | null | undefined) {
  if (!value) return "-";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value.length === 10 ? `${value}T00:00:00` : value));
}

export function relativeTime(value: string | null | undefined) {
  if (!value) return "-";
  const diff = (new Date(value).getTime() - Date.now()) / 1000;
  const units: [Intl.RelativeTimeFormatUnit, number][] = [["year", 31536000], ["month", 2592000], ["week", 604800], ["day", 86400], ["hour", 3600], ["minute", 60]];
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  for (const [unit, seconds] of units) {
    if (Math.abs(diff) >= seconds) return rtf.format(Math.round(diff / seconds), unit);
  }
  return "just now";
}

export function formatMoney(value: string | null | undefined, currency = "USD") {
  if (value === null || value === undefined || value === "") return "-";
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(Number(value));
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

export function humanize(value: string) {
  const text = value.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function initials(name: string | null | undefined) {
  return (name || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("");
}
