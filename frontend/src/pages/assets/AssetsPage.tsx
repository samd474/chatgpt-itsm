import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { listResource, ENDPOINTS } from "../../api/resources";
import { useAuth } from "../../auth/context";
import { isStaff } from "../../auth/roles";
import { Pill } from "../../components/badges";
import { useLookup } from "../../components/form";
import { Card, DataTable, EmptyState, LoadingState, PageHeader, Pager, SearchInput } from "../../components/ui";
import type { Asset } from "../../types";
import { formatDay } from "../../utils/format";
import { ASSET_STATUSES } from "./assetFields";

export function AssetsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const [page, setPage] = useState(1);
  const types = useLookup("assetTypes");
  const query = useQuery({
    queryKey: ["assets", search, status, type, page],
    queryFn: () => listResource<Asset>(ENDPOINTS.assets, { page, search: search || undefined, status: status || undefined, asset_type: type || undefined }),
  });
  return (
    <>
      <PageHeader title="Assets" description="Hardware, software and infrastructure the organisation owns."
        actions={isStaff(user) && <button className="btn btn-primary" onClick={() => navigate("/assets/new")}><Plus />New asset</button>} />
      <div className="toolbar">
        <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search tag, name, serial, model" />
        <select className="select" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} aria-label="Status">
          <option value="">Any status</option>{ASSET_STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <select className="select" value={type} onChange={(e) => { setType(e.target.value); setPage(1); }} aria-label="Type">
          <option value="">Any type</option>{types.data?.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
      </div>
      {query.isPending && <LoadingState />}
      {query.data && (
        <Card flush>
          <DataTable rows={query.data.items} rowKey={(a) => a.id} onRowClick={(a) => navigate(`/assets/${a.id}`)}
            empty={<EmptyState title="No assets found" message="Add assets here or bring them in from your inventory." />}
            columns={[
              { key: "t", label: "Tag", className: "num", render: (a) => a.asset_tag },
              { key: "n", label: "Name", className: "title-cell", render: (a) => a.name },
              { key: "ty", label: "Type", render: (a) => a.asset_type_name },
              { key: "s", label: "Status", render: (a) => <Pill value={a.status} /> },
              { key: "u", label: "Assigned to", className: "hide-sm", render: (a) => a.assigned_to_name ?? <span className="subtle">—</span> },
              { key: "l", label: "Location", className: "hide-sm", render: (a) => a.location_name ?? <span className="subtle">—</span> },
              { key: "w", label: "Warranty", className: "hide-sm", render: (a) => <span className="subtle">{formatDay(a.warranty_expires)}</span> },
            ]} />
          {(query.data.next || query.data.previous) && <Pager count={query.data.count} page={page} hasNext={!!query.data.next} hasPrev={!!query.data.previous} onPage={setPage} noun="assets" />}
        </Card>
      )}
    </>
  );
}
