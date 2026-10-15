import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getAction, ENDPOINTS } from "../../api/resources";
import { ChangeStatusBadge, Pill } from "../../components/badges";
import { Card, EmptyState, LoadingState, PageHeader } from "../../components/ui";
import type { ChangeStatus } from "../../types";

type Entry = { id: number; number: string; title: string; status: ChangeStatus; risk: string; change_type: string; planned_start: string; planned_end: string };

function startOfWeek(d: Date) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  x.setDate(x.getDate() - ((x.getDay() + 6) % 7));
  return x;
}

export function ChangeCalendarPage() {
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));
  const end = useMemo(() => { const e = new Date(weekStart); e.setDate(e.getDate() + 14); return e; }, [weekStart]);
  const query = useQuery({
    queryKey: ["change-calendar", weekStart.toISOString()],
    queryFn: () => getAction<Entry[]>(`${ENDPOINTS.changes}calendar/`, { start: weekStart.toISOString(), end: end.toISOString() }),
  });
  const days = Array.from({ length: 14 }, (_, i) => { const d = new Date(weekStart); d.setDate(d.getDate() + i); return d; });
  const shift = (n: number) => setWeekStart((w) => { const x = new Date(w); x.setDate(x.getDate() + n); return x; });
  const fmt = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" });
  const time = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" });

  return (
    <>
      <PageHeader title="Change calendar" description="Approved and scheduled change windows for the next two weeks."
        actions={<div className="row">
          <button className="btn btn-secondary btn-icon" aria-label="Previous week" onClick={() => shift(-7)}><ChevronLeft /></button>
          <button className="btn btn-secondary" onClick={() => setWeekStart(startOfWeek(new Date()))}>Today</button>
          <button className="btn btn-secondary btn-icon" aria-label="Next week" onClick={() => shift(7)}><ChevronRight /></button>
        </div>} />
      {query.isPending && <LoadingState />}
      {query.data && (
        <Card flush>
          {query.data.length === 0 && <EmptyState title="Nothing scheduled" message="No change windows in this period." />}
          {query.data.length > 0 && days.map((day) => {
            const next = new Date(day); next.setDate(next.getDate() + 1);
            const items = query.data.filter((e) => new Date(e.planned_start) < next && new Date(e.planned_end) > day);
            const today = day.toDateString() === new Date().toDateString();
            return (
              <div className="cal-day" key={day.toISOString()}>
                <div className="cal-date"><strong style={{ color: today ? "var(--accent-text)" : undefined }}>{fmt.format(day)}</strong>{today && "Today"}</div>
                <div>
                  {items.length === 0 && <span className="subtle">—</span>}
                  {items.map((e) => (
                    <div className="cal-event" key={e.id} style={{ borderLeftColor: e.risk === "high" ? "var(--red)" : e.risk === "medium" ? "var(--amber)" : "var(--green)" }}>
                      <span className="num">{time.format(new Date(e.planned_start))}–{time.format(new Date(e.planned_end))}</span>
                      <Link to={`/changes/${e.id}`}>{e.number}</Link>
                      <span className="title-cell">{e.title}</span>
                      <span className="spacer" /><Pill value={e.change_type} /><ChangeStatusBadge status={e.status} />
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </Card>
      )}
    </>
  );
}
