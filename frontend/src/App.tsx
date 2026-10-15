import { Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./auth/RequireAuth";
import { RequireRole } from "./auth/RequireRole";
import { useAuth } from "./auth/context";
import { homePath } from "./auth/roles";
import { Shell } from "./components/Shell";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PortalHomePage } from "./pages/portal/PortalHomePage";
import { NewIncidentPage } from "./pages/portal/NewIncidentPage";
import { TicketDetailPage } from "./pages/portal/TicketDetailPage";
import { CatalogPage } from "./pages/portal/CatalogPage";
import { CatalogItemPage } from "./pages/portal/CatalogItemPage";
import { EquipmentPage } from "./pages/portal/EquipmentPage";
import { ApprovalsPage } from "./pages/approvals/ApprovalsPage";
import { QueuePage } from "./pages/technician/QueuePage";
import { TechnicianTicketPage } from "./pages/technician/TechnicianTicketPage";
import { ReportsPage } from "./pages/reports/ReportsPage";
import { AuditPage } from "./pages/audit/AuditPage";
import { UsersPage } from "./pages/admin/UsersPage";
import { TicketSetupPage } from "./pages/admin/TicketSetupPage";
import { SettingsPage } from "./pages/admin/SettingsPage";
import { AssetsPage } from "./pages/assets/AssetsPage";
import { AssetDetailPage } from "./pages/assets/AssetDetailPage";
import { ContractsPage } from "./pages/contracts/ContractsPage";
import { ContractDetailPage } from "./pages/contracts/ContractDetailPage";
import { ProjectsPage } from "./pages/projects/ProjectsPage";
import { ProjectDetailPage } from "./pages/projects/ProjectDetailPage";
import { ChangesPage } from "./pages/changes/ChangesPage";
import { ChangeDetailPage } from "./pages/changes/ChangeDetailPage";
import { ChangeCalendarPage } from "./pages/changes/ChangeCalendarPage";

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
