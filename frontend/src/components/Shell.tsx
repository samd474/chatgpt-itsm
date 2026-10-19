import {
  BarChart3,
  Boxes,
  CalendarClock,
  CheckSquare,
  ClipboardList,
  FileText,
  FolderKanban,
  GitPullRequestArrow,
  Inbox,
  LayoutGrid,
  LogOut,
  Menu,
  Monitor,
  PlusCircle,
  ScrollText,
  Settings,
  ShieldCheck,
  Users,
  type LucideIcon,
} from "lucide-react";
import { Suspense, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/context";
import { hasRole, isStaff } from "../auth/roles";
import type { User } from "../types";
import { Avatar, LoadingState } from "./ui";

type Item = { to: string; label: string; icon: LucideIcon; end?: boolean; show?: (u: User) => boolean };
type Section = { label: string; items: Item[]; show?: (u: User) => boolean };

const staff = (u: User) => isStaff(u);
const staffOrAuditor = (u: User) => isStaff(u) || hasRole(u, "Auditor");

const SECTIONS: Section[] = [
  {
    label: "Service desk",
    items: [
      { to: "/portal", label: "My requests", icon: Inbox, end: true },
      { to: "/portal/incidents/new", label: "Report an issue", icon: PlusCircle },
      { to: "/portal/catalog", label: "Service catalog", icon: LayoutGrid },
      { to: "/portal/equipment", label: "My equipment", icon: Monitor },
      { to: "/approvals", label: "Approvals", icon: CheckSquare },
    ],
  },
  {
    label: "Work",
    show: staffOrAuditor,
    items: [
      { to: "/tech/queue", label: "Ticket queue", icon: ClipboardList, show: staff },
      { to: "/changes", label: "Changes", icon: GitPullRequestArrow },
      { to: "/changes/calendar", label: "Change calendar", icon: CalendarClock },
      { to: "/projects", label: "Projects", icon: FolderKanban },
    ],
  },
  {
    label: "Inventory",
    show: staffOrAuditor,
    items: [
      { to: "/assets", label: "Assets", icon: Boxes },
      { to: "/contracts", label: "Contracts", icon: FileText },
    ],
  },
  {
    label: "Insights",
    show: (u) => hasRole(u, "Manager", "Administrator", "Auditor"),
    items: [
      { to: "/reports", label: "Reports", icon: BarChart3, show: (u) => hasRole(u, "Manager", "Administrator") },
      { to: "/audit", label: "Audit log", icon: ScrollText, show: (u) => hasRole(u, "Auditor", "Administrator") },
    ],
  },
  {
    label: "Administration",
    show: (u) => hasRole(u, "Administrator"),
    items: [
      { to: "/manage/users", label: "Users & roles", icon: Users },
      { to: "/manage/tickets", label: "Ticket setup", icon: ShieldCheck },
      { to: "/manage/settings", label: "Settings", icon: Settings, end: false },
    ],
  },
];

export function Shell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [lastPath, setLastPath] = useState(location.pathname);
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname);
    setOpen(false);
  }

  if (!user) return null;
  const wide = /^\/(tech|projects\/\d+|changes\/calendar)/.test(location.pathname);

  return (
    <div className="shell">
      <aside className={`sidebar${open ? " open" : ""}`}>
        <div className="brand"><span className="brand-mark">IT</span>Service Desk</div>
        {SECTIONS.filter((s) => !s.show || s.show(user)).map((section) => {
          const items = section.items.filter((i) => !i.show || i.show(user));
          if (items.length === 0) return null;
          return (
            <nav key={section.label} className="nav-section" aria-label={section.label}>
              <div className="nav-label">{section.label}</div>
              {items.map((item) => (
                <NavLink key={item.to} to={item.to} end={item.end ?? true} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
                  <item.icon />{item.label}
                </NavLink>
              ))}
            </nav>
          );
        })}
        <div className="sidebar-footer">
          <div className="user-chip">
            <Avatar name={user.name || user.username} />
            <div className="user-meta"><strong>{user.name || user.username}</strong><span>{user.groups.join(", ") || "Member"}</span></div>
            <button className="btn btn-ghost btn-icon" title="Sign out" aria-label="Sign out"
              onClick={async () => { await logout(); navigate("/login", { replace: true }); }}><LogOut /></button>
          </div>
        </div>
      </aside>
      {open && <div className="overlay" onClick={() => setOpen(false)} />}
      <div className="main">
        <div className="mobile-bar">
          <button className="btn btn-ghost btn-icon" aria-label="Open menu" onClick={() => setOpen(true)}><Menu /></button>
          <span className="brand-mark">IT</span><strong>Service Desk</strong>
        </div>
        <main className={`content${wide ? " content--wide" : ""}`}>
          <Suspense fallback={<LoadingState />}><Outlet /></Suspense>
        </main>
      </div>
    </div>
  );
}
