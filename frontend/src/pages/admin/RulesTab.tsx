import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { apiErrorMessage } from "../../api/client";
import { deleteRule, listRules, previewRule, saveRule, type RuleInput } from "../../api/rules";
import { getCategories, getServices, getSupportGroups } from "../../api/tickets";
import { MultiSelect } from "../../components/MultiSelect";
import { Badge, Card, DataTable, Drawer, EmptyState, ErrorState, Field, LoadingState, Notice } from "../../components/ui";
import type { Lookup, RuleActions, RuleConditions, RulePreview, RuleRunsOn, RuleWatchedField, TicketRule, TicketStatus } from "../../types";
import { LEVELS, statusLabel } from "../../utils/format";

const BLANK: RuleInput = { name: "", description: "", position: 0, active: true, stop_processing: false, runs_on: "created", conditions: {}, actions: {} };
const STATUSES: TicketStatus[] = ["new", "assigned", "in_progress", "pending_user_response", "resolved", "closed", "cancelled"];
const WATCHED: { value: RuleWatchedField; label: string }[] = [
  { value: "status", label: "Status" }, { value: "category", label: "Category" }, { value: "service", label: "Service" },
  { value: "impact", label: "Impact" }, { value: "urgency", label: "Urgency" }, { value: "priority", label: "Priority" },
  { value: "assignment_group", label: "Assignment group" }, { value: "technician", label: "Assignee" },
];
const TRIGGERS: Record<RuleRunsOn, string> = { created: "a ticket is created", updated: "a ticket is updated", both: "a ticket is created or updated" };
const watchedName = (f: string) => WATCHED.find((w) => w.value === f)?.label.toLowerCase() ?? f;
const levelName = (v: number) => LEVELS.find((l) => l.value === v)?.label.replace(/^\d - /, "") ?? String(v);

// Drop empty values so the API only sees conditions and actions that were actually chosen.
function clean<T extends object>(obj: T): T {
  return Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== undefined && v !== null && v !== "" && !(Array.isArray(v) && v.length === 0))) as T;
}

function useLookups() {
  const groups = useQuery({ queryKey: ["lookup", "groups-simple"], queryFn: getSupportGroups });
  const categories = useQuery({ queryKey: ["lookup", "categories"], queryFn: getCategories });
  const services = useQuery({ queryKey: ["lookup", "services"], queryFn: getServices });
  const name = (rows: Lookup[] | undefined, id: number | undefined) => rows?.find((r) => r.id === id)?.name ?? `#${id}`;
  return { groups: groups.data ?? [], categories: categories.data ?? [], services: services.data ?? [], name };
}

function Summary({ rule }: { rule: TicketRule }) {
  const { groups, categories, services, name } = useLookups();
  const c = rule.conditions, a = rule.actions;
  const when = [
    c.changed?.length && `its ${c.changed.map(watchedName).join(" or ")} changed`,
    c.status?.length && `status is ${c.status.map((s) => statusLabel(s)).join(" or ")}`,
    c.request_type && `type is ${c.request_type}`,
    c.keywords?.length && `mentions ${c.keywords.map((k) => `"${k}"`).join(" or ")}`,
    c.category?.length && `category is ${c.category.map((id) => name(categories, id)).join(" or ")}`,
    c.service?.length && `service is ${c.service.map((id) => name(services, id)).join(" or ")}`,
    c.impact?.length && `impact is ${c.impact.map(levelName).join(" or ")}`,
    c.urgency?.length && `urgency is ${c.urgency.map(levelName).join(" or ")}`,
  ].filter(Boolean);
  const then = [
    a.set_assignment_group && `route to ${name(groups, a.set_assignment_group)}`,
    a.set_category && `set category ${name(categories, a.set_category)}`,
    a.set_service && `set service ${name(services, a.set_service)}`,
    a.set_impact && `impact ${levelName(a.set_impact)}`,
    a.set_urgency && `urgency ${levelName(a.set_urgency)}`,
    a.notify_group && `notify ${name(groups, a.notify_group)}`,
    a.add_note && "add a private note",
  ].filter(Boolean);
  const trigger = TRIGGERS[rule.runs_on ?? "created"];
  return <span className="muted">When {trigger}{when.length > 0 && ` and ${when.join(" and ")}`}: {then.join(", ")}{rule.stop_processing && "; then stop"}</span>;
}

function Select({ label, value, options, onChange, placeholder = "Don't change" }: {
  label: string; value: number | undefined; options: { value: number; label: string }[]; onChange: (v: number | undefined) => void; placeholder?: string;
}) {
  return (
    <Field label={label}>
      <select className="select" value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value))}>
        <option value="">{placeholder}</option>{options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </Field>
  );
}

