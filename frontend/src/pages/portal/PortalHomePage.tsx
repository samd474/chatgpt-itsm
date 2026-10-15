import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { getTickets } from "../../api/tickets";
import { apiErrorMessage } from "../../api/client";
import { EmptyState, ErrorState, LoadingState } from "../../components/Feedback";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import { formatDate } from "../../utils/format";

export function PortalHomePage() {
  const [page, setPage] = useState(1);
  // No requester ID is sent: Django's visible_HelpRequests() scope decides what this user may see.
  const query = useQuery({
    queryKey: ["tickets", "portal", page],
    queryFn: () => getTickets({ ordering: "-created_at", page }),
  });

  return (
    <section>
      <div className="page-heading">
        <div><h1>My requests</h1><p>Tickets the API allows your account to see.</p></div>
        <Link className="button" to="/portal/incidents/new">Report an incident</Link>
      </div>

      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState message={apiErrorMessage(query.error)} />}
      {query.data && query.data.results.length === 0 && <EmptyState message="You do not have any tickets yet." />}

      {query.data && query.data.results.length > 0 && (
        <>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Number</th><th>Subject</th><th>Status</th><th>Priority</th><th>Updated</th></tr></thead>
              <tbody>
                {query.data.results.map((ticket) => (
                  <tr key={ticket.public_id}>
                    <td><Link to={`/portal/tickets/${ticket.public_id}`}>{ticket.request_number || ticket.public_id}</Link></td>
                    <td>{ticket.subject}</td>
                    <td><StatusBadge status={ticket.status} /></td>
                    <td><PriorityBadge priority={ticket.priority} /></td>
                    <td>{formatDate(ticket.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <button className="button button--secondary" disabled={!query.data.previous} onClick={() => setPage((p) => Math.max(1, p - 1))}>Previous</button>
            <span>{query.data.count} tickets</span>
            <button className="button button--secondary" disabled={!query.data.next} onClick={() => setPage((p) => p + 1)}>Next</button>
          </div>
        </>
      )}
    </section>
  );
}
