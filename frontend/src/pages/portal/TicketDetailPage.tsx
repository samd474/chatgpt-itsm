import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { addComment, getComments, getTicket, transitionTicket } from "../../api/tickets";
import { apiErrorMessage } from "../../api/client";
import { AttachmentsPanel } from "../../components/AttachmentsPanel";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import type { TicketStatus } from "../../types";
import { formatDate } from "../../utils/format";

export function TicketDetailPage() {
  const { id = "" } = useParams();
  const location = useLocation();
  const uploadErrors = (location.state as { uploadErrors?: string[] } | null)?.uploadErrors ?? [];
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const ticketQuery = useQuery({ queryKey: ["ticket", id], queryFn: () => getTicket(id), enabled: !!id });
  const commentsQuery = useQuery({ queryKey: ["ticket-comments", id], queryFn: () => getComments(id), enabled: !!id });
  const commentMutation = useMutation({
    // Requesters only ever post public replies; Django also refuses private ones from them.
    mutationFn: () => addComment(id, { body: comment, visibility: "public" }),
    onSuccess: async () => {
      setComment("");
      await queryClient.invalidateQueries({ queryKey: ["ticket-comments", id] });
    },
  });
  const transition = useMutation({
    mutationFn: (status: TicketStatus) => transitionTicket(id, { status }),
    onSuccess: (ticket) => queryClient.setQueryData(["ticket", id], ticket),
  });

  if (ticketQuery.isPending) return <LoadingState />;
  if (ticketQuery.isError) return <ErrorState message={apiErrorMessage(ticketQuery.error)} />;
  const ticket = ticketQuery.data;
  const answers = (ticket.request_payload.answers ?? null) as Record<string, unknown> | null;

  return (
    <section>
      <div className="page-heading">
        <div><div className="eyebrow">{ticket.request_number}</div><h1>{ticket.subject}</h1></div>
        <div className="badge-row"><PriorityBadge priority={ticket.priority} /><StatusBadge status={ticket.status} /></div>
      </div>
      {uploadErrors.map((e) => <div key={e} className="alert alert--error">Attachment not uploaded: {e}</div>)}

      <div className="detail-grid">
        <div className="panel">
          <h2>Description</h2>
          <p className="pre-wrap">{ticket.description || "-"}</p>
          {answers && (
            <>
              <h3>Request details</h3>
              <dl>{Object.entries(answers).map(([k, v]) => <div key={k} className="dl-row"><dt>{k.replaceAll("_", " ")}</dt><dd>{String(v)}</dd></div>)}</dl>
            </>
          )}
          {ticket.resolution_body && <><h3>Resolution</h3><p className="pre-wrap">{ticket.resolution_body}</p></>}
        </div>
        <div className="panel">
          <h2>Details</h2>
          <dl>
            <dt>Created</dt><dd>{formatDate(ticket.created_at)}</dd>
            <dt>Updated</dt><dd>{formatDate(ticket.updated_at)}</dd>
            <dt>Assigned to</dt><dd>{ticket.technician_name || ticket.assignment_group_name || "Service desk"}</dd>
            <dt>Category</dt><dd>{ticket.category_name || "-"}</dd>
          </dl>
          <div className="badge-row">
            {ticket.status === "new" && <button className="button button--secondary" disabled={transition.isPending} onClick={() => transition.mutate("cancelled")}>Cancel request</button>}
            {ticket.status === "resolved" && <>
              <button className="button" disabled={transition.isPending} onClick={() => transition.mutate("closed")}>Confirm fixed</button>
              <button className="button button--secondary" disabled={transition.isPending} onClick={() => transition.mutate("in_progress")}>Still broken - reopen</button>
            </>}
          </div>
          {transition.isError && <div className="alert alert--error">{apiErrorMessage(transition.error)}</div>}
        </div>
      </div>

      <AttachmentsPanel publicId={ticket.public_id} canUpload={!["closed", "cancelled"].includes(ticket.status)} />

      <div className="panel">
        <h2>Conversation</h2>
        {commentsQuery.isPending && <LoadingState message="Loading comments..." />}
        {commentsQuery.isError && <ErrorState message={apiErrorMessage(commentsQuery.error)} />}
        <div className="timeline">
          {commentsQuery.data?.map((item) => (
            <article className="timeline-item" key={item.id}>
              <div><strong>{item.author_name || `User ${item.author}`}</strong><span className="muted"> {formatDate(item.created_at)}</span></div>
              <p className="pre-wrap">{item.body}</p>
            </article>
          ))}
        </div>
        <textarea rows={4} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Add a reply" />
        {commentMutation.isError && <div className="alert alert--error">{apiErrorMessage(commentMutation.error)}</div>}
        <button className="button" disabled={!comment.trim() || commentMutation.isPending} onClick={() => commentMutation.mutate()}>Post reply</button>
      </div>
    </section>
  );
}