function RuleEditor({ rule, onClose, onSaved }: { rule: TicketRule | null; onClose: () => void; onSaved: () => void }) {
  const { groups, categories, services } = useLookups();
  const [form, setForm] = useState<RuleInput>(() => rule ? { ...rule } : BLANK);
  const [keywords, setKeywords] = useState((rule?.conditions.keywords ?? []).join("\n"));
  const setCondition = <K extends keyof RuleConditions>(key: K, value: RuleConditions[K]) => setForm((f) => ({ ...f, conditions: { ...f.conditions, [key]: value } }));
  const setAction = <K extends keyof RuleActions>(key: K, value: RuleActions[K]) => setForm((f) => ({ ...f, actions: { ...f.actions, [key]: value } }));
  const opts = (rows: Lookup[]) => rows.map((r) => ({ value: r.id, label: r.name }));
  const levelOpts = LEVELS.map((l) => ({ value: l.value, label: l.label }));
  const payload = (): Pick<RuleInput, "conditions" | "actions"> => ({
    conditions: clean({
      ...form.conditions,
      keywords: keywords.split("\n").map((k) => k.trim()).filter(Boolean),
      // "changed" only means something for rules that run on updates.
      changed: form.runs_on === "created" ? undefined : form.conditions.changed,
    }),
    actions: clean(form.actions),
  });
  const save = useMutation({ mutationFn: () => saveRule(rule?.id ?? null, { ...form, ...payload() }), onSuccess: onSaved });
  const [preview, setPreview] = useState<RulePreview | null>(null);
  const runPreview = useMutation({
    mutationFn: () => { const p = payload(); return previewRule(p.conditions, p.actions); },
    onSuccess: setPreview,
  });
  const remove = useMutation({ mutationFn: () => deleteRule(rule!.id), onSuccess: onSaved });
  const c = form.conditions, a = form.actions;

  return (
    <Drawer title={rule ? "Edit rule" : "New rule"} onClose={onClose} footer={<>
      {rule && <button className="btn btn-ghost" disabled={remove.isPending} onClick={() => remove.mutate()}>Delete</button>}
      <span className="spacer" />
      <button className="btn btn-secondary" disabled={runPreview.isPending} onClick={() => runPreview.mutate()}>Preview</button>
      <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
      <button className="btn btn-primary" disabled={!form.name.trim() || save.isPending} onClick={() => save.mutate()}>Save</button>
    </>}>
      <div className="stack" style={{ gap: 12 }}>
        <Field label="Name"><input className="input" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} /></Field>
        <Field label="Description"><input className="input" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} /></Field>
        <div className="grid-2">
          <Field label="Order" hint="Lower runs first."><input className="input" type="number" min={0} value={form.position} onChange={(e) => setForm((f) => ({ ...f, position: Number(e.target.value) }))} /></Field>
          <div className="stack" style={{ gap: 6, paddingTop: 22 }}>
            <label className="checkbox"><input type="checkbox" checked={form.active} onChange={(e) => setForm((f) => ({ ...f, active: e.target.checked }))} />Active</label>
            <label className="checkbox"><input type="checkbox" checked={form.stop_processing} onChange={(e) => setForm((f) => ({ ...f, stop_processing: e.target.checked }))} />Stop here when this rule matches</label>
          </div>
        </div>

        <Field label="Runs">
          <select className="select" aria-label="Runs" value={form.runs_on} onChange={(e) => setForm((f) => ({ ...f, runs_on: e.target.value as RuleRunsOn }))}>
            <option value="created">When a ticket is created</option><option value="updated">When a ticket is updated</option><option value="both">Both</option>
          </select>
        </Field>

        <h3>When the ticket matches all of</h3>
        {form.runs_on !== "created" && (
          <Field label="On update, only when this changed" hint={form.runs_on === "updated" ? "Required, so the rule doesn't fire on every edit." : "Ignored when the ticket is created."}>
            <MultiSelect options={WATCHED} value={c.changed ?? []} onChange={(v) => setCondition("changed", v as RuleWatchedField[])} placeholder="Pick fields" />
          </Field>
        )}
        <Field label="Status is any of">
          <MultiSelect options={STATUSES.map((s) => ({ value: s, label: statusLabel(s) }))} value={c.status ?? []}
            onChange={(v) => setCondition("status", v as TicketStatus[])} placeholder="Any status" />
        </Field>
        <Field label="Type">
          <select className="select" value={c.request_type ?? ""} onChange={(e) => setCondition("request_type", (e.target.value || undefined) as RuleConditions["request_type"])}>
            <option value="">Any</option><option value="incident">Incident</option><option value="request">Request</option>
          </select>
        </Field>
        <Field label="Mentions any of" hint="One phrase per line; matched in the subject or description, ignoring case.">
          <textarea className="textarea" rows={3} value={keywords} onChange={(e) => setKeywords(e.target.value)} aria-label="Keywords" />
        </Field>
        <Field label="Category is any of"><MultiSelect options={opts(categories)} value={c.category ?? []} onChange={(v) => setCondition("category", v.map(Number))} placeholder="Any category" /></Field>
        <Field label="Service is any of"><MultiSelect options={opts(services)} value={c.service ?? []} onChange={(v) => setCondition("service", v.map(Number))} placeholder="Any service" /></Field>
        <div className="grid-2">
          <Field label="Impact is any of"><MultiSelect options={levelOpts} value={c.impact ?? []} onChange={(v) => setCondition("impact", v.map(Number))} placeholder="Any" /></Field>
          <Field label="Urgency is any of"><MultiSelect options={levelOpts} value={c.urgency ?? []} onChange={(v) => setCondition("urgency", v.map(Number))} placeholder="Any" /></Field>
        </div>

        <h3>Then</h3>
        <Select label="Route to group" value={a.set_assignment_group} options={opts(groups)} onChange={(v) => setAction("set_assignment_group", v)} />
        <div className="grid-2">
          <Select label="Set category" value={a.set_category} options={opts(categories)} onChange={(v) => setAction("set_category", v)} />
          <Select label="Set service" value={a.set_service} options={opts(services)} onChange={(v) => setAction("set_service", v)} />
          <Select label="Set impact" value={a.set_impact} options={levelOpts} onChange={(v) => setAction("set_impact", v)} />
          <Select label="Set urgency" value={a.set_urgency} options={levelOpts} onChange={(v) => setAction("set_urgency", v)} />
        </div>
        <Select label="Email a group" value={a.notify_group} options={opts(groups)} onChange={(v) => setAction("notify_group", v)} placeholder="No one" />
        <Field label="Add a private note" hint="Staff only; requesters never see it.">
          <textarea className="textarea" rows={3} value={a.add_note ?? ""} onChange={(e) => setAction("add_note", e.target.value)} />
        </Field>
        {(save.isError || remove.isError || runPreview.isError) && <Notice tone="error">{apiErrorMessage(save.error ?? remove.error ?? runPreview.error)}</Notice>}
        {preview && <PreviewResult preview={preview} />}
      </div>
    </Drawer>
  );
}

