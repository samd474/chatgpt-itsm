import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, Clock, OctagonAlert } from "lucide-react";
import { useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiErrorMessage } from "../../api/client";
import { getSlaReport, type SlaAttention, type SlaBreakdown, type SlaPeriodDays, type SlaTrendDay } from "../../api/operations";
import { getSupportGroups } from "../../api/tickets";
import { PriorityBadge } from "../../components/badges";
import { Badge, Card, DataTable, ErrorState, LoadingState, PageHeader, Tabs } from "../../components/ui";
import { formatDate, formatDay, relativeTime } from "../../utils/format";

const PERIODS: { value: `${SlaPeriodDays}`; label: string }[] = [
  { value: "7", label: "Last 7 days" }, { value: "30", label: "Last 30 days" }, { value: "90", label: "Last 90 days" },
];

const percent = (value: number | null) => (value === null ? "—" : `${value.toFixed(value % 1 === 0 ? 0 : 1)}%`);

function StateBadge({ row }: { row: SlaAttention }) {
  return row.state === "breached"
    ? <Badge tone="red"><OctagonAlert size={12} aria-hidden />Breached</Badge>
    : <Badge tone="amber"><AlertTriangle size={12} aria-hidden />At risk</Badge>;
}

function dueText(row: SlaAttention) {
  const when = relativeTime(row.due_at);
  const target = row.target === "response" ? "Response" : "Resolution";
  if (row.paused) return `${target} due ${when} (paused)`;
  return new Date(row.due_at).getTime() <= Date.now() ? `${target} was due ${when}` : `${target} due ${when}`;
}

