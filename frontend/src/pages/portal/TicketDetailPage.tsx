import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useParams } from "react-router-dom";
import { getTicket, transitionTicket } from "../../api/tickets";
import { apiErrorMessage } from "../../api/client";
import { AttachmentsPanel } from "../../components/AttachmentsPanel";
import { PriorityBadge, StatusBadge } from "../../components/badges";
import { Conversation } from "../../components/Conversation";
import { Card, ErrorState, LoadingState, Notice, PageHeader, PropRows } from "../../components/ui";
import type { TicketStatus } from "../../types";
import { formatDate } from "../../utils/format";

export function TicketDetailPage() {
  const { id = "" } = useParams();
  const location = useLocation();
  const uploadErrors = (location.state as { uploadErrors?: string[] } | null)?.uploadErrors ?? [];
  const queryClient = useQueryClient();
  const ticketQuery = useQuery({ queryKey: ["ticket", id], queryFn: () => getTicket(id), enabled: !!id });
  const transition = useMutation({
    mutationFn: (status: TicketStatus) => transitionTicket(id, { status }),
    onSuccess: (ticket) => queryClient.setQueryData(["ticket", id], ticket),
  });

  if (ticketQuery.isPending) return <LoadingState />;
  if (ticketQuery.isError) return <ErrorState message={apiErrorMessage(ticketQuery.error)} />;
  const t = ticketQuery.data;
  const answers = (t.request_payload.answers ?? null) as Record<string, unknown> | null;

  return (
    <>
      <PageHeader eyebrow={t.request_number} title={t.subject}
        actions={<>
          {t.status === "new" && <button className="btn btn-secondary" disabled={transition.isPending} onClick={() => transition.mutate("cancelled")}>Cancel request</button>}
          {t.status === "resolved" && <>
            <button className="btn btn-secondary" disabled={transition.isPending} onClick={() => transition.mutate("in_progress")}>Still not fixed</button>
            <button className="btn btn-primary" disabled={transition.isPending} onClick={() => transition.mutate("closed")}>Confirm it's fixed</button>
          </>}
        </>} />
      <div className="stack">
        {uploadErrors.map((e) => <Notice key={e} tone="error">Attachment not uploaded — {e}</Notice>)}
        {transition.isError && <Notice tone="error">{apiErrorMessage(transition.error)}</Notice>}
        {t.status === "resolved" && <Notice tone="success">We think this is fixed. Please confirm, or tell us if it's still happening.</Notice>}
        <div className="grid-main">
          <div className="stack">
            <Card title="Description">
              <p className="pre-wrap">{t.description || "—"}</p>
              {answers && <dl className="props" style={{ marginTop: 14 }}><PropRows data={answers} /></dl>}
              {t.resolution_body && <div style={{ marginTop: 14 }}><h3>Resolution</h3><p className="pre-wrap muted" style={{ marginTop: 4 }}>{t.resolution_body}</p></div>}
            </Card>
            <Conversation publicId={t.public_id} staff={false} />
          </div>
          <div className="stack">
            <Card title="Details">
              <dl className="props">
                <dt>Status</dt><dd><StatusBadge status={t.status} /></dd>
                <dt>Priority</dt><dd><PriorityBadge priority={t.priority} /></dd>
                <dt>Assigned to</dt><dd>{t.technician_name || t.assignment_group_name || "Service desk"}</dd>
                <dt>Category</dt><dd>{t.category_name || "—"}</dd>
                <dt>Opened</dt><dd>{formatDate(t.created_at)}</dd>
                <PropRows data={t.custom_fields} />
              </dl>
            </Card>
            <AttachmentsPanel publicId={t.public_id} canUpload={!["closed", "cancelled"].includes(t.status)} />
          </div>
        </div>
      </div>
    </>
  );
}
