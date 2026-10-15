import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { getAuditEvents, type AuditParams } from "../../api/operations";
import { apiErrorMessage } from "../../api/client";
import { Card, DataTable, Drawer, ErrorState, LoadingState, PageHeader, Pager } from "../../components/ui";
import type { AuditEvent } from "../../types";
import { formatDate } from "../../utils/format";

export function AuditPage() {
  const [params, setParams] = useState<AuditParams>({ page: 1 });
  const [draft, setDraft] = useState({ activity_type: "", object_id: "", request_id: "" });
  const [selected, setSelected] = useState<AuditEvent | null>(null);
  const query = useQuery({ queryKey: ["audit-events", params], queryFn: () => getAuditEvents(params) });

  function search(event: FormEvent) {
    event.preventDefault();
    setParams({ page: 1, activity_type: draft.activity_type || undefined, object_id: draft.object_id || undefined, request_id: draft.request_id || undefined });
  }

  return (
    <>
      <PageHeader title="Audit log" description="Every meaningful change, append-only. Records can't be edited or deleted." />
      <form className="toolbar" onSubmit={search}>
        <input className="input" placeholder="Event (e.g. ticket.created)" value={draft.activity_type} onChange={(e) => setDraft({ ...draft, activity_type: e.target.value })} />
        <input className="input" placeholder="Object ID" value={draft.object_id} onChange={(e) => setDraft({ ...draft, object_id: e.target.value })} />
        <input className="input" placeholder="Request ID" value={draft.request_id} onChange={(e) => setDraft({ ...draft, request_id: e.target.value })} />
        <button className="btn btn-secondary">Filter</button>
      </form>
      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState message={apiErrorMessage(query.error)} />}
      {query.data && (
        <Card flush>
          <DataTable rows={query.data.results} rowKey={(e) => e.id} onRowClick={setSelected} columns={[
            { key: "t", label: "Time", className: "num", render: (e) => formatDate(e.created_at) },
            { key: "e", label: "Event", render: (e) => <code>{e.event_type}</code> },
            { key: "o", label: "Object", render: (e) => <span className="subtle">{e.object_type} · {e.object_id.slice(0, 13)}</span> },
            { key: "a", label: "Actor", render: (e) => e.actor_name ?? <span className="subtle">System</span> },
            { key: "ip", label: "Source", className: "num", render: (e) => e.source_ip ?? "—" },
          ]} />
          <Pager count={query.data.count} page={params.page ?? 1} hasNext={!!query.data.next} hasPrev={!!query.data.previous}
            onPage={(p) => setParams((old) => ({ ...old, page: p }))} noun="events" />
        </Card>
      )}
      {selected && (
        <Drawer title={selected.event_type} onClose={() => setSelected(null)}>
          <div className="stack">
            <dl className="props">
              <dt>When</dt><dd>{formatDate(selected.created_at)}</dd>
              <dt>Actor</dt><dd>{selected.actor_name ?? "System"}</dd>
              <dt>Object</dt><dd>{selected.object_type} {selected.object_id}</dd>
              <dt>Request ID</dt><dd><code>{selected.request_id || "—"}</code></dd>
              <dt>Source IP</dt><dd>{selected.source_ip ?? "—"}</dd>
            </dl>
            {Object.keys(selected.before).length > 0 && <><h3>Before</h3><pre>{JSON.stringify(selected.before, null, 2)}</pre></>}
            {Object.keys(selected.after).length > 0 && <><h3>After</h3><pre>{JSON.stringify(selected.after, null, 2)}</pre></>}
            {Object.keys(selected.metadata).length > 0 && <><h3>Details</h3><pre>{JSON.stringify(selected.metadata, null, 2)}</pre></>}
          </div>
        </Drawer>
      )}
    </>
  );
}
