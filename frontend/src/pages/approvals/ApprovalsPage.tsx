import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { decideApproval, getMyApprovals } from "../../api/tickets";
import { listAll, postAction, ENDPOINTS } from "../../api/resources";
import { apiErrorMessage } from "../../api/client";
import { useAuth } from "../../auth/context";
import { isStaff } from "../../auth/roles";
import { Pill } from "../../components/badges";
import { Card, EmptyState, LoadingState, Notice, PageHeader, Tabs } from "../../components/ui";
import type { ChangeApproval } from "../../types";
import { relativeTime } from "../../utils/format";

function Decision({ title, eyebrow, link, created, state, comment, decide }: {
  title: string; eyebrow: string; link?: string; created: string; state: string; comment: string;
  decide: (state: "approved" | "rejected", comment: string) => Promise<unknown>;
}) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const mutation = useMutation({
    mutationFn: (s: "approved" | "rejected") => decide(s, note),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["approvals"] }),
  });
  return (
    <Card>
      <div className="stack" style={{ gap: 10 }}>
        <div className="row"><span className="eyebrow">{eyebrow}</span><span className="spacer" /><span className="subtle">{relativeTime(created)}</span></div>
        <h2>{link ? <Link to={link}>{title}</Link> : title}</h2>
        {state === "pending" ? <>
          <textarea className="textarea" rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Comment (optional)" />
          {mutation.isError && <Notice tone="error">{apiErrorMessage(mutation.error)}</Notice>}
          <div className="form-actions">
            <button className="btn btn-danger" disabled={mutation.isPending} onClick={() => mutation.mutate("rejected")}>Reject</button>
            <button className="btn btn-primary" disabled={mutation.isPending} onClick={() => mutation.mutate("approved")}>Approve</button>
          </div>
        </> : <div className="row"><Pill value={state} />{comment && <span className="muted">“{comment}”</span>}</div>}
      </div>
    </Card>
  );
}

export function ApprovalsPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<"requests" | "changes">("requests");
  const [pendingOnly, setPendingOnly] = useState(true);
  const requests = useQuery({ queryKey: ["approvals", "requests", pendingOnly], queryFn: () => getMyApprovals(pendingOnly ? "pending" : undefined) });
  const changes = useQuery({
    queryKey: ["approvals", "changes", pendingOnly], enabled: isStaff(user),
    queryFn: () => listAll<ChangeApproval>(ENDPOINTS.changeApprovals, { state: pendingOnly ? "pending" : undefined }),
  });

  return (
    <>
      <PageHeader title="Approvals" description="Decisions waiting on you."
        actions={<div className="segmented"><button className={pendingOnly ? "on" : ""} onClick={() => setPendingOnly(true)}>Pending</button><button className={!pendingOnly ? "on" : ""} onClick={() => setPendingOnly(false)}>All</button></div>} />
      {isStaff(user) && <Tabs value={tab} onChange={setTab} tabs={[
        { value: "requests", label: "Service requests", count: requests.data?.count },
        { value: "changes", label: "Changes", count: changes.data?.length },
      ]} />}
      {tab === "requests" && <>
        {requests.isPending && <LoadingState />}
        {requests.data?.results.length === 0 && <EmptyState title="You're all caught up" message="No requests are waiting for your approval." />}
        <div className="tiles">
          {requests.data?.results.map((a) => (
            <Decision key={a.id} eyebrow={a.request_number ?? ""} title={a.subject} created={a.created_at} state={a.state} comment={a.comment}
              decide={(s, c) => decideApproval(a.id, s, c)} />
          ))}
        </div>
      </>}
      {tab === "changes" && <>
        {changes.isPending && <LoadingState />}
        {changes.data?.length === 0 && <EmptyState title="No change approvals" message="Changes needing your approval as a CAB member appear here." />}
        <div className="tiles">
          {changes.data?.map((a) => (
            <Decision key={a.id} eyebrow={a.change_number} title={a.change_title} link={`/changes/${a.change}`} created={a.created_at} state={a.state} comment={a.comment}
              decide={(s, c) => postAction(`${ENDPOINTS.changeApprovals}${a.id}/decide/`, { state: s, comment: c })} />
          ))}
        </div>
      </>}
    </>
  );
}
