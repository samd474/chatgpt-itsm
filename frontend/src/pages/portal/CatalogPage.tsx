import { useQuery } from "@tanstack/react-query";
import { LayoutGrid } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { getCatalogItems } from "../../api/catalog";
import { apiErrorMessage } from "../../api/client";
import { Badge, EmptyState, ErrorState, LoadingState, PageHeader, SearchInput } from "../../components/ui";

export function CatalogPage() {
  const [search, setSearch] = useState("");
  const query = useQuery({ queryKey: ["catalog-items"], queryFn: getCatalogItems });
  const items = (query.data ?? []).filter((i) => i.active && `${i.name} ${i.short_description}`.toLowerCase().includes(search.toLowerCase()));
  return (
    <>
      <PageHeader title="Service catalog" description="Request standard services and equipment." />
      <div className="toolbar"><SearchInput value={search} onChange={setSearch} placeholder="Search the catalog" /></div>
      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState message={apiErrorMessage(query.error)} />}
      {query.data && items.length === 0 && <EmptyState title="No matching services" />}
      <div className="tiles">
        {items.map((item) => (
          <Link className="tile" key={item.slug} to={`/portal/catalog/${item.slug}`}>
            <div className="row"><span className="tile-icon"><LayoutGrid /></span><span className="spacer" />{item.requires_approval && <Badge tone="amber">Needs approval</Badge>}</div>
            <h3>{item.name}</h3>
            <p>{item.short_description}</p>
          </Link>
        ))}
      </div>
    </>
  );
}
