import { useQuery } from "@tanstack/react-query";
import { CalendarClock, Plus } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listResource, ENDPOINTS } from "../../api/resources";
import { useAuth } from "../../auth/context";
import { isStaff } from "../../auth/roles";
import { ChangeStatusBadge, Pill } from "../../components/badges";
import { Card, DataTable, EmptyState, LoadingState, PageHeader, Pager, SearchInput, Tabs } from "../../components/ui";
import type { Change } from "../../types";
import { formatDate } from "../../utils/format";

const VIEWS: Record<string, string | undefined> = { active: undefined, draft: "draft", awaiting_approval: "awaiting_approval", scheduled: "scheduled", closed: "closed" };

export function ChangesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [view, setView] = useState("active");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["changes", view, search, page],
    queryFn: () => listResource<Change>(ENDPOINTS.changes, {
      page, search: search || undefined, status: VIEWS[view], in_flight: view === "active" ? true : undefined, ordering: "-created_at",
    }),
  });
  const rows = query.data?.items ?? [];
  return (
    <>
      <PageHeader title="Changes" description="Plan, approve and track changes to production systems."
        actions={<>
          <Link className="btn btn-secondary" to="/changes/calendar"><CalendarClock />Calendar</Link>
          {isStaff(user) && <button className="btn btn-primary" onClick={() => navigate("/changes/new")}><Plus />New change</button>}
        </>} />
      <Tabs value={view} onChange={(v) => { setView(v); setPage(1); }} tabs={[
        { value: "active", label: "In flight" }, { value: "draft", label: "Drafts" }, { value: "awaiting_approval", label: "Awaiting approval" },
        { value: "scheduled", label: "Scheduled" }, { value: "closed", label: "Closed" },
      ]} />
      <div className="toolbar"><SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search changes" /></div>
      {query.isPending && <LoadingState />}
      {query.data && (
        <Card flush>
          <DataTable rows={rows} rowKey={(c) => c.id} onRowClick={(c) => navigate(`/changes/${c.id}`)}
            empty={<EmptyState title="No changes" />}
            columns={[
              { key: "n", label: "Number", className: "num", render: (c) => c.number },
              { key: "t", label: "Title", className: "title-cell", render: (c) => c.title },
              { key: "ty", label: "Type", className: "hide-sm", render: (c) => <Pill value={c.change_type} /> },
              { key: "r", label: "Risk", render: (c) => <Pill value={c.risk} /> },
              { key: "s", label: "Status", render: (c) => <ChangeStatusBadge status={c.status} /> },
              { key: "w", label: "Window", className: "hide-sm", render: (c) => <span className="subtle">{c.planned_start ? formatDate(c.planned_start) : "Not scheduled"}</span> },
            ]} />
          {(query.data.next || query.data.previous) && <Pager count={query.data.count} page={page} hasNext={!!query.data.next} hasPrev={!!query.data.previous} onPage={setPage} noun="changes" />}
        </Card>
      )}
    </>
  );
}
