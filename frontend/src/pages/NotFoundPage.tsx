import { Link } from "react-router-dom";
import { EmptyState } from "../components/ui";

export function NotFoundPage() {
  return <div className="auth"><EmptyState title="Page not found" message="The page you were looking for doesn't exist." action={<Link className="btn btn-secondary" to="/">Go home</Link>} /></div>;
}
