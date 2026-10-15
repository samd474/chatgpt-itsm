import { AppShell } from "../components/AppShell";

export function AdminLayout() {
  return (
    <AppShell
      title="Operations"
      nav={[
        { to: "/admin/config", label: "Configuration" },
        { to: "/reports", label: "Reports" },
        { to: "/audit", label: "Audit" },
        { to: "/portal", label: "Requester portal" },
      ]}
    />
  );
}
