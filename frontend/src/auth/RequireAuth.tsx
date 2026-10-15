import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./context";
import { LoadingState } from "../components/Feedback";

export function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingState message="Checking your session..." />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return <Outlet />;
}
