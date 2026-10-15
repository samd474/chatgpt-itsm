import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { exportUrl, getSupportGroups, getTickets, type TicketListParams } from "../../api/tickets";
import { apiErrorMessage } from "../../api/client";
import { useAuth } from "../../auth/context";
import { hasRole } from "../../auth/roles";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { SlaBadge } from "../../components/SlaBadge";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import { formatDate } from "../../utils/format";

export function QueuePage() {
  const { user } = useAuth();
  const [filters, setFilters] = useState<TicketListParams>({ ordering: "priority" });
  const [draftSearch, setDraftSearch] = useState("");
  const query = useQuery({ queryKey: ["tickets", "tech", filters], queryFn: () => getTickets(filters) });
  const groups = useQuery({ queryKey: ["lookup", "groups"], queryFn: getSupportGroups });

  function update(changes: Partial<TicketListParams>) {
    setFilters((old) => ({ ...old, page: 1, ...changes }));
  }

  function search(event: FormEvent) {
    event.preventDefault();
    update({ search: draftSearch || undefined });
  }

  return (
    <section>
      <div className="page-heading">
        <div><h1>Technician queue</h1><p>Filtering and paging run on the server.</p></div>
        {hasRole(user, "Manager", "Administrator") && (
          <a className="button button--secondary" href={exportUrl({ ...filters, page: undefined })}>Export CSV</a>
        )}
      </div>
      <div className="filter-bar">
        <form onSubmit={search} className="inline-form">
          <input value={draftSearch} onChange={(e) => setDraftSearch(e.target.value)} placeholder="Search number, subject, description" />
          <button className="button button--secondary">Search</button>
        </form>
        <select value={filters.status ?? ""} onChange={(e) => update({ status: e.target.value || undefined })} aria-label="Status filter">
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="assigned">Assigned</option>
          <option value="in_progress">In progress</option>
          <option value="pending_user_response">Pending user response</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
        <select value={filters.priority ?? ""} onChange={(e) => update({ priority: e.target.value || undefined })} aria-label="Priority filter">
          <option value="">All priorities</option>
          {[1, 2, 3, 4].map((p) => <option key={p} value={p}>P{p}</option>)}
        </select>
        <select value={filters.assignment_group ?? ""} onChange={(e) => update({ assignment_group: e.target.value || undefined })} aria-label="Group filter">
          <option value="">All groups</option>
          {groups.data?.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
        </select>
        <select value={filters.technician ?? ""} onChange={(e) => update({ technician: e.target.value || undefined })} aria-label="Assignee filter">
          <option value="">Anyone</option>
          {user && <option value={user.id}>Assigned to me</option>}
        </select>
        <select value={filters.ordering ?? ""} onChange={(e) => update({ ordering: e.target.value || undefined })} aria-label="Sort order">
          <option value="priority">Highest priority</option>
          <option value="-updated_at">Recently updated</option>
          <option value="created_at">Oldest first</option>
        </select>
      </div>

      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState message={apiErrorMessage(query.error)} />}
      {query.data && <>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Number</th><th>Subject</th><th>Status</th><th>Priority</th><th>Assignee</th><th>SLA</th><th>Updated</th></tr></thead>
            <tbody>
              {query.data.results.map((ticket) => (
                <tr key={ticket.public_id}>
                  <td><Link to={`/tech/tickets/${ticket.public_id}`}>{ticket.request_number}</Link></td>
                  <td>{ticket.subject}</td>
                  <td><StatusBadge status={ticket.status} /></td>
                  <td><PriorityBadge priority={ticket.priority} /></td>
                  <td>{ticket.technician_name ?? ticket.assignment_group_name ?? "Unassigned"}</td>
                  <td><SlaBadge sla={ticket.sla} /></td>
                  <td>{formatDate(ticket.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="pagination">
          <button className="button button--secondary" disabled={!query.data.previous} onClick={() => setFilters((old) => ({ ...old, page: Math.max(1, (old.page ?? 1) - 1) }))}>Previous</button>
          <span>{query.data.count} tickets</span>
          <button className="button button--secondary" disabled={!query.data.next} onClick={() => setFilters((old) => ({ ...old, page: (old.page ?? 1) + 1 }))}>Next</button>
        </div>
      </>}
    </section>
  );
}
