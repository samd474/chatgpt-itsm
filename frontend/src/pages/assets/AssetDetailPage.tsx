import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Link2, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, apiErrorMessage } from "../../api/client";
import { createResource, getAction, getResource, listAll, postAction, updateResource, ENDPOINTS } from "../../api/resources";
import { getCustomFields } from "../../api/tickets";
import { useAuth } from "../../auth/context";
import { isStaff } from "../../auth/roles";
import { Pill, StatusBadge } from "../../components/badges";
import { useLookup } from "../../components/form";
import { RecordEditor } from "../../components/RecordEditor";
import { Card, ErrorState, LoadingState, Notice, PageHeader } from "../../components/ui";
import type { Asset, AssetRelationship, AuditEvent, Contract } from "../../types";
import { formatDay, relativeTime } from "../../utils/format";
import { ASSET_FIELDS } from "./assetFields";

const KINDS = [{ value: "depends_on", label: "Depends on" }, { value: "runs_on", label: "Runs on" }, { value: "connected_to", label: "Connected to" }, { value: "contains", label: "Contains" }];

function Relationships({ asset, canEdit }: { asset: Asset; canEdit: boolean }) {
  const queryClient = useQueryClient();
  const [target, setTarget] = useState("");
  const [kind, setKind] = useState("depends_on");
  const assets = useLookup(canEdit ? "assets" : undefined);
  const rels = useQuery({ queryKey: ["asset-rels", asset.id], queryFn: () => getAction<AssetRelationship[]>(`${ENDPOINTS.assets}${asset.id}/relationships/`) });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["asset-rels", asset.id] });
  const add = useMutation({ mutationFn: () => postAction(`${ENDPOINTS.assets}${asset.id}/relationships/`, { target: Number(target), kind }), onSuccess: () => { setTarget(""); void refresh(); } });
  const remove = useMutation({ mutationFn: (id: number) => api.delete(`${ENDPOINTS.assets}${asset.id}/relationships/${id}/`), onSuccess: () => void refresh() });
  return (
    <Card title="Relationships">
      {rels.data?.length === 0 && <p className="subtle">No related assets.</p>}
      <div className="list">
        {rels.data?.map((r) => (
          <div className="list-item" key={r.id}>
            <Link to={`/assets/${r.source}`}>{r.source_label}</Link><ArrowRight /><span className="muted">{KINDS.find((k) => k.value === r.kind)?.label}</span><ArrowRight />
            <Link to={`/assets/${r.target}`}>{r.target_label}</Link><span className="spacer" />
            {canEdit && <button className="btn btn-ghost btn-icon btn-sm" aria-label="Remove" onClick={() => remove.mutate(r.id)}><Trash2 /></button>}
          </div>
        ))}
      </div>
      {canEdit && (
        <div className="row" style={{ marginTop: 10 }}>
          <select className="select" style={{ width: 150 }} value={kind} onChange={(e) => setKind(e.target.value)}>{KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}</select>
          <select className="select" style={{ flex: 1 }} value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="">Choose asset…</option>{assets.data?.filter((a) => a.value !== asset.id).map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
          <button className="btn btn-secondary" disabled={!target || add.isPending} onClick={() => add.mutate()}>Add</button>
        </div>
      )}
      {add.isError && <div style={{ marginTop: 8 }}><Notice tone="error">{apiErrorMessage(add.error)}</Notice></div>}
    </Card>
  );
}

