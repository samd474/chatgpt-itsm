import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getTickets } from "../../api/tickets";
import { apiErrorMessage } from "../../api/client";
import { PriorityBadge, StatusBadge } from "../../components/badges";
import { Card, DataTable, EmptyState, ErrorState, LoadingState, PageHeader, Pager, Tabs } from "../../components/ui";
import { relativeTime } from "../../utils/format";

type View = "open" | "resolved" | "all";

export function PortalHomePage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [view, setView] = useState<View>("open");
  // No requester ID is sent: the server's visibility scope decides what this user may see.
  const query = useQuery({
    queryKey: ["tickets", "portal", view, page],
    queryFn: () => getTickets({
      ordering: "-updated_at",
      page,
      open: view === "open" ? true : undefined,
      status: view === "resolved" ? "resolved" : undefined,
    }),
  });

  return (
    <>
      <PageHeader title="My requests" description="Track the issues and requests you've raised."
        actions={<Link className="btn btn-primary" to="/portal/incidents/new"><Plus />Report an issue</Link>} />
      <Tabs value={view} onChange={(v) => { setView(v); setPage(1); }} tabs={[
        { value: "open", label: "Open" }, { value: "resolved", label: "Awaiting confirmation" }, { value: "all", label: "All" },
      ]} />
      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState message={apiErrorMessage(query.error)} />}
      {query.data && (
        <Card flush>
          <DataTable
            rows={query.data.results}
            rowKey={(t) => t.public_id}
            onRowClick={(t) => navigate(`/portal/tickets/${t.public_id}`)}
            empty={<EmptyState title="No requests here" message="When you report an issue it will show up here."
              action={<Link className="btn btn-secondary" to="/portal/incidents/new">Report an issue</Link>} />}
            columns={[
              { key: "n", label: "Number", className: "num", render: (t) => t.request_number },
              { key: "s", label: "Subject", className: "title-cell", render: (t) => t.subject },
              { key: "st", label: "Status", render: (t) => <StatusBadge status={t.status} /> },
              { key: "p", label: "Priority", render: (t) => <PriorityBadge priority={t.priority} /> },
              { key: "u", label: "Updated", render: (t) => <span className="subtle">{relativeTime(t.updated_at)}</span> },
            ]}
          />
          {(query.data.next || query.data.previous) && (
            <Pager count={query.data.count} page={page} hasNext={!!query.data.next} hasPrev={!!query.data.previous} onPage={setPage} noun="requests" />
          )}
        </Card>
      )}
    </>
  );
}
