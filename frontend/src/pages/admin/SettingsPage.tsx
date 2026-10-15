import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { confirmImport, uploadImport } from "../../api/operations";
import { apiErrorMessage } from "../../api/client";
import { ENDPOINTS } from "../../api/resources";

import type { FieldDef, Option } from "../../components/form";
import { ResourceManager } from "../../components/ResourceManager";
import { Badge, Card, Field, Notice, PageHeader, Tabs } from "../../components/ui";
import type { ImportJob } from "../../types";
import { LEVELS } from "../../utils/format";

type Row = { id: number } & Record<string, unknown>;
const levels: Option[] = LEVELS.map((l) => ({ value: l.value, label: l.label }));
const active = (r: Row) => (r.active === false ? <Badge>Inactive</Badge> : <Badge tone="green" dot>Active</Badge>);
const activeField: FieldDef = { name: "active", label: "Active", type: "checkbox", span: true };
const EVENTS = ["ticket.created", "ticket.assigned", "ticket.public_comment", "ticket.resolved", "sla.warning", "sla.breached",
  "approval.requested", "approval.approved", "approval.rejected", "contract.renewal_due", "change.approval_requested",
  "change.approved", "change.rejected", "change.scheduled", "project.task_assigned"];

function CsvImport() {
  const [kind, setKind] = useState<ImportJob["kind"]>("categories");
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<ImportJob | null>(null);
  const upload = useMutation({ mutationFn: () => uploadImport(kind, file as File), onSuccess: setJob });
  const confirm = useMutation({ mutationFn: () => confirmImport((job as ImportJob).id), onSuccess: setJob });
  return (
    <Card title="CSV import">
      <div className="stack">
        <p className="muted">Upload, review the preview, then confirm. Nothing changes until you confirm.</p>
        <div className="form-grid">
          <Field label="Import" hint={kind === "categories" ? "Columns: name,parent,active" : "Columns: name,owner_group,active"}>
            <select className="select" value={kind} onChange={(e) => { setKind(e.target.value as ImportJob["kind"]); setJob(null); }}>
              <option value="categories">Categories</option><option value="services">Services</option>
            </select>
          </Field>
          <Field label="CSV file"><input className="input" type="file" accept=".csv,text/csv" style={{ paddingTop: 5 }} onChange={(e) => { setFile(e.target.files?.[0] ?? null); setJob(null); }} /></Field>
        </div>
        <div><button className="btn btn-secondary" disabled={!file || upload.isPending} onClick={() => upload.mutate()}>Validate file</button></div>
        {upload.isError && <Notice tone="error">{apiErrorMessage(upload.error)}</Notice>}
        {job && (
          <div className="stack" style={{ gap: 8 }}>
            <div className="row"><Badge tone="green">{job.preview.valid.length} valid</Badge><Badge tone="red">{job.preview.errors.length} errors</Badge><Badge tone="amber">{job.preview.warnings.length} warnings</Badge></div>
            {job.preview.errors.map((e) => <div key={`e${e.row}`} className="field-error">Row {e.row}: {e.error}</div>)}
            {job.preview.warnings.map((w, i) => <div key={`w${i}`} className="subtle">Row {w.row}: {w.warning}</div>)}
            {job.state === "validated"
              ? <div><button className="btn btn-primary" disabled={confirm.isPending || job.preview.valid.length === 0} onClick={() => confirm.mutate()}>Import {job.preview.valid.length} rows</button></div>
              : <Notice tone="success">Imported: {job.result.created} created, {job.result.updated} updated.</Notice>}
            {confirm.isError && <Notice tone="error">{apiErrorMessage(confirm.error)}</Notice>}
          </div>
        )}
      </div>
    </Card>
  );
}

type TabKey = "catalog" | "slas" | "calendars" | "notifications" | "assets" | "import";

