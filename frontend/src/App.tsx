import { lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./auth/RequireAuth";
import { RequireRole } from "./auth/RequireRole";
import { useAuth } from "./auth/context";
import { homePath } from "./auth/roles";
import { Shell } from "./components/Shell";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";

// Each page is its own chunk, so the login screen and portal don't download the admin console.
const PortalHomePage = lazy(() => import("./pages/portal/PortalHomePage").then((m) => ({ default: m.PortalHomePage })));
const NewIncidentPage = lazy(() => import("./pages/portal/NewIncidentPage").then((m) => ({ default: m.NewIncidentPage })));
const TicketDetailPage = lazy(() => import("./pages/portal/TicketDetailPage").then((m) => ({ default: m.TicketDetailPage })));
const CatalogPage = lazy(() => import("./pages/portal/CatalogPage").then((m) => ({ default: m.CatalogPage })));
const CatalogItemPage = lazy(() => import("./pages/portal/CatalogItemPage").then((m) => ({ default: m.CatalogItemPage })));
const EquipmentPage = lazy(() => import("./pages/portal/EquipmentPage").then((m) => ({ default: m.EquipmentPage })));
const ApprovalsPage = lazy(() => import("./pages/approvals/ApprovalsPage").then((m) => ({ default: m.ApprovalsPage })));
const QueuePage = lazy(() => import("./pages/technician/QueuePage").then((m) => ({ default: m.QueuePage })));
const TechnicianTicketPage = lazy(() => import("./pages/technician/TechnicianTicketPage").then((m) => ({ default: m.TechnicianTicketPage })));
const ReportsPage = lazy(() => import("./pages/reports/ReportsPage").then((m) => ({ default: m.ReportsPage })));
const AuditPage = lazy(() => import("./pages/audit/AuditPage").then((m) => ({ default: m.AuditPage })));
const UsersPage = lazy(() => import("./pages/admin/UsersPage").then((m) => ({ default: m.UsersPage })));
const TicketSetupPage = lazy(() => import("./pages/admin/TicketSetupPage").then((m) => ({ default: m.TicketSetupPage })));
const SettingsPage = lazy(() => import("./pages/admin/SettingsPage").then((m) => ({ default: m.SettingsPage })));
const AssetsPage = lazy(() => import("./pages/assets/AssetsPage").then((m) => ({ default: m.AssetsPage })));
const AssetDetailPage = lazy(() => import("./pages/assets/AssetDetailPage").then((m) => ({ default: m.AssetDetailPage })));
const ContractsPage = lazy(() => import("./pages/contracts/ContractsPage").then((m) => ({ default: m.ContractsPage })));
const ContractDetailPage = lazy(() => import("./pages/contracts/ContractDetailPage").then((m) => ({ default: m.ContractDetailPage })));
const ProjectsPage = lazy(() => import("./pages/projects/ProjectsPage").then((m) => ({ default: m.ProjectsPage })));
const ProjectDetailPage = lazy(() => import("./pages/projects/ProjectDetailPage").then((m) => ({ default: m.ProjectDetailPage })));
const ChangesPage = lazy(() => import("./pages/changes/ChangesPage").then((m) => ({ default: m.ChangesPage })));
const ChangeDetailPage = lazy(() => import("./pages/changes/ChangeDetailPage").then((m) => ({ default: m.ChangeDetailPage })));
const ChangeCalendarPage = lazy(() => import("./pages/changes/ChangeCalendarPage").then((m) => ({ default: m.ChangeCalendarPage })));

function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={user ? homePath(user) : "/login"} replace />;
}

const STAFF = ["Technician", "Manager", "Administrator"];
const STAFF_AUDIT = [...STAFF, "Auditor"];

// Route guards are for navigation only; the API enforces every permission itself.
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<Shell />}>
          <Route index element={<HomeRedirect />} />
          <Route path="/portal" element={<PortalHomePage />} />
          <Route path="/portal/incidents/new" element={<NewIncidentPage />} />
          <Route path="/portal/tickets/:id" element={<TicketDetailPage />} />
          <Route path="/portal/catalog" element={<CatalogPage />} />
          <Route path="/portal/catalog/:slug" element={<CatalogItemPage />} />
          <Route path="/portal/equipment" element={<EquipmentPage />} />
          <Route path="/approvals" element={<ApprovalsPage />} />

          <Route element={<RequireRole allowed={STAFF} />}>
            <Route path="/tech" element={<Navigate to="/tech/queue" replace />} />
            <Route path="/tech/queue" element={<QueuePage />} />
            <Route path="/tech/tickets/:id" element={<TechnicianTicketPage />} />
          </Route>

          <Route element={<RequireRole allowed={STAFF_AUDIT} />}>
            <Route path="/assets" element={<AssetsPage />} />
            <Route path="/assets/:id" element={<AssetDetailPage />} />
            <Route path="/contracts" element={<ContractsPage />} />
            <Route path="/contracts/:id" element={<ContractDetailPage />} />
            <Route path="/changes" element={<ChangesPage />} />
            <Route path="/changes/calendar" element={<ChangeCalendarPage />} />
            <Route path="/changes/:id" element={<ChangeDetailPage />} />
          </Route>
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:id" element={<ProjectDetailPage />} />

          <Route element={<RequireRole allowed={["Manager", "Administrator"]} />}>
            <Route path="/reports" element={<ReportsPage />} />
          </Route>
          <Route element={<RequireRole allowed={["Auditor", "Administrator"]} />}>
            <Route path="/audit" element={<AuditPage />} />
          </Route>
          <Route element={<RequireRole allowed={["Administrator"]} />}>
            {/* /admin/* belongs to Django admin (proxied by Vite and NGINX), so the console lives under /manage. */}
            <Route path="/manage" element={<Navigate to="/manage/users" replace />} />
            <Route path="/manage/users" element={<UsersPage />} />
            <Route path="/manage/tickets" element={<TicketSetupPage />} />
            <Route path="/manage/settings" element={<SettingsPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
