import { useQuery } from "@tanstack/react-query";
import { Monitor } from "lucide-react";
import { Link } from "react-router-dom";
import { listAll, ENDPOINTS } from "../../api/resources";
import { Pill } from "../../components/badges";
import { Badge, EmptyState, LoadingState, PageHeader } from "../../components/ui";
import type { Asset } from "../../types";
import { formatDay } from "../../utils/format";

export function EquipmentPage() {
  const query = useQuery({ queryKey: ["my-assets"], queryFn: () => listAll<Asset>(ENDPOINTS.assets) });
  return (
    <>
      <PageHeader title="My equipment" description="Devices and licences assigned to you."
        actions={<Link className="btn btn-secondary" to="/portal/incidents/new">Report a problem</Link>} />
      {query.isPending && <LoadingState />}
      {query.data?.length === 0 && <EmptyState title="Nothing assigned to you" message="Equipment the IT team assigns to you will appear here." />}
      <div className="tiles">
        {query.data?.map((a) => (
          <div className="tile" key={a.id}>
            <div className="row"><span className="tile-icon"><Monitor /></span><span className="spacer" /><Pill value={a.status} /></div>
            <h3>{a.name}</h3>
            <p className="eyebrow">{a.asset_tag}</p>
            <dl className="props">
              <dt>Type</dt><dd>{a.asset_type_name}</dd>
              <dt>Model</dt><dd>{[a.manufacturer, a.model].filter(Boolean).join(" ") || "—"}</dd>
              <dt>Serial</dt><dd>{a.serial_number || "—"}</dd>
              <dt>Warranty</dt><dd>{a.warranty_expires ? <>{formatDay(a.warranty_expires)} {new Date(a.warranty_expires) < new Date() && <Badge tone="red">Expired</Badge>}</> : "—"}</dd>
            </dl>
          </div>
        ))}
      </div>
    </>
  );
}
