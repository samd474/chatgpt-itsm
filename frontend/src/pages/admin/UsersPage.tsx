import { useState } from "react";
import { ENDPOINTS } from "../../api/resources";
import { Badge, PageHeader, Tabs } from "../../components/ui";
import { ResourceManager } from "../../components/ResourceManager";
import { relativeTime } from "../../utils/format";

type UserRow = { id: number; username: string; email: string; first_name: string; last_name: string; department: string; is_enabled: boolean; roles: string[]; last_login: string | null };
type RoleRow = { id: number; name: string; built_in: boolean; member_count: number };

export function UsersPage() {
  const [tab, setTab] = useState<"users" | "roles">("users");
  return (
    <>
      <PageHeader title="Users & roles" description="Accounts, role membership and access. Changes are audited." />
      <Tabs value={tab} onChange={setTab} tabs={[{ value: "users", label: "Users" }, { value: "roles", label: "Roles" }]} />
      {tab === "users" && (
        <ResourceManager<UserRow> config={{
          title: "Users", noun: "user", endpoint: ENDPOINTS.users, searchable: true,
          defaults: { is_enabled: true, roles: ["Requester"] },
          columns: [
            { key: "n", label: "Name", render: (u) => <div><div style={{ fontWeight: 500 }}>{[u.first_name, u.last_name].filter(Boolean).join(" ") || u.username}</div><div className="subtle">{u.email}</div></div> },
            { key: "r", label: "Roles", render: (u) => <div className="row">{u.roles.map((r) => <Badge key={r} tone={r === "Administrator" ? "violet" : "gray"}>{r}</Badge>)}</div> },
            { key: "d", label: "Department", render: (u) => u.department || <span className="subtle">—</span> },
            { key: "s", label: "Status", render: (u) => u.is_enabled ? <Badge tone="green" dot>Active</Badge> : <Badge tone="red" dot>Disabled</Badge> },
            { key: "l", label: "Last sign-in", render: (u) => <span className="subtle">{u.last_login ? relativeTime(u.last_login) : "Never"}</span> },
          ],
          fields: [
            { name: "username", label: "Username", required: true, readOnlyOnEdit: true },
            { name: "email", label: "Email", type: "email", required: true },
            { name: "first_name", label: "First name" },
            { name: "last_name", label: "Last name" },
            { name: "department", label: "Department" },
            { name: "title", label: "Job title" },
            { name: "location", label: "Location" },
            { name: "password", label: "Password", type: "password", hint: "Required for new users. Leave blank to keep the current password." },
            { name: "roles", label: "Roles", type: "multiselect", lookup: "roles", hint: "Ctrl/Cmd-click to select several. You can't change your own roles." },
            { name: "support_groups", label: "Support groups", type: "multiselect", lookup: "groups" },
            { name: "is_enabled", label: "Account enabled (disabling signs the user out everywhere)", type: "checkbox", span: true },
          ],
        }} />
      )}
      {tab === "roles" && (
        <ResourceManager<RoleRow> config={{
          title: "Roles", noun: "role", endpoint: ENDPOINTS.roles, canDelete: true,
          description: "Built-in roles control access across the platform. Add people to CAB to make them change approvers.",
          columns: [
            { key: "n", label: "Role", render: (r) => <strong>{r.name}</strong> },
            { key: "b", label: "", render: (r) => r.built_in ? <Badge>Built-in</Badge> : <Badge tone="accent">Custom</Badge> },
            { key: "m", label: "Members", render: (r) => r.member_count },
          ],
          fields: [{ name: "name", label: "Name", required: true }],
        }} />
      )}
    </>
  );
}
