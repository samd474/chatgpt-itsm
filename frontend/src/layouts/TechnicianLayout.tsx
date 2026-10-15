import { AppShell } from "../components/AppShell";

export function TechnicianLayout() {
  return (
    <AppShell
      title="Technician Workspace"
      nav={[
        { to: "/tech/queue", label: "Queue" },
        { to: "/approvals", label: "My approvals" },
        { to: "/portal", label: "Requester portal" },
      ]}
    />
  );
}
