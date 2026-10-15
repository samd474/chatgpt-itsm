import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiErrorMessage } from "../../api/client";
import { createResource, getAction, getResource, postAction, updateResource, ENDPOINTS } from "../../api/resources";
import { getCustomFields } from "../../api/tickets";
import { useAuth } from "../../auth/context";
import { hasRole, isStaff } from "../../auth/roles";
import { ChangeStatusBadge, Pill } from "../../components/badges";
import type { FieldDef } from "../../components/form";
import { RecordEditor } from "../../components/RecordEditor";
import { Avatar, Card, ErrorState, Field, LoadingState, Notice, PageHeader } from "../../components/ui";
import type { Change, ChangeStatus } from "../../types";
import { formatDate, relativeTime } from "../../utils/format";

const CONTENT_FIELDS: FieldDef[] = [
  { name: "title", label: "Title", required: true, span: true },
  { name: "change_type", label: "Type", type: "select", required: true, options: [
    { value: "standard", label: "Standard (pre-approved)" }, { value: "normal", label: "Normal" }, { value: "emergency", label: "Emergency" }] },
  { name: "risk", label: "Risk", type: "select", required: true, options: [{ value: "low", label: "Low" }, { value: "medium", label: "Medium" }, { value: "high", label: "High" }] },
  { name: "impact", label: "Impact", type: "select", required: true, options: [{ value: 1, label: "1 - Critical" }, { value: 2, label: "2 - High" }, { value: 3, label: "3 - Medium" }] },
  { name: "service", label: "Affected service", type: "select", lookup: "services" },
  { name: "assignment_group", label: "Owning group", type: "select", lookup: "groups" },
  { name: "assets", label: "Affected assets", type: "multiselect", lookup: "assets" },
  { name: "description", label: "Description", type: "textarea", required: true },
  { name: "justification", label: "Business justification", type: "textarea" },
  { name: "implementation_plan", label: "Implementation plan", type: "textarea" },
  { name: "backout_plan", label: "Backout plan", type: "textarea" },
  { name: "test_plan", label: "Test plan", type: "textarea" },
];
const SCHEDULE_FIELDS: FieldDef[] = [
  { name: "implementer", label: "Implementer", type: "select", lookup: "staff" },
  { name: "planned_start", label: "Planned start", type: "datetime" },
  { name: "planned_end", label: "Planned end", type: "datetime" },
];

const ACTIONS: Partial<Record<ChangeStatus, { to: ChangeStatus; label: string; primary?: boolean }[]>> = {
  draft: [{ to: "awaiting_approval", label: "Submit for approval", primary: true }, { to: "cancelled", label: "Cancel" }],
  awaiting_approval: [{ to: "cancelled", label: "Withdraw" }],
  approved: [{ to: "scheduled", label: "Schedule", primary: true }, { to: "cancelled", label: "Cancel" }],
  scheduled: [{ to: "implementing", label: "Start implementation", primary: true }, { to: "approved", label: "Unschedule" }, { to: "cancelled", label: "Cancel" }],
  implementing: [{ to: "review", label: "Finish implementation", primary: true }],
  review: [{ to: "closed", label: "Close change", primary: true }],
  rejected: [{ to: "draft", label: "Rework as draft", primary: true }, { to: "cancelled", label: "Cancel" }],
};

function Lifecycle({ change, onDone }: { change: Change; onDone: (c: Change) => void }) {
  const [outcome, setOutcome] = useState("successful");
  const [notes, setNotes] = useState(change.closure_notes);
  const mutation = useMutation({
    mutationFn: (to: ChangeStatus) => postAction<Change>(`${ENDPOINTS.changes}${change.id}/transition/`, {
      status: to, ...(to === "review" ? { outcome } : {}), ...(to === "closed" ? { closure_notes: notes } : {}),
    }),
    onSuccess: onDone,
  });
  const actions = ACTIONS[change.status] ?? [];
  return (
    <Card title="Lifecycle">
      <div className="stack" style={{ gap: 10 }}>
        <div className="row"><ChangeStatusBadge status={change.status} /><span className="spacer" /><span className="subtle">updated {relativeTime(change.updated_at)}</span></div>
        {change.status === "implementing" && <Field label="Outcome"><select className="select" value={outcome} onChange={(e) => setOutcome(e.target.value)}>
          <option value="successful">Successful</option><option value="partial">Partially successful</option><option value="failed">Failed</option><option value="backed_out">Backed out</option>
        </select></Field>}
        {change.status === "review" && <Field label="Post-implementation review"><textarea className="textarea" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="What happened, lessons learned" /></Field>}
        {change.outcome && <div className="row"><span className="subtle">Outcome</span><Pill value={change.outcome} /></div>}
        {mutation.isError && <Notice tone="error">{apiErrorMessage(mutation.error)}</Notice>}
        {actions.length === 0 ? <p className="subtle">No further actions.</p> : (
          <div className="row">{actions.map((a) => (
            <button key={a.to} className={`btn ${a.primary ? "btn-primary" : a.to === "cancelled" ? "btn-danger" : "btn-secondary"}`} disabled={mutation.isPending}
              onClick={() => mutation.mutate(a.to)}>{a.label}</button>
          ))}</div>
        )}
      </div>
    </Card>
  );
}