export function AssetDetailPage() {
  const { id = "" } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canEdit = isStaff(user);
  const [ticketRef, setTicketRef] = useState("");
  const asset = useQuery({ queryKey: ["asset", id], enabled: !isNew, queryFn: () => getResource<Asset>(ENDPOINTS.assets, id) });
  const customDefs = useQuery({ queryKey: ["custom-fields", "asset"], queryFn: () => getCustomFields("asset") });
  const history = useQuery({ queryKey: ["asset-history", id], enabled: !isNew, queryFn: () => getAction<AuditEvent[]>(`${ENDPOINTS.assets}${id}/history/`) });
  const contracts = useQuery({ queryKey: ["asset-contracts", id], enabled: !isNew, queryFn: () => listAll<Contract>(ENDPOINTS.contracts, { assets: id }) });
  const link = useMutation({
    mutationFn: () => postAction<Asset>(`${ENDPOINTS.assets}${id}/link-ticket/`, { help_request: ticketRef.trim() }),
    onSuccess: (a) => { setTicketRef(""); queryClient.setQueryData(["asset", id], a); },
  });

  if (!isNew && asset.isPending) return <LoadingState />;
  if (!isNew && asset.isError) return <ErrorState message={apiErrorMessage(asset.error)} />;
  if (customDefs.isPending) return <LoadingState />;
  const a = asset.data;

  return (
    <>
      <PageHeader eyebrow={a?.asset_tag ?? "Assets"} title={a?.name ?? "New asset"} actions={a && <Pill value={a.status} />} />
      <div className="grid-main">
        <div className="stack">
          <RecordEditor<Asset>
            key={a?.updated_at ?? "new"}
            fields={ASSET_FIELDS}
            record={a ? (a as unknown as Record<string, unknown>) : null}
            customDefs={customDefs.data}
            readOnly={!canEdit}
            saveLabel={isNew ? "Create asset" : "Save changes"}
            save={(payload) => (isNew ? createResource<Asset>(ENDPOINTS.assets, payload) : updateResource<Asset>(ENDPOINTS.assets, id, payload))}
            onSaved={(saved) => {
              void queryClient.invalidateQueries({ queryKey: ["assets"] });
              void queryClient.invalidateQueries({ queryKey: ["asset-history", id] });
              if (isNew) navigate(`/assets/${saved.id}`, { replace: true });
              else queryClient.setQueryData(["asset", id], saved);
            }}
          />
          {a && <Relationships asset={a} canEdit={canEdit} />}
        </div>
        {a && (
          <div className="stack">
            <Card title="Linked tickets">
              {a.linked_tickets?.length === 0 && <p className="subtle">No tickets linked.</p>}
              <div className="list">
                {a.linked_tickets?.map((t) => (
                  <div className="list-item" key={t.public_id}><Link2 /><Link to={`/tech/tickets/${t.public_id}`}>{t.request_number}</Link><span className="title-cell muted">{t.subject}</span><span className="spacer" /><StatusBadge status={t.status} /></div>
                ))}
              </div>
              {canEdit && <form className="row" style={{ marginTop: 10 }} onSubmit={(e) => { e.preventDefault(); link.mutate(); }}>
                <input className="input" style={{ flex: 1 }} placeholder="Ticket ID (UUID)" value={ticketRef} onChange={(e) => setTicketRef(e.target.value)} />
                <button className="btn btn-secondary" disabled={!ticketRef.trim()}>Link</button>
              </form>}
              {link.isError && <div style={{ marginTop: 8 }}><Notice tone="error">{apiErrorMessage(link.error)}</Notice></div>}
            </Card>
            <Card title="Contracts">
              {contracts.data?.length === 0 && <p className="subtle">Not covered by any contract.</p>}
              <div className="list">{contracts.data?.map((c) => <div className="list-item" key={c.id}><Link to={`/contracts/${c.id}`}>{c.number}</Link><span className="muted">{c.vendor_name}</span><span className="spacer" /><span className="subtle">ends {formatDay(c.end_date)}</span></div>)}</div>
            </Card>
            <Card title="History">
              <div className="list">
                {history.data?.slice(0, 12).map((e) => <div className="list-item" key={e.id}><code>{e.event_type.replace("asset.", "")}</code><span className="muted">{e.actor_name ?? "System"}</span><span className="spacer" /><span className="subtle">{relativeTime(e.created_at)}</span></div>)}
              </div>
            </Card>
          </div>
        )}
      </div>
    </>
  );
}
