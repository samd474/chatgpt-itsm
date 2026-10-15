import { useMutation, useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { getServiceDeskReport } from "../../api/operations";
import { apiErrorMessage } from "../../api/client";
import { exportDownloadUrl, getExports, requestExport } from "../../api/tickets";
import { Pill } from "../../components/badges";
import { Card, DataTable, ErrorState, LoadingState, Notice, PageHeader } from "../../components/ui";
import { relativeTime } from "../../utils/format";

const AGE_LABELS: Record<string, string> = { under_1_day: "< 1 day", "1_to_3_days": "1–3 days", "3_to_7_days": "3–7 days", over_7_days: "> 7 days" };

function Breakdown({ title, data, labels }: { title: string; data: Record<string, number>; labels?: Record<string, string> }) {
  const max = Math.max(1, ...Object.values(data));
  return (
    <Card title={title}>
      {Object.keys(data).length === 0 && <p className="subtle">No data yet.</p>}
      {Object.entries(data).map(([key, value]) => (
        <div className="bar-row" key={key}>
          <span className="muted">{labels?.[key] ?? key.replaceAll("_", " ")}</span>
          <div className="bar"><i style={{ width: `${(value / max) * 100}%` }} /></div>
          <strong style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{value}</strong>
        </div>
      ))}
    </Card>
  );
}

export function ReportsPage() {
  const report = useQuery({ queryKey: ["report", "service-desk"], queryFn: getServiceDeskReport, refetchInterval: 60_000 });
  const exports = useQuery({ queryKey: ["exports"], queryFn: getExports, refetchInterval: (q) => (q.state.data?.some((j) => j.state === "queued" || j.state === "running") ? 3000 : false) });
  const exporter = useMutation({ mutationFn: () => requestExport({}), onSuccess: () => exports.refetch() });

  return (
    <>
      <PageHeader title="Reports" description="Live service desk figures for the tickets you can see."
        actions={<button className="btn btn-secondary" disabled={exporter.isPending} onClick={() => exporter.mutate()}><Download />Export all tickets</button>} />
      {report.isPending && <LoadingState />}
      {report.isError && <ErrorState message={apiErrorMessage(report.error)} />}
      {report.data && <>
        <div className="metrics">
          <div className="metric"><span>Open tickets</span><strong>{report.data.open_tickets}</strong></div>
          <div className="metric"><span>Unassigned</span><strong>{report.data.unassigned}</strong></div>
          <div className="metric"><span>SLA at risk</span><strong style={{ color: report.data.sla_at_risk ? "var(--amber)" : undefined }}>{report.data.sla_at_risk}</strong></div>
          <div className="metric"><span>SLA breached</span><strong style={{ color: report.data.sla_breached ? "var(--red)" : undefined }}>{report.data.sla_breached}</strong></div>
        </div>
        <div className="grid-2" style={{ marginBottom: 16 }}>
          <Breakdown title="Open by priority" data={report.data.by_priority} />
          <Breakdown title="Backlog age" data={report.data.backlog_by_age} labels={AGE_LABELS} />
        </div>
        <div style={{ marginBottom: 16 }}><Breakdown title="All tickets by status" data={report.data.by_status} /></div>
      </>}
      {exporter.data?.queued && <div style={{ marginBottom: 12 }}><Notice tone="success">Large export queued — it will appear below when ready.</Notice></div>}
      <Card title="Exports" flush>
        <DataTable rows={exports.data ?? []} rowKey={(j) => j.public_id}
          empty={<div className="card-body subtle">Large exports you request are prepared in the background and kept for 24 hours.</div>}
          columns={[
            { key: "c", label: "Requested", render: (j) => relativeTime(j.created_at) },
            { key: "s", label: "Status", render: (j) => <Pill value={j.state === "done" ? "completed" : j.state === "failed" ? "rejected" : "in_progress"} /> },
            { key: "r", label: "Rows", render: (j) => j.row_count || "—" },
            { key: "e", label: "Expires", render: (j) => relativeTime(j.expires_at) },
            { key: "d", label: "", render: (j) => j.state === "done" ? <a className="btn btn-secondary btn-sm" href={exportDownloadUrl(j.public_id)}><Download />Download</a> : <span className="subtle">{j.error}</span> },
          ]} />
      </Card>
    </>
  );
}
