import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./context";
import { hasRole } from "./roles";

// User experience only: keeps people out of screens they can't use. Django still
// rejects unauthorized API requests if someone types a URL directly.
export function RequireRole({ allowed }: { allowed: string[] }) {
  const { user } = useAuth();
  if (!hasRole(user, ...allowed)) return <Navigate to="/portal" replace />;
  return <Outlet />;
}
