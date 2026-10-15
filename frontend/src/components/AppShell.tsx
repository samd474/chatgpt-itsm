import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/context";
import { hasRole, isStaff } from "../auth/roles";

export type NavItem = { to: string; label: string; end?: boolean };

export function AppShell({ title, nav }: { title: string; nav: NavItem[] }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  // Cross-workspace links, shown only to people who can use them.
  const extra: NavItem[] = [];
  if (isStaff(user) && !nav.some((n) => n.to === "/tech/queue")) extra.push({ to: "/tech/queue", label: "Technician queue" });
  if (hasRole(user, "Manager", "Administrator") && !nav.some((n) => n.to === "/reports")) extra.push({ to: "/reports", label: "Reports" });
  if (hasRole(user, "Auditor", "Administrator") && !nav.some((n) => n.to === "/audit")) extra.push({ to: "/audit", label: "Audit" });
  if (hasRole(user, "Administrator") && !nav.some((n) => n.to === "/admin/config")) extra.push({ to: "/admin/config", label: "Configuration" });

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">ITSM</div>
        <div className="sidebar-title">{title}</div>
        <nav aria-label="Primary navigation">
          {[...nav, ...extra].map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-link${isActive ? " nav-link--active" : ""}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div>
            <strong>{user?.name || user?.username}</strong>
            <span className="muted topbar-groups">{user?.groups.join(", ") || "Authenticated user"}</span>
          </div>
          <button className="button button--secondary" onClick={handleLogout}>Sign out</button>
        </header>
        <main className="content"><Outlet /></main>
      </div>
    </div>
  );
}
