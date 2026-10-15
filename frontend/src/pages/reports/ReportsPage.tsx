import { useQuery } from "@tanstack/react-query";
import { getServiceDeskReport } from "../../api/operations";
import { apiErrorMessage } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { exportUrl } from "../../api/tickets";

const AGE_LABELS: Record<string, string> = {
  under_1_day: "Under 1 day",
  "1_to_3_days": "1-3 days",
  "3_to_7_days": "3-7 days",
  over_7_days: "Over 7 days",
};

function Breakdown({ title, data, labels }: { title: string; data: Record<string, number>; labels?: Record<string, string> }) {
  const max = Math.max(1, ...Object.values(data));
  return (
    <div className="panel">
      <h2>{title}</h2>
      {Object.keys(data).length === 0 && <p className="muted">No data.</p>}
      {Object.entries(data).map(([key, value]) => (
        <div className="bar-row" key={key}>
          <span>{labels?.[key] ?? key.replaceAll("_", " ")}</span>
          <div className="bar"><div className="bar-fill" style={{ width: `${(value / max) * 100}%` }} /></div>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

export function ReportsPage() {
  const query = useQuery({ queryKey: ["report", "service-desk"], queryFn: getServiceDeskReport, refetchInterval: 60_000 });
  return (
    <section>
      <div className="page-heading">
        <div><h1>Service desk overview</h1><p>Counts are calculated by the server for the tickets you can see.</p></div>
        <a className="button button--secondary" href={exportUrl({})}>Export all tickets (CSV)</a>
      </div>
      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState message={apiErrorMessage(query.error)} />}
      {query.data && <>
        <div className="metric-grid">
          <Metric label="Open tickets" value={query.data.open_tickets} />
          <Metric label="Unassigned" value={query.data.unassigned} />
          <Metric label="SLA at risk" value={query.data.sla_at_risk} />
          <Metric label="SLA breached" value={query.data.sla_breached} />
        </div>
        <div className="detail-grid">
          <Breakdown title="Open by priority" data={query.data.by_priority} />
          <Breakdown title="Open backlog by age" data={query.data.backlog_by_age} labels={AGE_LABELS} />
          <Breakdown title="All tickets by status" data={query.data.by_status} />
        </div>
      </>}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}
