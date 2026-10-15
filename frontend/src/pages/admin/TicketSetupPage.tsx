import { useState } from "react";
import { ENDPOINTS } from "../../api/resources";
import { Pill } from "../../components/badges";
import type { FieldDef, Option } from "../../components/form";
import { ResourceManager } from "../../components/ResourceManager";
import { Badge, PageHeader, Tabs } from "../../components/ui";
import { LEVELS } from "../../utils/format";

type Row = { id: number } & Record<string, unknown>;
const levels: Option[] = LEVELS.map((l) => ({ value: l.value, label: l.label }));
const active = (r: Row) => (r.active === false ? <Badge tone="gray">Inactive</Badge> : <Badge tone="green" dot>Active</Badge>);
const activeField: FieldDef = { name: "active", label: "Active", type: "checkbox", span: true };

type TabKey = "groups" | "categories" | "services" | "templates" | "queues" | "fields";

export function TicketSetupPage() {
  const [tab, setTab] = useState<TabKey>("groups");
  return (
    <>
      <PageHeader title="Ticket setup" description="Teams, classification, templates, queues and custom fields." />
      <Tabs value={tab} onChange={setTab} tabs={[
        { value: "groups", label: "Support groups" }, { value: "categories", label: "Categories" }, { value: "services", label: "Services" },
        { value: "templates", label: "Templates" }, { value: "queues", label: "Queues" }, { value: "fields", label: "Custom fields" },
      ]} />
      {tab === "groups" && <ResourceManager<Row> config={{
        title: "Support groups", noun: "group", endpoint: ENDPOINTS.supportGroups, canDelete: true, defaults: { active: true },
        description: "Teams that own tickets. Members see and work their group's tickets; managers also oversee them.",
        columns: [
          { key: "n", label: "Name", render: (r) => <strong>{String(r.name)}</strong> },
          { key: "m", label: "Members", render: (r) => (r.members as number[] | undefined)?.length ?? 0 },
          { key: "a", label: "Status", render: active },
        ],
        fields: [
          { name: "name", label: "Name", required: true, span: true },
          { name: "members", label: "Members", type: "multiselect", lookup: "users" },
          { name: "managers", label: "Managers", type: "multiselect", lookup: "users" },
          activeField,
        ],
      }} />}
      {tab === "categories" && <ResourceManager<Row> config={{
        title: "Categories", noun: "category", endpoint: ENDPOINTS.categories, canDelete: true, defaults: { active: true },
        columns: [{ key: "n", label: "Name", render: (r) => String(r.name) }, { key: "a", label: "Status", render: active }],
        fields: [{ name: "name", label: "Name", required: true }, { name: "parent", label: "Parent", type: "select", lookup: "categories" }, activeField],
      }} />}
      {tab === "services" && <ResourceManager<Row> config={{
        title: "Business services", noun: "service", endpoint: ENDPOINTS.services, canDelete: true, defaults: { active: true },
        columns: [{ key: "n", label: "Name", render: (r) => String(r.name) }, { key: "a", label: "Status", render: active }],
        fields: [{ name: "name", label: "Name", required: true }, { name: "owner_group", label: "Owning group", type: "select", lookup: "groups" }, activeField],
      }} />}
      {tab === "templates" && <ResourceManager<Row> config={{
        title: "Ticket templates", noun: "template", endpoint: ENDPOINTS.templates, canDelete: true,
        defaults: { active: true, available_to_requesters: true, request_type: "incident", impact: 3, urgency: 3 },
        description: "Pre-filled starting points. A template's assignment group is applied by the server, so requesters can't route tickets themselves.",
        columns: [
          { key: "n", label: "Name", render: (r) => <strong>{String(r.name)}</strong> },
          { key: "t", label: "Type", render: (r) => <Pill value={String(r.request_type)} /> },
          { key: "v", label: "Visible to", render: (r) => (r.available_to_requesters ? "Everyone" : "Staff only") },
          { key: "a", label: "Status", render: active },
        ],
        fields: [
          { name: "name", label: "Name", required: true },
          { name: "request_type", label: "Type", type: "select", required: true, options: [{ value: "incident", label: "Incident" }, { value: "request", label: "Request" }] },
          { name: "help_text", label: "Help text", span: true },
          { name: "subject", label: "Subject", span: true },
          { name: "description", label: "Description", type: "textarea" },
          { name: "category", label: "Category", type: "select", lookup: "categories" },
          { name: "service", label: "Service", type: "select", lookup: "services" },
          { name: "assignment_group", label: "Route to group", type: "select", lookup: "groups" },
          { name: "impact", label: "Impact", type: "select", options: levels, required: true },
          { name: "urgency", label: "Urgency", type: "select", options: levels, required: true },
          { name: "available_to_requesters", label: "Requesters can use this template", type: "checkbox", span: true },
          activeField,
        ],
      }} />}
      {tab === "queues" && <ResourceManager<Row> config={{
        title: "Queues", noun: "queue", endpoint: ENDPOINTS.queues, canDelete: true,
        defaults: { active: true, ordering: "priority", filters: {}, visible_to_roles: [], position: 0 },
        description: "Saved views shown as tabs in the ticket queue. They only narrow what each person can already see.",
        columns: [
          { key: "n", label: "Name", render: (r) => <strong>{String(r.name)}</strong> },
          { key: "f", label: "Filters", render: (r) => <code>{JSON.stringify(r.filters)}</code> },
          { key: "v", label: "Visible to", render: (r) => ((r.visible_to_roles as string[]).length ? (r.visible_to_roles as string[]).join(", ") : "All staff") },
          { key: "a", label: "Status", render: active },
        ],
        fields: [
          { name: "name", label: "Name", required: true },
          { name: "ordering", label: "Sort", type: "select", required: true, options: [
            { value: "priority", label: "Highest priority first" }, { value: "created_at", label: "Oldest first" },
            { value: "-created_at", label: "Newest first" }, { value: "-updated_at", label: "Recently updated" }] },
          { name: "description", label: "Description", span: true },
          { name: "filters", label: "Filters (JSON)", type: "json", rows: 6,
            hint: 'Keys: status [..], priority [1-4], request_type, assignment_group [ids], my_groups true, technician "me"|"unassigned", category [ids], service [ids], sla "breached"|"at_risk". Example: {"my_groups": true, "status": ["new","assigned"]}' },
          { name: "visible_to_roles", label: "Visible to roles", type: "multiselect",
            options: ["Technician", "Manager", "Administrator", "Auditor"].map((r) => ({ value: r, label: r })), hint: "None selected = all staff." },
          { name: "position", label: "Position", type: "number" },
          activeField,
        ],
      }} />}
      {tab === "fields" && <ResourceManager<Row> config={{
        title: "Custom fields", noun: "field", endpoint: ENDPOINTS.customFields, canDelete: true,
        defaults: { active: true, entity: "ticket", field_type: "text", options: [], visible_to_requester: true, position: 0 },
        description: "Extra fields on tickets, assets, changes, projects and contracts. Values are validated by the server.",
        columns: [
          { key: "e", label: "Applies to", render: (r) => <Pill value={String(r.entity)} /> },
          { key: "l", label: "Label", render: (r) => <strong>{String(r.label)}</strong> },
          { key: "k", label: "Key", className: "num", render: (r) => String(r.key) },
          { key: "t", label: "Type", render: (r) => String(r.field_type) },
          { key: "r", label: "Required", render: (r) => (r.required ? "Yes" : "No") },
          { key: "a", label: "Status", render: active },
        ],
        fields: [
          { name: "entity", label: "Applies to", type: "select", required: true, readOnlyOnEdit: true, options: ["ticket", "asset", "change", "project", "contract"].map((v) => ({ value: v, label: v[0].toUpperCase() + v.slice(1) })) },
          { name: "key", label: "Key", required: true, readOnlyOnEdit: true, hint: "lowercase_with_underscores; can't change later" },
          { name: "label", label: "Label", required: true },
          { name: "field_type", label: "Type", type: "select", required: true, options: [
            { value: "text", label: "Text" }, { value: "textarea", label: "Long text" }, { value: "date", label: "Date" },
            { value: "boolean", label: "Yes/no" }, { value: "select", label: "Choice" }] },
          { name: "options", label: "Choices (JSON list)", type: "json", rows: 3, hint: 'Only for Choice fields, e.g. ["Laptop", "Desktop"]' },
          { name: "position", label: "Position", type: "number" },
          { name: "required", label: "Required", type: "checkbox" },
          { name: "visible_to_requester", label: "Requesters see this (tickets only)", type: "checkbox" },
          activeField,
        ],
      }} />}
    </>
  );
}