function PreviewResult({ preview }: { preview: RulePreview }) {
  const describe = (c: RulePreview["tickets"][number]["changes"][number]) =>
    c.field === "notify" ? `email ${c.to}` : c.field === "note" ? "add a private note"
      : `${c.field.replace("_", " ")}: ${c.from ?? "none"} → ${c.to ?? "none"}`;
  return (
    <div className="stack" style={{ gap: 8 }} aria-live="polite">
      <h3>Preview</h3>
      <p className="muted">Would match {preview.matched} of the last {preview.scanned} tickets, judged on their current values. Nothing was changed.</p>
      {preview.ignored_conditions.length > 0 && <Notice tone="info">"Changed" conditions can't be judged after the fact, so the preview ignores them.</Notice>}
      <div className="list">
        {preview.tickets.map((t) => (
          <div className="list-item" key={t.public_id} style={{ alignItems: "flex-start" }}>
            <span className="subtle">{t.request_number}</span>
            <span className="stack" style={{ gap: 2 }}>
              <span>{t.subject}</span>
              <span className="subtle">{t.changes.length ? t.changes.map(describe).join(" · ") : "Already matches; nothing would change"}</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Ticket automation: ordered rules that run when tickets are created and/or updated. */
export function RulesTab() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<TicketRule | "new" | null>(null);
  const rules = useQuery({ queryKey: ["ticket-rules"], queryFn: listRules });
  const onSaved = async () => { setEditing(null); await queryClient.invalidateQueries({ queryKey: ["ticket-rules"] }); };

  return (
    <Card title="Automation rules" flush actions={<button className="btn btn-primary btn-sm" onClick={() => setEditing("new")}><Plus />New rule</button>}>
      <div className="card-body muted">
        Rules run in order when a ticket is created or updated, as each rule chooses. Every matching rule applies its actions
        (later rules win), unless a rule says to stop. They run after templates, so they can override a template's routing,
        and a rule's own changes never trigger other update rules.
      </div>
      {rules.isPending && <LoadingState rows={3} />}
      {rules.isError && <div className="card-body"><ErrorState message={apiErrorMessage(rules.error)} /></div>}
      {rules.data && (
        <DataTable rows={rules.data} rowKey={(r) => r.id} onRowClick={(r) => setEditing(r)}
          empty={<EmptyState title="No rules yet" message="New tickets are routed only by templates and staff." />}
          columns={[
            { key: "p", label: "Order", className: "num", render: (r) => r.position },
            { key: "n", label: "Rule", render: (r) => <div className="stack" style={{ gap: 2 }}><strong>{r.name}</strong><Summary rule={r} /></div> },
            { key: "a", label: "Status", render: (r) => (r.active ? <Badge tone="green" dot>Active</Badge> : <Badge tone="gray">Off</Badge>) },
          ]} />
      )}
      {editing && <RuleEditor rule={editing === "new" ? null : editing} onClose={() => setEditing(null)} onSaved={onSaved} />}
    </Card>
  );
}
