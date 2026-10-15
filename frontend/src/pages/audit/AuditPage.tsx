import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { getAuditEvents, type AuditParams } from "../../api/operations";
import { apiErrorMessage } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { formatDate } from "../../utils/format";

export function AuditPage() {
  const [params, setParams] = useState<AuditParams>({ page: 1 });
  const [draft, setDraft] = useState({ activity_type: "", object_id: "", request_id: "" });
  const query = useQuery({ queryKey: ["audit-events", params], queryFn: () => getAuditEvents(params) });

  function search(event: FormEvent) {
    event.preventDefault();
    setParams({
      page: 1,
      activity_type: draft.activity_type || undefined,
      object_id: draft.object_id || undefined,
      request_id: draft.request_id || undefined,
    });
  }

  return (
    <section>
      <div className="page-heading"><div><h1>Audit events</h1><p>Read-only. Records cannot be changed or deleted through the application.</p></div></div>
      <form className="filter-bar" onSubmit={search}>
        <input placeholder="Event type (e.g. ticket.created)" value={draft.activity_type} onChange={(e) => setDraft({ ...draft, activity_type: e.target.value })} />
        <input placeholder="Object ID" value={draft.object_id} onChange={(e) => setDraft({ ...draft, object_id: e.target.value })} />
        <input placeholder="Request ID" value={draft.request_id} onChange={(e) => setDraft({ ...draft, request_id: e.target.value })} />
        <button className="button button--secondary">Filter</button>
      </form>
      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState message={apiErrorMessage(query.error)} />}
      {query.data && <>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Time</th><th>Event</th><th>Object</th><th>Actor</th><th>Details</th><th>Request ID</th></tr></thead>
            <tbody>
              {query.data.results.map((event) => (
                <tr key={event.id}>
                  <td>{formatDate(event.created_at)}</td>
                  <td>{event.event_type}</td>
                  <td>{event.object_type} <code>{event.object_id}</code></td>
                  <td>{event.actor_name ?? "System"}</td>
                  <td>{Object.keys(event.metadata).length > 0 && <code className="small">{JSON.stringify(event.metadata)}</code>}</td>
                  <td><code className="small">{event.request_id || "-"}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="pagination">
          <button className="button button--secondary" disabled={!query.data.previous} onClick={() => setParams((p) => ({ ...p, page: Math.max(1, (p.page ?? 1) - 1) }))}>Previous</button>
          <span>{query.data.count} events</span>
          <button className="button button--secondary" disabled={!query.data.next} onClick={() => setParams((p) => ({ ...p, page: (p.page ?? 1) + 1 }))}>Next</button>
        </div>
      </>}
    </section>
  );
}
