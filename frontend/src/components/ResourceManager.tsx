import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState, type ReactNode } from "react";
import { createResource, deleteResource, listResource, updateResource } from "../api/resources";
import { EntityForm } from "./EntityForm";
import { apiFieldErrors, toFormValues, toPayload, type FieldDef, type Values } from "./form";
import { Card, DataTable, Drawer, ErrorState, LoadingState, Notice, Pager, SearchInput, type Column } from "./ui";

type Row = { id: number | string } & Record<string, unknown>;

export type ResourceConfig<T extends Row> = {
  title: string;
  noun: string;
  endpoint: string;
  columns: Column<T>[];
  fields: FieldDef[];
  defaults?: Values;
  canCreate?: boolean;
  canDelete?: boolean;
  searchable?: boolean;
  description?: ReactNode;
  params?: Record<string, unknown>;
};

/** Generic list + drawer editor used by the admin console and module setup screens. */
export function ResourceManager<T extends Row>({ config }: { config: ResourceConfig<T> }) {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<T | "new" | null>(null);
  const [values, setValues] = useState<Values>({});
  const [errors, setErrors] = useState<{ fields: Record<string, string>; general?: string }>({ fields: {} });
  const key = ["resource", config.endpoint, page, search, config.params];
  const query = useQuery({ queryKey: key, queryFn: () => listResource<T>(config.endpoint, { page, search: search || undefined, ...config.params }) });

  const isNew = editing === "new";
  const close = () => { setEditing(null); setErrors({ fields: {} }); };
  const open = (row: T | "new") => {
    setEditing(row);
    setErrors({ fields: {} });
    setValues(row === "new" ? toFormValues(config.fields, config.defaults ?? {}) : toFormValues(config.fields, row));
  };
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["resource", config.endpoint] }).then(() =>
    queryClient.invalidateQueries({ queryKey: ["lookup"] }));

  const save = useMutation({
    mutationFn: () => {
      let payload: Values;
      try {
        payload = toPayload(config.fields, values, !isNew);
      } catch (fieldErrors) {
        return Promise.reject({ local: fieldErrors });
      }
      return isNew ? createResource<T>(config.endpoint, payload) : updateResource<T>(config.endpoint, (editing as T).id, payload);
    },
    onSuccess: async () => { close(); await refresh(); },
    onError: (error: unknown) => {
      if (error && typeof error === "object" && "local" in error) setErrors({ fields: (error as { local: Record<string, string> }).local });
      else setErrors(apiFieldErrors(error));
    },
  });
  const remove = useMutation({
    mutationFn: () => deleteResource(config.endpoint, (editing as T).id),
    onSuccess: async () => { close(); await refresh(); },
    onError: (error: unknown) => setErrors(apiFieldErrors(error)),
  });

  const data = query.data;
  return (
    <Card
      title={config.title}
      flush
      actions={config.canCreate !== false && <button className="btn btn-primary btn-sm" onClick={() => open("new")}><Plus />New {config.noun}</button>}
    >
      {config.description && <div className="card-body muted">{config.description}</div>}
      {config.searchable && <div className="card-body" style={{ paddingBottom: 0 }}><SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder={`Search ${config.noun}s`} /></div>}
      {query.isPending && <LoadingState rows={3} />}
      {query.isError && <div className="card-body"><ErrorState message="Could not load this list." /></div>}
      {data && <DataTable rows={data.items} columns={config.columns} rowKey={(r) => r.id} onRowClick={(r) => open(r)} />}
      {data && (data.next || data.previous) && (
        <Pager count={data.count} page={page} hasNext={!!data.next} hasPrev={!!data.previous} onPage={setPage} noun={`${config.noun}s`} />
      )}

      {editing && (
        <Drawer
          title={isNew ? `New ${config.noun}` : `Edit ${config.noun}`}
          onClose={close}
          footer={<>
            <div>{!isNew && config.canDelete && <button className="btn btn-danger" disabled={remove.isPending} onClick={() => { if (confirm(`Delete this ${config.noun}?`)) remove.mutate(); }}>Delete</button>}</div>
            <div className="row">
              <button className="btn btn-secondary" onClick={close}>Cancel</button>
              <button className="btn btn-primary" disabled={save.isPending} onClick={() => save.mutate()}>{save.isPending ? "Saving…" : "Save"}</button>
            </div>
          </>}
        >
          <div className="stack">
            {errors.general && <Notice tone="error">{errors.general}</Notice>}
            <EntityForm fields={config.fields} values={values} onChange={setValues} errors={errors.fields} editing={!isNew} />
          </div>
        </Drawer>
      )}
    </Card>
  );
}
