import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { apiErrorMessage } from "../../api/client";
import { createResource, getResource, updateResource, ENDPOINTS } from "../../api/resources";
import { getCustomFields } from "../../api/tickets";
import { useAuth } from "../../auth/context";
import { hasRole } from "../../auth/roles";
import { Pill } from "../../components/badges";
import type { FieldDef } from "../../components/form";
import { RecordEditor } from "../../components/RecordEditor";
import { ErrorState, LoadingState, Notice, PageHeader } from "../../components/ui";
import type { Contract } from "../../types";

const BASE_FIELDS: FieldDef[] = [
  { name: "name", label: "Name", required: true },
  { name: "vendor", label: "Vendor", type: "select", lookup: "vendors", required: true },
  { name: "contract_type", label: "Type", type: "select", required: true, options: [
    { value: "support", label: "Support" }, { value: "license", label: "Software licence" }, { value: "lease", label: "Lease" },
    { value: "maintenance", label: "Maintenance" }, { value: "warranty", label: "Warranty" }, { value: "service", label: "Service agreement" }] },
  { name: "status", label: "Status", type: "select", required: true, options: [
    { value: "draft", label: "Draft" }, { value: "active", label: "Active" }, { value: "expired", label: "Expired" }, { value: "terminated", label: "Terminated" }] },
  { name: "start_date", label: "Start date", type: "date", required: true },
  { name: "end_date", label: "End date", type: "date", required: true },
  { name: "owner", label: "Owner", type: "select", lookup: "people" },
  { name: "renewal_notice_days", label: "Remind this many days before end", type: "number" },
  { name: "auto_renew", label: "Renews automatically", type: "checkbox", span: true },
  { name: "assets", label: "Covered assets", type: "multiselect", lookup: "assets" },
  { name: "services", label: "Covered services", type: "multiselect", lookup: "services" },
  { name: "notes", label: "Notes", type: "textarea" },
];
const FINANCIAL_FIELDS: FieldDef[] = [
  { name: "value", label: "Contract value", type: "number" },
  { name: "currency", label: "Currency", hint: "Three-letter code, e.g. USD" },
  { name: "billing_frequency", label: "Billing", type: "select", options: [
    { value: "one_time", label: "One-time" }, { value: "monthly", label: "Monthly" }, { value: "quarterly", label: "Quarterly" }, { value: "annual", label: "Annual" }] },
];

export function ContractDetailPage() {
  const { id = "" } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canWrite = hasRole(user, "Manager", "Administrator");
  const seesMoney = hasRole(user, "Manager", "Administrator", "Auditor");
  const contract = useQuery({ queryKey: ["contract", id], enabled: !isNew, queryFn: () => getResource<Contract>(ENDPOINTS.contracts, id) });
  const customDefs = useQuery({ queryKey: ["custom-fields", "contract"], queryFn: () => getCustomFields("contract") });

  if (!isNew && contract.isPending) return <LoadingState />;
  if (!isNew && contract.isError) return <ErrorState message={apiErrorMessage(contract.error)} />;
  if (customDefs.isPending) return <LoadingState />;
  const c = contract.data;

  return (
    <div style={{ maxWidth: 880 }}>
      <PageHeader eyebrow={c?.number ?? "Contracts"} title={c?.name ?? "New contract"} description={c && `${c.vendor_name} · ${c.days_remaining >= 0 ? `${c.days_remaining} days remaining` : "ended"}`}
        actions={c && <Pill value={c.status} />} />
      <div className="stack">
        {!seesMoney && <Notice>Financial terms are visible to managers only.</Notice>}
        <RecordEditor<Contract>
          key={c?.number ?? "new"}
          fields={seesMoney ? [...BASE_FIELDS, ...FINANCIAL_FIELDS] : BASE_FIELDS}
          record={c ? (c as unknown as Record<string, unknown>) : null}
          customDefs={customDefs.data}
          readOnly={!canWrite}
          saveLabel={isNew ? "Create contract" : "Save changes"}
          save={(payload) => (isNew ? createResource<Contract>(ENDPOINTS.contracts, payload) : updateResource<Contract>(ENDPOINTS.contracts, id, payload))}
          onSaved={(saved) => {
            void queryClient.invalidateQueries({ queryKey: ["contracts"] });
            if (isNew) navigate(`/contracts/${saved.id}`, { replace: true });
            else queryClient.setQueryData(["contract", id], saved);
          }}
        />
      </div>
    </div>
  );
}
