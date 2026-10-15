import { Link } from "react-router-dom";

export function NotFoundPage() {
  return <div className="state-card"><h1>Page not found</h1><Link to="/">Return to the application</Link></div>;
}
