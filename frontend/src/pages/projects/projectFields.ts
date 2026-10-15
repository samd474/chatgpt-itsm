import type { FieldDef, Values } from "../../components/form";
import type { Project } from "../../types";

export const PROJECT_FIELDS: FieldDef[] = [
  { name: "key", label: "Key", required: true, readOnlyOnEdit: true, hint: "2–10 capitals, used in task numbers (e.g. NET-12)" },
  { name: "name", label: "Name", required: true },
  { name: "status", label: "Status", type: "select", required: true, options: [
    { value: "proposed", label: "Proposed" }, { value: "active", label: "Active" }, { value: "on_hold", label: "On hold" },
    { value: "completed", label: "Completed" }, { value: "cancelled", label: "Cancelled" }] },
  { name: "manager", label: "Project manager", type: "select", lookup: "people", required: true },
  { name: "start_date", label: "Start date", type: "date" },
  { name: "target_date", label: "Target date", type: "date" },
  { name: "budget", label: "Budget", type: "number" },
  { name: "description", label: "Description", type: "textarea" },
  { name: "contributors", label: "Contributors", type: "multiselect", lookup: "people", hint: "Can create and update tasks" },
  { name: "viewers", label: "Viewers", type: "multiselect", lookup: "people", hint: "Read-only; can update tasks assigned to them" },
];

export function projectToRecord(project: Project): Values {
  return {
    ...project,
    contributors: project.members.filter((m) => m.role === "contributor").map((m) => m.user),
    viewers: project.members.filter((m) => m.role === "viewer").map((m) => m.user),
  };
}

export function membersPayload(payload: Values): Values {
  const { contributors, viewers, ...rest } = payload as Values & { contributors?: number[]; viewers?: number[] };
  const members = [
    ...(contributors ?? []).map((user) => ({ user, role: "contributor" })),
    ...(viewers ?? []).filter((u) => !(contributors ?? []).includes(u)).map((user) => ({ user, role: "viewer" })),
  ];
  return { ...rest, members };
}
