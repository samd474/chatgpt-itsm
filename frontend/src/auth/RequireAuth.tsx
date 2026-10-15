import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./context";
import { LoadingState } from "../components/ui";

export function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <div className="auth"><div className="auth-card"><LoadingState rows={2} /></div></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return <Outlet />;
}
