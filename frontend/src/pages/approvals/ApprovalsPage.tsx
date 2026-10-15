import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { decideApproval, getMyApprovals } from "../../api/tickets";
import { apiErrorMessage } from "../../api/client";
import { EmptyState, ErrorState, LoadingState } from "../../components/Feedback";
import type { Approval } from "../../types";
import { formatDate } from "../../utils/format";

function ApprovalCard({ approval }: { approval: Approval }) {
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const decide = useMutation({
    mutationFn: (state: "approved" | "rejected") => decideApproval(approval.id, state, comment),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["approvals"] }),
  });
  return (
    <article className="panel">
      <div className="eyebrow">{approval.request_number}</div>
      <h2>{approval.subject}</h2>
      <p className="muted">Requested {formatDate(approval.created_at)}</p>
      {approval.state === "pending" ? <>
        <textarea rows={2} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Optional comment" />
        {decide.isError && <div className="alert alert--error">{apiErrorMessage(decide.error)}</div>}
        <div className="badge-row">
          <button className="button" disabled={decide.isPending} onClick={() => decide.mutate("approved")}>Approve</button>
          <button className="button button--secondary" disabled={decide.isPending} onClick={() => decide.mutate("rejected")}>Reject</button>
        </div>
      </> : <p><strong>{approval.state}</strong> {formatDate(approval.decided_at)} {approval.comment && `- ${approval.comment}`}</p>}
    </article>
  );
}

export function ApprovalsPage() {
  const [state, setState] = useState("pending");
  const query = useQuery({ queryKey: ["approvals", state], queryFn: () => getMyApprovals(state || undefined) });
  return (
    <section>
      <div className="page-heading">
        <div><h1>My approvals</h1><p>Requests waiting for your decision.</p></div>
        <select value={state} onChange={(e) => setState(e.target.value)} aria-label="Approval state" className="select--auto">
          <option value="pending">Pending</option>
          <option value="">All</option>
        </select>
      </div>
      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState message={apiErrorMessage(query.error)} />}
      {query.data?.results.length === 0 && <EmptyState message="Nothing is waiting for you." />}
      <div className="card-grid">{query.data?.results.map((a) => <ApprovalCard key={a.id} approval={a} />)}</div>
    </section>
  );
}
