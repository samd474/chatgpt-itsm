import type { SlaSummary } from "../types";
import { formatDate } from "../utils/format";

export function SlaBadge({ sla }: { sla: SlaSummary | null }) {
  if (!sla) return <span className="muted">No SLA</span>;
  if (sla.response_breached || sla.resolution_breached) return <span className="badge badge--breached">SLA breached</span>;
  if (sla.paused) return <span className="badge">SLA paused</span>;
  if (sla.warning) return <span className="badge badge--warning">SLA at risk</span>;
  return <span className="muted">Due {formatDate(sla.resolution_due_at)}</span>;
}
