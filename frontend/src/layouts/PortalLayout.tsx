import { AppShell } from "../components/AppShell";

export function PortalLayout() {
  return (
    <AppShell
      title="Requester Portal"
      nav={[
        { to: "/portal", label: "My requests", end: true },
        { to: "/portal/incidents/new", label: "Report an incident" },
        { to: "/portal/catalog", label: "Service catalog" },
        { to: "/approvals", label: "My approvals" },
      ]}
    />
  );
}
