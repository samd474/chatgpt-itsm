import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Circle, Plus } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  addTicketTask,
  getCategories,
  getCustomFields,
  getServices,
  getSupportGroups,
  getTechnicians,
  getTicket,
  getTicketApprovals,
  getTicketTasks,
  patchTicket,
  transitionTicket,
  updateTask,
  type TicketUpdateInput,
} from "../../api/tickets";
import { apiErrorMessage } from "../../api/client";
import { ArticlesPanel } from "../../components/ArticlesPanel";
import { AttachmentsPanel } from "../../components/AttachmentsPanel";
import { Pill, PriorityBadge, SlaBadge, StatusBadge } from "../../components/badges";
import { Conversation } from "../../components/Conversation";
import { CustomFieldsForm } from "../../components/DynamicField";
import { Card, ErrorState, Field, LoadingState, Notice, PageHeader } from "../../components/ui";
import type { Ticket, TicketStatus } from "../../types";
import { ALLOWED_TRANSITIONS, LEVELS, formatDate, statusLabel } from "../../utils/format";

const toId = (value: string) => (value === "" ? null : Number(value));

function Properties({ ticket, onSaved }: { ticket: Ticket; onSaved: (t: Ticket) => void }) {
  const [form, setForm] = useState<TicketUpdateInput>({});
  const [lastSaved, setLastSaved] = useState(ticket.updated_at);
  if (lastSaved !== ticket.updated_at) { setLastSaved(ticket.updated_at); setForm({}); }
  const value = { ...ticket, ...form };
  const groups = useQuery({ queryKey: ["lookup", "groups-simple"], queryFn: getSupportGroups });
  const categories = useQuery({ queryKey: ["lookup", "categories"], queryFn: getCategories });
  const services = useQuery({ queryKey: ["lookup", "services"], queryFn: getServices });
  const technicians = useQuery({ queryKey: ["lookup", "technicians", value.assignment_group], queryFn: () => getTechnicians(value.assignment_group) });
  const customDefs = useQuery({ queryKey: ["custom-fields", "ticket"], queryFn: () => getCustomFields("ticket") });
  const save = useMutation({ mutationFn: () => patchTicket(ticket.public_id, form), onSuccess: onSaved });
  const dirty = Object.keys(form).length > 0;

  return (
    <Card title="Properties" actions={dirty && <>
      <button className="btn btn-ghost btn-sm" onClick={() => setForm({})}>Discard</button>
      <button className="btn btn-primary btn-sm" disabled={save.isPending} onClick={() => save.mutate()}>Save</button>
    </>}>
      <div className="stack" style={{ gap: 12 }}>
        <Field label="Assignment group">
          <select className="select" value={value.assignment_group ?? ""} onChange={(e) => setForm((f) => ({ ...f, assignment_group: toId(e.target.value), technician: null }))}>
            <option value="">None</option>{groups.data?.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
        </Field>
        <Field label="Assignee">
          <select className="select" value={value.technician ?? ""} onChange={(e) => setForm((f) => ({ ...f, technician: toId(e.target.value) }))}>
            <option value="">Unassigned</option>{technicians.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </Field>
        <div className="grid-2">
          <Field label="Impact"><select className="select" value={value.impact} onChange={(e) => setForm((f) => ({ ...f, impact: Number(e.target.value) }))}>{LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}</select></Field>
          <Field label="Urgency"><select className="select" value={value.urgency} onChange={(e) => setForm((f) => ({ ...f, urgency: Number(e.target.value) }))}>{LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}</select></Field>
        </div>
        <Field label="Category">
          <select className="select" value={value.category ?? ""} onChange={(e) => setForm((f) => ({ ...f, category: toId(e.target.value) }))}>
            <option value="">None</option>{categories.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </Field>
        <Field label="Service">
          <select className="select" value={value.service ?? ""} onChange={(e) => setForm((f) => ({ ...f, service: toId(e.target.value) }))}>
            <option value="">None</option>{services.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </Field>
        {customDefs.data && customDefs.data.length > 0 && (
          <CustomFieldsForm defs={customDefs.data} values={(value.custom_fields ?? {}) as Record<string, unknown>}
            onChange={(cf) => setForm((f) => ({ ...f, custom_fields: cf }))} />
        )}
        {save.isError && <Notice tone="error">{apiErrorMessage(save.error)}</Notice>}
      </div>
    </Card>
  );
}

function Tasks({ publicId, onChange }: { publicId: string; onChange: () => void }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const tasks = useQuery({ queryKey: ["ticket-tasks", publicId], queryFn: () => getTicketTasks(publicId) });
  const refresh = async () => { await queryClient.invalidateQueries({ queryKey: ["ticket-tasks", publicId] }); onChange(); };
  const add = useMutation({ mutationFn: () => addTicketTask(publicId, { title }), onSuccess: async () => { setTitle(""); await refresh(); } });
  const toggle = useMutation({ mutationFn: ({ id, done }: { id: number; done: boolean }) => updateTask(id, { status: done ? "done" : "open" }), onSuccess: refresh });
  const done = tasks.data?.filter((t) => t.status === "done").length ?? 0;

  return (
    <Card title="Tasks" actions={tasks.data && tasks.data.length > 0 && <span className="subtle">{done}/{tasks.data.length} done</span>}>
      <div className="list">
        {tasks.data?.map((t) => (
          <div className="list-item" key={t.id}>
            <button className="btn btn-ghost btn-icon btn-sm" aria-label={t.status === "done" ? "Reopen task" : "Complete task"}
              onClick={() => toggle.mutate({ id: t.id, done: t.status !== "done" })}>
              {t.status === "done" ? <CheckCircle2 color="var(--green)" /> : <Circle />}
            </button>
            <span style={{ textDecoration: t.status === "done" ? "line-through" : undefined, color: t.status === "done" ? "var(--text-3)" : undefined }}>{t.title}</span>
            <span className="spacer" />
            {t.assignment_group_name && <span className="subtle">{t.assignment_group_name}</span>}
            {t.status === "cancelled" && <Pill value="cancelled" />}
          </div>
        ))}
      </div>
      <form className="row" style={{ marginTop: 8 }} onSubmit={(e) => { e.preventDefault(); if (title.trim()) add.mutate(); }}>
        <input className="input" style={{ flex: 1 }} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Add a task…" />
        <button className="btn btn-secondary" disabled={!title.trim() || add.isPending}><Plus />Add</button>
      </form>
      {(add.isError || toggle.isError) && <div style={{ marginTop: 8 }}><Notice tone="error">{apiErrorMessage(add.error ?? toggle.error)}</Notice></div>}
    </Card>
  );
}

export function TechnicianTicketPage() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const [target, setTarget] = useState<TicketStatus | "">("");
  const [resolutionCode, setResolutionCode] = useState("");
  const [resolutionBody, setResolutionBody] = useState("");
  const ticketQuery = useQuery({ queryKey: ["ticket", id], queryFn: () => getTicket(id), enabled: !!id });
  const approvals = useQuery({ queryKey: ["ticket-approvals", id], queryFn: () => getTicketApprovals(id), enabled: !!id });
  const refresh = () => Promise.all([
    queryClient.invalidateQueries({ queryKey: ["ticket", id] }),
    queryClient.invalidateQueries({ queryKey: ["tickets", "tech"] }),
  ]);
  const needsResolution = target === "resolved" || target === "closed";
  const transition = useMutation({
    mutationFn: () => transitionTicket(id, {
      status: target as TicketStatus,
      resolution_code: needsResolution ? resolutionCode : undefined,
      resolution_body: needsResolution ? resolutionBody : undefined,
    }),
    onSuccess: async () => { setTarget(""); await refresh(); },
  });

  if (ticketQuery.isPending) return <LoadingState />;
  if (ticketQuery.isError) return <ErrorState message={apiErrorMessage(ticketQuery.error)} />;
  const t = ticketQuery.data;
  const next = ALLOWED_TRANSITIONS[t.status];

  return (
    <>
      <PageHeader eyebrow={`${t.request_number} · ${t.request_type}`} title={t.subject}
        actions={<div className="row"><PriorityBadge priority={t.priority} /><StatusBadge status={t.status} /><SlaBadge sla={t.sla} /></div>} />
      <div className="grid-main">
        <div className="stack">
          <Card title="Description">
            <p className="pre-wrap">{t.description || "—"}</p>
            {Object.keys(t.request_payload).length > 0 && <pre style={{ marginTop: 12 }}>{JSON.stringify(t.request_payload, null, 2)}</pre>}
            {t.resolution_body && <div style={{ marginTop: 14 }}><h3>Resolution · {t.resolution_code || "no code"}</h3><p className="pre-wrap muted" style={{ marginTop: 4 }}>{t.resolution_body}</p></div>}
          </Card>
          <Tasks publicId={t.public_id} onChange={refresh} />
          <Conversation publicId={t.public_id} staff onPosted={refresh} />
        </div>
        <div className="stack">
          <Card title="Status">
            {next.length === 0 ? <p className="muted">This ticket is {statusLabel(t.status).toLowerCase()}.</p> : (
              <div className="stack" style={{ gap: 10 }}>
                <select className="select" value={target} onChange={(e) => setTarget(e.target.value as TicketStatus | "")} aria-label="New status">
                  <option value="">Move to…</option>{next.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
                </select>
                {needsResolution && <>
                  <input className="input" value={resolutionCode} onChange={(e) => setResolutionCode(e.target.value)} placeholder="Resolution code (e.g. fixed)" />
                  <textarea className="textarea" rows={3} value={resolutionBody} onChange={(e) => setResolutionBody(e.target.value)} placeholder="What fixed it? The requester sees this." />
                </>}
                {t.open_tasks > 0 && needsResolution && <Notice tone="warn">{t.open_tasks} task(s) still open.</Notice>}
                {transition.isError && <Notice tone="error">{apiErrorMessage(transition.error)}</Notice>}
                <button className="btn btn-primary" disabled={!target || transition.isPending || (needsResolution && !resolutionBody.trim() && !t.resolution_body)}
                  onClick={() => transition.mutate()}>Update status</button>
              </div>
            )}
          </Card>
          <Properties ticket={t} onSaved={(saved) => { queryClient.setQueryData(["ticket", id], saved); void refresh(); }} />
          <Card title="Details">
            <dl className="props">
              <dt>Requester</dt><dd>{t.requester_name}</dd>
              <dt>Opened</dt><dd>{formatDate(t.created_at)}</dd>
              <dt>First response</dt><dd>{formatDate(t.first_response_time)}</dd>
              {t.sla && <><dt>Response due</dt><dd>{formatDate(t.sla.response_due_at)}</dd><dt>Resolve by</dt><dd>{formatDate(t.sla.resolution_due_at)}</dd><dt>SLA policy</dt><dd>{t.sla.policy}</dd></>}
            </dl>
            {approvals.data && approvals.data.length > 0 && (
              <div className="list" style={{ marginTop: 12 }}>
                {approvals.data.map((a) => <div className="list-item" key={a.id}>{a.approver_name}<span className="spacer" /><Pill value={a.state} /></div>)}
              </div>
            )}
          </Card>
          <ArticlesPanel publicId={t.public_id} staff onUse={next.includes("resolved") ? (a) => {
            setTarget("resolved");
            setResolutionCode((code) => code || "knowledge-base");
            setResolutionBody(`${a.body}\n\n(From ${a.number}: ${a.title})`);
          } : undefined} />
          <AttachmentsPanel publicId={t.public_id} canUpload />
        </div>
      </div>
    </>
  );
}