export function ChangeDetailPage() {
  const { id = "" } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const change = useQuery({ queryKey: ["change", id], enabled: !isNew, queryFn: () => getResource<Change>(ENDPOINTS.changes, id) });
  const conflicts = useQuery({ queryKey: ["change-conflicts", id], enabled: !isNew && !!change.data?.planned_start,
    queryFn: () => getAction<{ id: number; number: string; title: string; planned_start: string }[]>(`${ENDPOINTS.changes}${id}/conflicts/`) });
  const customDefs = useQuery({ queryKey: ["custom-fields", "change"], queryFn: () => getCustomFields("change") });
  const setChange = (c: Change) => { queryClient.setQueryData(["change", id], c); void queryClient.invalidateQueries({ queryKey: ["changes"] }); void conflicts.refetch(); };

  if (!isNew && change.isPending) return <LoadingState />;
  if (!isNew && change.isError) return <ErrorState message={apiErrorMessage(change.error)} />;
  if (customDefs.isPending) return <LoadingState />;
  const c = change.data;
  const manager = hasRole(user, "Manager", "Administrator");
  const contentEditable = isNew || (!!c && ["draft", "rejected"].includes(c.status) && (c.requested_by === user?.id || manager));
  const scheduleEditable = !!c && manager && (["draft", "rejected", "approved"].includes(c.status));

  return (
    <>
      <PageHeader eyebrow={c?.number ?? "Changes"} title={c?.title ?? "New change"}
        description={c && <>Requested by {c.requested_by_name} · {relativeTime(c.created_at)}</>}
        actions={c && <><Pill value={c.change_type} /><ChangeStatusBadge status={c.status} /></>} />
      <div className="grid-main">
        <div className="stack">
          {c && c.conflict_count > 0 && <Notice tone="warn"><AlertTriangle size={14} /> This window overlaps {c.conflict_count} scheduled change(s) touching the same assets or service.</Notice>}
          <RecordEditor<Change>
            key={c?.updated_at ?? "new"}
            title="Change"
            fields={CONTENT_FIELDS}
            record={c ? (c as unknown as Record<string, unknown>) : null}
            customDefs={customDefs.data}
            readOnly={!contentEditable || !isStaff(user)}
            saveLabel={isNew ? "Create draft" : "Save changes"}
            save={(payload) => (isNew ? createResource<Change>(ENDPOINTS.changes, payload) : updateResource<Change>(ENDPOINTS.changes, id, payload))}
            onSaved={(saved) => { if (isNew) navigate(`/changes/${saved.id}`, { replace: true }); else setChange(saved); }}
          />
        </div>
        {c && (
          <div className="stack">
            <Lifecycle change={c} onDone={setChange} />
            <RecordEditor<Change> key={`s${c.updated_at}`} title="Schedule" fields={SCHEDULE_FIELDS} record={c as unknown as Record<string, unknown>}
              readOnly={!scheduleEditable} save={(payload) => updateResource<Change>(ENDPOINTS.changes, c.id, payload)} onSaved={setChange} />
            <Card title="Approvals">
              {c.approvals.length === 0 && <p className="subtle">{c.change_type === "standard" ? "Standard changes are pre-approved." : "Requested when the change is submitted."}</p>}
              <div className="list">
                {c.approvals.map((a) => (
                  <div className="list-item" key={a.id}><Avatar name={a.approver_name} />{a.approver_name}<span className="spacer" /><Pill value={a.state} /></div>
                ))}
              </div>
            </Card>
            {conflicts.data && conflicts.data.length > 0 && (
              <Card title="Conflicts">
                <div className="list">{conflicts.data.map((x) => <div className="list-item" key={x.id}><Link to={`/changes/${x.id}`}>{x.number}</Link><span className="title-cell muted">{x.title}</span><span className="spacer" /><span className="subtle">{formatDate(x.planned_start)}</span></div>)}</div>
              </Card>
            )}
            {(c.actual_start || c.actual_end) && <Card title="Actuals"><dl className="props"><dt>Started</dt><dd>{formatDate(c.actual_start)}</dd><dt>Finished</dt><dd>{formatDate(c.actual_end)}</dd></dl>{c.closure_notes && <p className="pre-wrap muted" style={{ marginTop: 10 }}>{c.closure_notes}</p>}</Card>}
          </div>
        )}
      </div>
    </>
  );
}