export function SettingsPage() {
  const [tab, setTab] = useState<TabKey>("catalog");
  return (
    <>
      <PageHeader title="Settings" description="Service catalog, SLAs, notifications, asset setup and data import."
        actions={<a className="btn btn-secondary" href="/admin/" target="_blank" rel="noreferrer">Advanced (Django admin)</a>} />
      <Tabs value={tab} onChange={setTab} tabs={[
        { value: "catalog", label: "Service catalog" }, { value: "slas", label: "SLA policies" }, { value: "calendars", label: "Business hours" },
        { value: "notifications", label: "Email templates" }, { value: "assets", label: "Asset setup" }, { value: "import", label: "Import" },
      ]} />
      {tab === "catalog" && <ResourceManager<Row> config={{
        title: "Catalog items", noun: "catalog item", endpoint: ENDPOINTS.catalogItems, canDelete: true,
        defaults: { active: true, form_schema: [], fulfillment_tasks: [], default_impact: 3, default_urgency: 3, approvers: [] },
        columns: [
          { key: "n", label: "Name", render: (r) => <strong>{String(r.name)}</strong> },
          { key: "s", label: "Slug", className: "num", render: (r) => String(r.slug) },
          { key: "ap", label: "Approval", render: (r) => (r.requires_approval ? <Badge tone="amber">Required</Badge> : "—") },
          { key: "t", label: "Tasks", render: (r) => (r.fulfillment_tasks as unknown[]).length },
          { key: "a", label: "Status", render: active },
        ],
        fields: [
          { name: "name", label: "Name", required: true },
          { name: "slug", label: "Slug", required: true, hint: "URL-friendly id, e.g. new-starter" },
          { name: "short_description", label: "Short description", required: true, span: true },
          { name: "description", label: "Description", type: "textarea" },
          { name: "category", label: "Category", type: "select", lookup: "categories" },
          { name: "service", label: "Service", type: "select", lookup: "services" },
          { name: "assignment_group", label: "Route to group", type: "select", lookup: "groups" },
          { name: "default_impact", label: "Impact", type: "select", options: levels, required: true },
          { name: "default_urgency", label: "Urgency", type: "select", options: levels, required: true },
          { name: "form_schema", label: "Form fields (JSON)", type: "json", rows: 10,
            hint: 'List of {key, label, type: text|textarea|date|boolean|select, required, options, show_when: {field, equals}}' },
          { name: "fulfillment_tasks", label: "Fulfilment tasks (JSON)", type: "json", rows: 5, hint: 'List of {title, description, assignment_group: <group id>}' },
          { name: "requires_approval", label: "Requires approval", type: "checkbox" },
          { name: "approvers", label: "Approvers", type: "multiselect", lookup: "users", hint: "Empty = the routing group's managers, then any Manager. Requesters never approve their own requests." },
          activeField,
        ],
      }} />}
      {tab === "slas" && <ResourceManager<Row> config={{
        title: "SLA policies", noun: "policy", endpoint: ENDPOINTS.slaPolicies, canDelete: true,
        defaults: { active: true, ticket_type: "incident", priority: 3, warn_percent: 80 },
        description: "Targets per ticket type and priority, measured in business minutes on the chosen calendar.",
        columns: [
          { key: "n", label: "Name", render: (r) => <strong>{String(r.name)}</strong> },
          { key: "t", label: "Applies to", render: (r) => <>{String(r.ticket_type)} · P{String(r.priority)}</> },
          { key: "r", label: "Response", render: (r) => `${r.response_minutes} min` },
          { key: "z", label: "Resolution", render: (r) => `${r.resolution_minutes} min` },
          { key: "a", label: "Status", render: active },
        ],
        fields: [
          { name: "name", label: "Name", required: true },
          { name: "ticket_type", label: "Ticket type", type: "select", required: true, options: [{ value: "incident", label: "Incident" }, { value: "request", label: "Request" }] },
          { name: "priority", label: "Priority", type: "select", required: true, options: [1, 2, 3, 4].map((p) => ({ value: p, label: `P${p}` })) },
          { name: "calendar", label: "Business calendar", type: "select", lookup: "calendars", required: true },
          { name: "response_minutes", label: "Response target (minutes)", type: "number", required: true },
          { name: "resolution_minutes", label: "Resolution target (minutes)", type: "number", required: true },
          { name: "warn_percent", label: "Warn at % elapsed", type: "number" },
          activeField,
        ],
      }} />}
      {tab === "calendars" && <ResourceManager<Row> config={{
        title: "Business calendars", noun: "calendar", endpoint: ENDPOINTS.calendars, canDelete: true,
        defaults: { timezone: "America/New_York", hours: [], holidays: [] },
        description: "A calendar with no hours is treated as 24×7.",
        columns: [
          { key: "n", label: "Name", render: (r) => <strong>{String(r.name)}</strong> },
          { key: "z", label: "Time zone", render: (r) => String(r.timezone) },
          { key: "h", label: "Hours", render: (r) => ((r.hours as unknown[]).length ? `${(r.hours as unknown[]).length} windows` : "24×7") },
          { key: "d", label: "Holidays", render: (r) => (r.holidays as unknown[]).length },
        ],
        fields: [
          { name: "name", label: "Name", required: true },
          { name: "timezone", label: "Time zone", required: true, hint: "IANA name, e.g. Europe/London" },
          { name: "hours", label: "Business hours (JSON)", type: "json", rows: 6, hint: '[{"weekday": 0, "start_time": "09:00", "end_time": "17:00"}, …] — 0 = Monday' },
          { name: "holidays", label: "Holidays (JSON)", type: "json", rows: 4, hint: '[{"date": "2026-12-25", "name": "Christmas"}]' },
        ],
      }} />}
      {tab === "notifications" && <ResourceManager<Row> config={{
        title: "Email templates", noun: "template", endpoint: ENDPOINTS.notificationTemplates, canDelete: true,
        defaults: { enabled: true },
        description: "Override the built-in emails. Placeholders like {number}, {subject} and {link} are allowed; anything else is rejected.",
        columns: [
          { key: "e", label: "Event", render: (r) => <code>{String(r.event_type)}</code> },
          { key: "s", label: "Subject", className: "title-cell", render: (r) => String(r.subject) },
          { key: "on", label: "", render: (r) => (r.enabled ? <Badge tone="green" dot>Enabled</Badge> : <Badge>Disabled</Badge>) },
        ],
        fields: [
          { name: "event_type", label: "Event", type: "select", required: true, readOnlyOnEdit: true, options: EVENTS.map((e) => ({ value: e, label: e })) },
          { name: "subject", label: "Subject", required: true, span: true },
          { name: "body", label: "Body", type: "textarea", rows: 8, required: true },
          { name: "enabled", label: "Use this template instead of the default", type: "checkbox", span: true },
        ],
      }} />}
      {tab === "assets" && <div className="stack">
        <ResourceManager<Row> config={{
          title: "Asset types", noun: "asset type", endpoint: ENDPOINTS.assetTypes, canDelete: true, defaults: { active: true },
          columns: [{ key: "n", label: "Name", render: (r) => String(r.name) }, { key: "d", label: "Description", render: (r) => String(r.description || "") }, { key: "a", label: "Status", render: active }],
          fields: [{ name: "name", label: "Name", required: true }, { name: "description", label: "Description" }, activeField],
        }} />
        <ResourceManager<Row> config={{
          title: "Locations", noun: "location", endpoint: ENDPOINTS.locations, canDelete: true, defaults: { active: true },
          columns: [{ key: "n", label: "Name", render: (r) => String(r.name) }, { key: "d", label: "Address", render: (r) => String(r.address || "") }, { key: "a", label: "Status", render: active }],
          fields: [{ name: "name", label: "Name", required: true }, { name: "address", label: "Address", span: true }, activeField],
        }} />
      </div>}
      {tab === "import" && <CsvImport />}
    </>
  );
}
