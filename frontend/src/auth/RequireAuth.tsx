import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./context";
import { LoadingState } from "../components/ui";

export const SECURITY_PATH = "/account/security";

export function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <div className="auth"><div className="auth-card"><LoadingState rows={2} /></div></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  // The API refuses everything else until a required authenticator is set up.
  if (user.two_factor_setup_needed && location.pathname !== SECURITY_PATH) return <Navigate to={SECURITY_PATH} replace />;
  return <Outlet />;
}
