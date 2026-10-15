import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { listResource, ENDPOINTS } from "../../api/resources";
import { useAuth } from "../../auth/context";
import { hasRole } from "../../auth/roles";
import { Pill } from "../../components/badges";
import { ResourceManager } from "../../components/ResourceManager";
import { Badge, Card, DataTable, EmptyState, LoadingState, PageHeader, Pager, SearchInput, Tabs } from "../../components/ui";
import type { Contract } from "../../types";
import { formatDay, formatMoney } from "../../utils/format";

type Vendor = { id: number; name: string; contact_name: string; email: string; phone: string; active: boolean } & Record<string, unknown>;

function Remaining({ c }: { c: Contract }) {
  if (c.status !== "active") return <span className="subtle">—</span>;
  if (c.days_remaining < 0) return <Badge tone="red">Lapsed</Badge>;
  if (c.days_remaining <= c.renewal_notice_days) return <Badge tone="amber" dot>{c.days_remaining} days left</Badge>;
  return <span className="subtle">{c.days_remaining} days</span>;
}

export function ContractsPage() {
  const { user } = useAuth();
  const canWrite = hasRole(user, "Manager", "Administrator");
  const navigate = useNavigate();
  const [tab, setTab] = useState<"contracts" | "vendors">("contracts");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("active");
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["contracts", search, status, page],
    enabled: tab === "contracts",
    queryFn: () => listResource<Contract>(ENDPOINTS.contracts, { page, search: search || undefined, status: status || undefined, ordering: "end_date" }),
  });

  return (
    <>
      <PageHeader title="Contracts" description="Support agreements, licences, leases and warranties."
        actions={canWrite && tab === "contracts" && <button className="btn btn-primary" onClick={() => navigate("/contracts/new")}><Plus />New contract</button>} />
      <Tabs value={tab} onChange={setTab} tabs={[{ value: "contracts", label: "Contracts" }, { value: "vendors", label: "Vendors" }]} />
      {tab === "contracts" && <>
        <div className="toolbar">
          <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search number, name or vendor" />
          <select className="select" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} aria-label="Status">
            <option value="">Any status</option><option value="active">Active</option><option value="draft">Draft</option><option value="expired">Expired</option><option value="terminated">Terminated</option>
          </select>
        </div>
        {query.isPending && <LoadingState />}
        {query.data && (
          <Card flush>
            <DataTable rows={query.data.items} rowKey={(c) => c.id} onRowClick={(c) => navigate(`/contracts/${c.id}`)}
              empty={<EmptyState title="No contracts" />}
              columns={[
                { key: "n", label: "Number", className: "num", render: (c) => c.number },
                { key: "t", label: "Name", className: "title-cell", render: (c) => c.name },
                { key: "v", label: "Vendor", render: (c) => c.vendor_name },
                { key: "ty", label: "Type", render: (c) => <Pill value={c.contract_type} /> },
                { key: "e", label: "Ends", render: (c) => formatDay(c.end_date) },
                { key: "r", label: "Renewal", render: (c) => <Remaining c={c} /> },
                ...(canWrite ? [{ key: "val", label: "Value", render: (c: Contract) => formatMoney(c.value, c.currency) }] : []),
              ]} />
            {(query.data.next || query.data.previous) && <Pager count={query.data.count} page={page} hasNext={!!query.data.next} hasPrev={!!query.data.previous} onPage={setPage} noun="contracts" />}
          </Card>
        )}
      </>}
      {tab === "vendors" && <ResourceManager<Vendor> config={{
        title: "Vendors", noun: "vendor", endpoint: ENDPOINTS.vendors, searchable: true, canCreate: canWrite, defaults: { active: true },
        columns: [
          { key: "n", label: "Name", render: (v) => <strong>{v.name}</strong> },
          { key: "c", label: "Contact", render: (v) => v.contact_name || <span className="subtle">—</span> },
          { key: "e", label: "Email", render: (v) => v.email ? <a href={`mailto:${v.email}`}>{v.email}</a> : <span className="subtle">—</span> },
          { key: "p", label: "Phone", render: (v) => v.phone || <span className="subtle">—</span> },
        ],
        fields: [
          { name: "name", label: "Name", required: true },
          { name: "contact_name", label: "Contact name" },
          { name: "email", label: "Email", type: "email" },
          { name: "phone", label: "Phone" },
          { name: "website", label: "Website", type: "url", span: true },
          { name: "notes", label: "Notes", type: "textarea" },
          { name: "active", label: "Active", type: "checkbox", span: true },
        ],
      }} />}
    </>
  );
}
