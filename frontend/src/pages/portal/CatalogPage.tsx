import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getCatalogItems } from "../../api/catalog";
import { apiErrorMessage } from "../../api/client";
import { EmptyState, ErrorState, LoadingState } from "../../components/Feedback";

export function CatalogPage() {
  const query = useQuery({ queryKey: ["catalog-items"], queryFn: getCatalogItems });
  return (
    <section>
      <div className="page-heading"><div><h1>Service catalog</h1><p>Request standard services using guided forms.</p></div></div>
      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState message={apiErrorMessage(query.error)} />}
      {query.data?.length === 0 && <EmptyState message="No catalog items are available yet." />}
      <div className="card-grid">
        {query.data?.filter((item) => item.active).map((item) => (
          <Link className="catalog-card" key={item.slug} to={`/portal/catalog/${item.slug}`}>
            <h2>{item.name}</h2><p>{item.short_description}</p>{item.requires_approval && <span className="badge">Approval required</span>}
          </Link>
        ))}
      </div>
    </section>
  );
}
