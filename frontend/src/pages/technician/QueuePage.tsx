import { useMutation, useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getQueueTickets, getQueues, getSupportGroups, getTickets, requestExport, type TicketListParams } from "../../api/tickets";
import { apiErrorMessage } from "../../api/client";
import { useAuth } from "../../auth/context";
import { hasRole } from "../../auth/roles";
import { PriorityBadge, SlaBadge, StatusBadge } from "../../components/badges";
import { Avatar, Card, DataTable, EmptyState, ErrorState, LoadingState, Notice, PageHeader, Pager, SearchInput, Tabs } from "../../components/ui";
import type { Ticket } from "../../types";
import { relativeTime } from "../../utils/format";

export function QueuePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [view, setView] = useState<string>("all");
  const [filters, setFilters] = useState<TicketListParams>({ ordering: "priority", open: true });
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const queues = useQuery({ queryKey: ["queues"], queryFn: getQueues });
  const groups = useQuery({ queryKey: ["lookup", "groups-simple"], queryFn: getSupportGroups });
  const queueId = view === "all" ? null : Number(view);
  const tickets = useQuery({
    queryKey: ["tickets", "tech", view, filters, search, page],
    queryFn: () => queueId
      ? getQueueTickets(queueId, { page, search: search || undefined })
      : getTickets({ ...filters, page, search: search || undefined }),
  });
  const exporter = useMutation({ mutationFn: () => requestExport({ ...filters, search: search || undefined }) });
  const update = (changes: Partial<TicketListParams>) => { setFilters((f) => ({ ...f, ...changes })); setPage(1); };

  return (
    <>
      <PageHeader title="Ticket queue" description="Tickets for you and your teams."
        actions={hasRole(user, "Manager", "Administrator") && view === "all" && (
          <button className="btn btn-secondary" disabled={exporter.isPending} onClick={() => exporter.mutate()}><Download />Export CSV</button>
        )} />
      {exporter.data?.queued && <div style={{ marginBottom: 12 }}><Notice tone="success">That's {exporter.data.rows} rows, so the export is being prepared in the background. Download it from Reports → Exports.</Notice></div>}
      {exporter.isError && <div style={{ marginBottom: 12 }}><Notice tone="error">{apiErrorMessage(exporter.error)}</Notice></div>}

      <Tabs value={view} onChange={(v) => { setView(v); setPage(1); }} tabs={[
        { value: "all", label: "All tickets" },
        ...(queues.data ?? []).map((q) => ({ value: String(q.id), label: q.name })),
      ]} />

      <div className="toolbar">
        <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search number, subject, description" />
        {view === "all" && <>
          <select className="select" value={filters.open ? "open" : filters.status ?? ""} aria-label="Status"
            onChange={(e) => update(e.target.value === "open" ? { open: true, status: undefined } : { open: undefined, status: e.target.value || undefined })}>
            <option value="open">Open</option>
            <option value="">Any status</option>
            <option value="new">New</option>
            <option value="assigned">Assigned</option>
            <option value="in_progress">In progress</option>
            <option value="pending_user_response">Pending user</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
          <select className="select" value={filters.priority ?? ""} onChange={(e) => update({ priority: e.target.value || undefined })} aria-label="Priority">
            <option value="">Any priority</option>{[1, 2, 3, 4].map((p) => <option key={p} value={p}>P{p}</option>)}
          </select>
          <select className="select" value={filters.assignment_group ?? ""} onChange={(e) => update({ assignment_group: e.target.value || undefined })} aria-label="Group">
            <option value="">Any group</option>{groups.data?.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
          <select className="select" value={filters.technician ?? ""} onChange={(e) => update({ technician: e.target.value || undefined })} aria-label="Assignee">
            <option value="">Anyone</option>{user && <option value={user.id}>Assigned to me</option>}
          </select>
          <select className="select" value={filters.ordering ?? ""} onChange={(e) => update({ ordering: e.target.value })} aria-label="Sort">
            <option value="priority">Priority</option><option value="-updated_at">Recently updated</option><option value="created_at">Oldest</option>
          </select>
        </>}
      </div>

      {tickets.isPending && <LoadingState />}
      {tickets.isError && <ErrorState message={apiErrorMessage(tickets.error)} />}
      {tickets.data && (
        <Card flush>
          <DataTable<Ticket>
            rows={tickets.data.results}
            rowKey={(t) => t.public_id}
            onRowClick={(t) => navigate(`/tech/tickets/${t.public_id}`)}
            empty={<EmptyState title="Queue is clear" message="No tickets match these filters." />}
            columns={[
              { key: "p", label: "", render: (t) => <PriorityBadge priority={t.priority} /> },
              { key: "n", label: "Number", className: "num", render: (t) => t.request_number },
              { key: "s", label: "Subject", className: "title-cell", render: (t) => t.subject },
              { key: "st", label: "Status", className: "hide-sm", render: (t) => <StatusBadge status={t.status} /> },
              { key: "a", label: "Assignee", className: "hide-sm", render: (t) => t.technician_name
                ? <span className="row"><Avatar name={t.technician_name} />{t.technician_name}</span>
                : <span className="subtle">{t.assignment_group_name ?? "Unassigned"}</span> },
              { key: "sla", label: "SLA", className: "hide-sm", render: (t) => <SlaBadge sla={t.sla} compact /> },
              { key: "u", label: "Updated", className: "hide-sm", render: (t) => <span className="subtle">{relativeTime(t.updated_at)}</span> },
            ]}
          />
          {(tickets.data.next || tickets.data.previous) && (
            <Pager count={tickets.data.count} page={page} hasNext={!!tickets.data.next} hasPrev={!!tickets.data.previous} onPage={setPage} noun="tickets" />
          )}
        </Card>
      )}
    </>
  );
}
