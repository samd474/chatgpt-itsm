import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  addComment,
  getCategories,
  getComments,
  getServices,
  getSupportGroups,
  getTechnicians,
  getTicket,
  getTicketApprovals,
  patchTicket,
  transitionTicket,
  type TicketUpdateInput,
} from "../../api/tickets";
import { apiErrorMessage } from "../../api/client";
import { AttachmentsPanel } from "../../components/AttachmentsPanel";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { SlaBadge } from "../../components/SlaBadge";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import type { Ticket, TicketStatus } from "../../types";
import { ALLOWED_TRANSITIONS, LEVELS, formatDate, statusLabel } from "../../utils/format";

const toId = (value: string) => (value === "" ? null : Number(value));

function AssignmentPanel({ ticket, onSaved }: { ticket: Ticket; onSaved: (t: Ticket) => void }) {
  const [form, setForm] = useState<TicketUpdateInput>({});
  useEffect(() => setForm({}), [ticket.updated_at]);
  const value = { ...ticket, ...form };
  const groups = useQuery({ queryKey: ["lookup", "groups"], queryFn: getSupportGroups });
  const categories = useQuery({ queryKey: ["lookup", "categories"], queryFn: getCategories });
  const services = useQuery({ queryKey: ["lookup", "services"], queryFn: getServices });
  const technicians = useQuery({
    queryKey: ["lookup", "technicians", value.assignment_group],
    queryFn: () => getTechnicians(value.assignment_group),
  });
  const save = useMutation({ mutationFn: () => patchTicket(ticket.public_id, form), onSuccess: onSaved });
  const dirty = Object.keys(form).length > 0;

  return (
    <div className="panel">
      <h2>Classification and assignment</h2>
      <div className="form-grid">
        <label>Assignment group
          <select value={value.assignment_group ?? ""} onChange={(e) => setForm((f) => ({ ...f, assignment_group: toId(e.target.value), technician: null }))}>
            <option value="">None</option>
            {groups.data?.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
        </label>
        <label>Technician
          <select value={value.technician ?? ""} onChange={(e) => setForm((f) => ({ ...f, technician: toId(e.target.value) }))}>
            <option value="">Unassigned</option>
            {technicians.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </label>
        <label>Category
          <select value={value.category ?? ""} onChange={(e) => setForm((f) => ({ ...f, category: toId(e.target.value) }))}>
            <option value="">None</option>
            {categories.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
        <label>Service
          <select value={value.service ?? ""} onChange={(e) => setForm((f) => ({ ...f, service: toId(e.target.value) }))}>
            <option value="">None</option>
            {services.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>
        <label>Impact
          <select value={value.impact} onChange={(e) => setForm((f) => ({ ...f, impact: Number(e.target.value) }))}>
            {LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
          </select>
        </label>
        <label>Urgency
          <select value={value.urgency} onChange={(e) => setForm((f) => ({ ...f, urgency: Number(e.target.value) }))}>
            {LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
          </select>
        </label>
      </div>
      <p className="help-text">Priority is recalculated by the server from impact and urgency.</p>
      {save.isError && <div className="alert alert--error">{apiErrorMessage(save.error)}</div>}
      <button className="button" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>Save changes</button>
    </div>
  );
}

export function TechnicianTicketPage() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"public" | "private">("private");
  const [body, setBody] = useState("");
  const [targetStatus, setTargetStatus] = useState<TicketStatus | "">("");
  const [resolutionCode, setResolutionCode] = useState("");
  const [resolutionBody, setResolutionBody] = useState("");
  const ticketQuery = useQuery({ queryKey: ["ticket", id], queryFn: () => getTicket(id), enabled: !!id });
  const commentsQuery = useQuery({ queryKey: ["ticket-comments", id], queryFn: () => getComments(id), enabled: !!id });
  const approvalsQuery = useQuery({ queryKey: ["ticket-approvals", id], queryFn: () => getTicketApprovals(id), enabled: !!id });

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["ticket", id] }),
      queryClient.invalidateQueries({ queryKey: ["ticket-comments", id] }),
      queryClient.invalidateQueries({ queryKey: ["tickets", "tech"] }),
    ]);
  };
  const commentMutation = useMutation({
    mutationFn: () => addComment(id, { body, visibility: mode }),
    onSuccess: async () => { setBody(""); await refresh(); },
  });
  const needsResolution = targetStatus === "resolved" || targetStatus === "closed";
  const transitionMutation = useMutation({
    mutationFn: () => transitionTicket(id, {
      status: targetStatus as TicketStatus,
      resolution_code: needsResolution ? resolutionCode : undefined,
      resolution_body: needsResolution ? resolutionBody : undefined,
    }),
    onSuccess: async () => { setTargetStatus(""); await refresh(); },
  });

  if (ticketQuery.isPending) return <LoadingState />;
  if (ticketQuery.isError) return <ErrorState message={apiErrorMessage(ticketQuery.error)} />;
  const ticket = ticketQuery.data;
  const nextStatuses = ALLOWED_TRANSITIONS[ticket.status];

  return (
    <section>
      <div className="page-heading">
        <div><div className="eyebrow">{ticket.request_number} · {ticket.request_type}</div><h1>{ticket.subject}</h1></div>
        <div className="badge-row"><PriorityBadge priority={ticket.priority} /><StatusBadge status={ticket.status} /><SlaBadge sla={ticket.sla} /></div>
      </div>

      <div className="detail-grid">
        <div className="panel">
          <h2>Description</h2>
          <p className="pre-wrap">{ticket.description || "-"}</p>
          {Object.keys(ticket.request_payload).length > 0 && <><h3>Request data</h3><pre>{JSON.stringify(ticket.request_payload, null, 2)}</pre></>}
          {ticket.resolution_body && <><h3>Resolution ({ticket.resolution_code || "no code"})</h3><p className="pre-wrap">{ticket.resolution_body}</p></>}
        </div>
        <div className="panel">
          <h2>Ticket fields</h2>
          <dl>
            <dt>Requester</dt><dd>{ticket.requester_name}</dd>
            <dt>Assignee</dt><dd>{ticket.technician_name ?? "Unassigned"}</dd>
            <dt>Group</dt><dd>{ticket.assignment_group_name ?? "None"}</dd>
            <dt>Priority</dt><dd>P{ticket.priority} (impact {ticket.impact}, urgency {ticket.urgency})</dd>
            <dt>Created</dt><dd>{formatDate(ticket.created_at)}</dd>
            <dt>First response</dt><dd>{formatDate(ticket.first_response_time)}</dd>
            {ticket.sla && <><dt>Response due</dt><dd>{formatDate(ticket.sla.response_due_at)}</dd>
              <dt>Resolution due</dt><dd>{formatDate(ticket.sla.resolution_due_at)}</dd></>}
          </dl>
          {approvalsQuery.data && approvalsQuery.data.length > 0 && <>
            <h3>Approvals</h3>
            <ul className="file-list">{approvalsQuery.data.map((a) => <li key={a.id}>{a.approver_name}: <strong>{a.state}</strong>{a.comment && ` - ${a.comment}`}</li>)}</ul>
          </>}
        </div>
      </div>

      <AssignmentPanel ticket={ticket} onSaved={(t) => { queryClient.setQueryData(["ticket", id], t); void refresh(); }} />

      <div className="panel">
        <h2>Conversation and private notes</h2>
        {commentsQuery.isError && <ErrorState message={apiErrorMessage(commentsQuery.error)} />}
        <div className="timeline">
          {commentsQuery.data?.map((item) => (
            <article key={item.id} className={`timeline-item ${item.visibility === "private" ? "timeline-item--private" : ""}`}>
              <div><strong>{item.author_name || `User ${item.author}`}</strong> <span className="badge">{item.visibility}</span> <span className="muted">{formatDate(item.created_at)}</span></div>
              <p className="pre-wrap">{item.body}</p>
            </article>
          ))}
        </div>
        {/* Deliberately explicit: posting an internal note publicly can leak sensitive details. */}
        <div className="segmented" role="group" aria-label="Comment visibility">
          <button className={mode === "private" ? "selected" : ""} onClick={() => setMode("private")}>Private note</button>
          <button className={mode === "public" ? "selected" : ""} onClick={() => setMode("public")}>Public reply</button>
        </div>
        <textarea rows={5} value={body} onChange={(e) => setBody(e.target.value)} className={mode === "public" ? "textarea--public" : ""}
          placeholder={mode === "private" ? "Visible only to staff" : "Visible to the requester"} />
        {commentMutation.isError && <div className="alert alert--error">{apiErrorMessage(commentMutation.error)}</div>}
        <button className="button" disabled={!body.trim() || commentMutation.isPending} onClick={() => commentMutation.mutate()}>
          {mode === "private" ? "Add private note" : "Send public reply to requester"}
        </button>
      </div>

      <AttachmentsPanel publicId={ticket.public_id} canUpload />

      <div className="panel">
        <h2>Change status</h2>
        {nextStatuses.length === 0 ? <p className="muted">This ticket is {statusLabel(ticket.status).toLowerCase()} and cannot change further.</p> : <>
          <div className="form-grid">
            <label>New status
              <select value={targetStatus} onChange={(e) => setTargetStatus(e.target.value as TicketStatus | "")}>
                <option value="">Choose...</option>
                {nextStatuses.map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}
              </select>
            </label>
            {needsResolution && <>
              <label>Resolution code<input value={resolutionCode} onChange={(e) => setResolutionCode(e.target.value)} placeholder="e.g. fixed, workaround" /></label>
              <label className="grid-span">Resolution notes<textarea rows={4} value={resolutionBody} onChange={(e) => setResolutionBody(e.target.value)} /></label>
            </>}
          </div>
          {transitionMutation.isError && <div className="alert alert--error">{apiErrorMessage(transitionMutation.error)}</div>}
          <button className="button" disabled={!targetStatus || transitionMutation.isPending || (needsResolution && !resolutionBody.trim() && !ticket.resolution_body)}
            onClick={() => transitionMutation.mutate()}>Apply transition</button>
        </>}
      </div>
    </section>
  );
}