/** Met / breached resolutions per day: stacked columns, one baseline, hover + keyboard readout. */
function TrendChart({ days }: { days: SlaTrendDay[] }) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [active, setActive] = useState<number | null>(null);
  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(240, Math.floor(entry.contentRect.width))));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const height = 200, left = 36, right = 8, top = 8, bottom = 24;
  const plotW = width - left - right, plotH = height - top - bottom;
  const peak = Math.max(1, ...days.map((d) => d.met + d.breached));
  const step = peak <= 4 ? 1 : peak <= 10 ? 2 : Math.ceil(peak / 4 / 5) * 5;
  const yMax = Math.ceil(peak / step) * step;
  const ticks = Array.from({ length: yMax / step + 1 }, (_, i) => i * step);
  const band = plotW / days.length;
  const barW = Math.max(2, Math.min(24, band - 2));
  const y = (v: number) => top + plotH - (v / yMax) * plotH;
  const labelAt = new Set([0, Math.floor((days.length - 1) / 2), days.length - 1]);

  // Column path: square at the baseline, 4px rounded data-end (only when tall enough to show it).
  const column = (x: number, y0: number, y1: number, rounded: boolean) => {
    const h = y0 - y1;
    if (h <= 0) return "";
    const r = rounded ? Math.min(4, h, barW / 2) : 0;
    return `M${x},${y0}V${y1 + r}${r ? `Q${x},${y1} ${x + r},${y1}` : ""}H${x + barW - r}${r ? `Q${x + barW},${y1} ${x + barW},${y1 + r}` : ""}V${y0}Z`;
  };

  const onKey = (e: KeyboardEvent) => {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight" && e.key !== "Home" && e.key !== "End") return;
    e.preventDefault();
    const last = days.length - 1;
    setActive((i) => e.key === "Home" ? 0 : e.key === "End" ? last
      : Math.min(last, Math.max(0, (i ?? last) + (e.key === "ArrowRight" ? 1 : -1))));
  };

  const shown = active === null ? null : days[active];
  const colX = active === null ? 0 : left + band * active + band / 2;
  const tipOnLeft = colX > width / 2;
  const total = days.reduce((n, d) => n + d.met + d.breached, 0);

  return (
    <div className="sla-chart" ref={box}>
      <div className="chart-legend" aria-hidden>
        <span><i className="swatch met" />Met</span>
        <span><i className="swatch breached" />Breached</span>
      </div>
      {width > 0 && <svg width={width} height={height} role="img" tabIndex={0} onKeyDown={onKey}
        onFocus={() => setActive((i) => i ?? days.length - 1)} onBlur={() => setActive(null)}
        onPointerLeave={() => setActive(null)}
        aria-label={`Resolutions per day: ${total} in the period. Use the arrow keys to read each day.`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={left} x2={width - right} y1={y(t)} y2={y(t)} className="grid" />
            <text x={left - 6} y={y(t)} dy="0.32em" textAnchor="end" className="tick">{t}</text>
          </g>
        ))}
        {days.map((d, i) => {
          const x = left + band * i + (band - barW) / 2;
          const metTop = y(d.met), allTop = y(d.met + d.breached);
          // 2px surface gap between the met segment and the breached segment stacked on it.
          const gap = d.met && d.breached ? 2 : 0;
          return (
            <g key={d.date} className={active === i ? "col on" : "col"}>
              <path className="met" d={column(x, y(0), metTop, !d.breached)} />
              <path className="breached" d={column(x, metTop - gap, allTop, true)} />
              <rect x={left + band * i} y={top} width={band} height={plotH} fill="transparent"
                onPointerEnter={() => setActive(i)} onPointerMove={() => setActive(i)} />
              {labelAt.has(i) && (
                <text x={left + band * i + band / 2} y={height - 6} textAnchor={i === 0 ? "start" : i === days.length - 1 ? "end" : "middle"} className="tick">
                  {new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(`${d.date}T00:00:00`))}
                </text>
              )}
            </g>
          );
        })}
      </svg>}
      {shown && (
        <div className="chart-tip" role="status"
          style={tipOnLeft ? { right: width - colX + band / 2 + 8 } : { left: colX + band / 2 + 8 }}>
          <div className="tip-title">{formatDay(shown.date)}</div>
          <div><i className="key met" /><strong>{shown.met}</strong> met</div>
          <div><i className="key breached" /><strong>{shown.breached}</strong> breached</div>
        </div>
      )}
      <details className="chart-table">
        <summary>Show as table</summary>
        <table className="table">
          <thead><tr><th>Day</th><th>Met</th><th>Breached</th></tr></thead>
          <tbody>{days.map((d) => <tr key={d.date}><td>{formatDay(d.date)}</td><td className="num">{d.met}</td><td className="num">{d.breached}</td></tr>)}</tbody>
        </table>
      </details>
    </div>
  );
}

function Meter({ value }: { value: number | null }) {
  if (value === null) return <span className="subtle">—</span>;
  return (
    <span className="meter-cell">
      <span className="meter" aria-hidden><i style={{ width: `${value}%` }} /></span>
      <span className="num">{percent(value)}</span>
    </span>
  );
}

function BreakdownTable({ title, rows, empty }: { title: string; rows: SlaBreakdown[]; empty: string }) {
  return (
    <Card title={`${title}: targets met`} flush>
      <DataTable rows={rows} rowKey={(r) => String(r.key)} empty={<div className="card-body subtle">{empty}</div>}
        columns={[
          { key: "l", label: "", render: (r) => <strong>{r.name}</strong> },
          { key: "res", label: "Resolution", render: (r) => <Meter value={r.resolution_met_percent} /> },
          { key: "n", label: "Resolved", className: "num hide-sm", render: (r) => r.resolved },
          { key: "resp", label: "Response", render: (r) => <Meter value={r.response_met_percent} /> },
          { key: "b", label: <span title="Open tickets past a target right now">Breached</span>, className: "num",
            render: (r) => r.open_breached || <span className="subtle">0</span> },
        ]} />
    </Card>
  );
}

