import { Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./auth/RequireAuth";
import { RequireRole } from "./auth/RequireRole";
import { useAuth } from "./auth/context";
import { homePath } from "./auth/roles";
import { PortalLayout } from "./layouts/PortalLayout";
import { TechnicianLayout } from "./layouts/TechnicianLayout";
import { AdminLayout } from "./layouts/AdminLayout";
import { LoginPage } from "./pages/LoginPage";
import { PortalHomePage } from "./pages/portal/PortalHomePage";
import { NewIncidentPage } from "./pages/portal/NewIncidentPage";
import { TicketDetailPage } from "./pages/portal/TicketDetailPage";
import { CatalogPage } from "./pages/portal/CatalogPage";
import { CatalogItemPage } from "./pages/portal/CatalogItemPage";
import { ApprovalsPage } from "./pages/approvals/ApprovalsPage";
import { QueuePage } from "./pages/technician/QueuePage";
import { TechnicianTicketPage } from "./pages/technician/TechnicianTicketPage";
import { AdminConfigPage } from "./pages/admin/AdminConfigPage";
import { ReportsPage } from "./pages/reports/ReportsPage";
import { AuditPage } from "./pages/audit/AuditPage";
import { NotFoundPage } from "./pages/NotFoundPage";

function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={user ? homePath(user) : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route index element={<HomeRedirect />} />

        <Route path="/portal" element={<PortalLayout />}>
          <Route index element={<PortalHomePage />} />
          <Route path="incidents/new" element={<NewIncidentPage />} />
          <Route path="tickets/:id" element={<TicketDetailPage />} />
          <Route path="catalog" element={<CatalogPage />} />
          <Route path="catalog/:slug" element={<CatalogItemPage />} />
        </Route>
        <Route path="/approvals" element={<PortalLayout />}>
          <Route index element={<ApprovalsPage />} />
        </Route>

        <Route element={<RequireRole allowed={["Technician", "Manager", "Administrator"]} />}>
          <Route path="/tech" element={<TechnicianLayout />}>
            <Route index element={<Navigate to="queue" replace />} />
            <Route path="queue" element={<QueuePage />} />
            <Route path="tickets/:id" element={<TechnicianTicketPage />} />
          </Route>
        </Route>

        <Route element={<RequireRole allowed={["Administrator"]} />}>
          <Route path="/admin" element={<AdminLayout />}>
            <Route path="config" element={<AdminConfigPage />} />
          </Route>
        </Route>

        <Route element={<RequireRole allowed={["Manager", "Administrator"]} />}>
          <Route path="/reports" element={<AdminLayout />}><Route index element={<ReportsPage />} /></Route>
        </Route>

        <Route element={<RequireRole allowed={["Auditor", "Administrator"]} />}>
          <Route path="/audit" element={<AdminLayout />}><Route index element={<AuditPage />} /></Route>
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