export function SlaDashboardPage() {
  const navigate = useNavigate();
  const [days, setDays] = useState<`${SlaPeriodDays}`>("30");
  const [group, setGroup] = useState("");
  const groups = useQuery({ queryKey: ["support-groups"], queryFn: getSupportGroups });
  const report = useQuery({
    queryKey: ["report", "sla", days, group],
    queryFn: () => getSlaReport({ days: Number(days) as SlaPeriodDays, group: group ? Number(group) : undefined }),
    placeholderData: keepPreviousData,
    refetchInterval: 60_000,
  });
  const data = report.data;

  return (
    <>
      <PageHeader eyebrow={<Link to="/reports" className="back-link"><ArrowLeft size={14} />Reports</Link>}
        title="SLA dashboard"
        description="Tickets breaching or about to breach their targets now, and how often targets were met." />
      <div className="filter-row">
        <Tabs tabs={PERIODS} value={days} onChange={setDays} />
        <select className="select" aria-label="Support group" value={group} onChange={(e) => setGroup(e.target.value)} style={{ maxWidth: 220 }}>
          <option value="">All groups</option>
          {groups.data?.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
        </select>
        {data && <span className="subtle">Updated {relativeTime(data.generated_at)}</span>}
      </div>
      {report.isPending && <LoadingState />}
      {report.isError && !data && <ErrorState message={apiErrorMessage(report.error)} />}
      {data && (
        <div className={report.isPlaceholderData ? "stack sla-page refreshing" : "stack sla-page"}>
          <div className="metrics" style={{ marginBottom: 0 }}>
            <div className="metric"><span><OctagonAlert size={12} aria-hidden /> Breached now</span>
              <strong style={{ color: data.now.breached ? "var(--red)" : undefined }}>{data.now.breached}</strong></div>
            <div className="metric"><span><AlertTriangle size={12} aria-hidden /> At risk</span>
              <strong style={{ color: data.now.at_risk ? "var(--amber)" : undefined }}>{data.now.at_risk}</strong></div>
            <div className="metric"><span>Resolution target met</span><strong>{percent(data.period.resolution_met_percent)}</strong>
              <small className="subtle">{data.period.resolved} resolved</small></div>
            <div className="metric"><span>Response target met</span><strong>{percent(data.period.response_met_percent)}</strong>
              <small className="subtle">{data.period.responded} first responses</small></div>
          </div>
          <p className="subtle" style={{ margin: 0 }}>
            Also open: {data.now.on_track} on track, {data.now.paused} paused (waiting on the requester)
            {data.now.no_sla ? `, ${data.now.no_sla} without an SLA policy` : ""}.
          </p>

          <Card title="Needs attention" flush>
            <DataTable rows={data.attention} rowKey={(r) => r.public_id}
              onRowClick={(r) => navigate(`/tech/tickets/${r.public_id}`)}
              empty={<div className="card-body subtle"><Clock size={14} aria-hidden /> Nothing is breached or at risk right now.</div>}
              columns={[
                { key: "s", label: "State", render: (r) => <StateBadge row={r} /> },
                { key: "t", label: "Ticket", className: "title-cell", render: (r) => (
                  <Link to={`/tech/tickets/${r.public_id}`} onClick={(e) => e.stopPropagation()}>
                    <span className="num">{r.request_number}</span> {r.subject}
                  </Link>) },
                { key: "p", label: "Priority", render: (r) => <PriorityBadge priority={r.priority} /> },
                { key: "d", label: "Due", render: (r) => <span title={formatDate(r.due_at)}>{dueText(r)}</span> },
                { key: "g", label: "Group", className: "hide-sm", render: (r) => r.assignment_group ?? <span className="subtle">None</span> },
                { key: "a", label: "Assignee", className: "hide-sm", render: (r) => r.technician ?? <span className="subtle">Unassigned</span> },
              ]} />
            {data.attention.length >= 50 && <div className="card-body subtle">Showing the 50 most urgent.</div>}
          </Card>

          <Card title={`Resolutions per day, last ${data.days} days`}>
            <TrendChart days={data.trend} />
          </Card>

          <div className="grid-2">
            <BreakdownTable title="By support group" rows={data.by_group} empty="No resolved or breached tickets in this period." />
            <BreakdownTable title="By priority" rows={data.by_priority} empty="No resolved or breached tickets in this period." />
          </div>
        </div>
      )}
    </>
  );
}
