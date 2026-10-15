import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { listAll, ENDPOINTS } from "../api/resources";

export type Option = { value: string | number; label: string };

export type LookupKey =
  | "users" | "staff" | "people" | "groups" | "categories" | "services" | "roles" | "assetTypes" | "locations"
  | "vendors" | "calendars" | "assets";

type Named = { id: number; name?: string; username?: string; first_name?: string; last_name?: string; asset_tag?: string };

const LOOKUPS: Record<LookupKey, { endpoint: string; value?: (r: Named) => string | number; label: (r: Named) => string }> = {
  users: { endpoint: ENDPOINTS.users, label: (r) => [r.first_name, r.last_name].filter(Boolean).join(" ") || r.username || String(r.id) },
  staff: { endpoint: ENDPOINTS.technicians, label: (r) => r.name || r.username || String(r.id) },
  people: { endpoint: ENDPOINTS.people, label: (r) => r.name || r.username || String(r.id) },
  groups: { endpoint: ENDPOINTS.supportGroups, label: (r) => r.name ?? "" },
  categories: { endpoint: ENDPOINTS.categories, label: (r) => r.name ?? "" },
  services: { endpoint: ENDPOINTS.services, label: (r) => r.name ?? "" },
  roles: { endpoint: ENDPOINTS.roles, value: (r) => r.name ?? "", label: (r) => r.name ?? "" },
  assetTypes: { endpoint: ENDPOINTS.assetTypes, label: (r) => r.name ?? "" },
  locations: { endpoint: ENDPOINTS.locations, label: (r) => r.name ?? "" },
  vendors: { endpoint: ENDPOINTS.vendors, label: (r) => r.name ?? "" },
  calendars: { endpoint: ENDPOINTS.calendars, label: (r) => r.name ?? "" },
  assets: { endpoint: ENDPOINTS.assets, label: (r) => `${r.asset_tag} ${r.name ?? ""}` },
};

export function useLookup(key: LookupKey | undefined) {
  return useQuery({
    queryKey: ["lookup", key],
    enabled: !!key,
    staleTime: 60_000,
    queryFn: async (): Promise<Option[]> => {
      const spec = LOOKUPS[key as LookupKey];
      const rows = await listAll<Named>(spec.endpoint, key === "users" || key === "assets" || key === "people" ? { page_size: 200 } : {});
      return rows.map((r) => ({ value: spec.value ? spec.value(r) : r.id, label: spec.label(r) }));
    },
  });
}

export type FieldDef = {
  name: string;
  label: string;
  type?: "text" | "textarea" | "number" | "checkbox" | "select" | "multiselect" | "date" | "datetime" | "json" | "password" | "email" | "url";
  options?: Option[];
  lookup?: LookupKey;
  required?: boolean;
  hint?: string;
  span?: boolean;
  nullable?: boolean;
  createOnly?: boolean;
  readOnlyOnEdit?: boolean;
  rows?: number;
};

export type Values = Record<string, unknown>;

function toLocalInput(iso: unknown) {
  if (!iso || typeof iso !== "string") return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Turn a stored record into editable form values. */
export function toFormValues(fields: FieldDef[], record: Values): Values {
  const out: Values = {};
  for (const f of fields) {
    const v = record[f.name];
    if (f.type === "json") out[f.name] = JSON.stringify(v ?? (f.name.endsWith("s") ? [] : {}), null, 2);
    else if (f.type === "datetime") out[f.name] = toLocalInput(v);
    else if (f.type === "checkbox") out[f.name] = Boolean(v);
    else if (f.type === "multiselect") out[f.name] = Array.isArray(v) ? v : [];
    else out[f.name] = v ?? "";
  }
  return out;
}

/** Convert form values to an API payload. Throws {field: message} on invalid JSON. */
export function toPayload(fields: FieldDef[], values: Values, editing: boolean): Values {
  const out: Values = {};
  const errors: Record<string, string> = {};
  for (const f of fields) {
    if (editing && (f.createOnly || f.readOnlyOnEdit)) continue;
    const v = values[f.name];
    if (f.type === "password") { if (v) out[f.name] = v; continue; }
    if (f.type === "json") {
      try { out[f.name] = JSON.parse(String(v || "null")); } catch { errors[f.name] = "Invalid JSON"; }
      continue;
    }
    if (f.type === "checkbox") { out[f.name] = Boolean(v); continue; }
    if (f.type === "multiselect") { out[f.name] = v ?? []; continue; }
    if (f.type === "datetime") { out[f.name] = v ? new Date(String(v)).toISOString() : null; continue; }
    if (v === "" || v === undefined) { out[f.name] = f.nullable || f.type === "select" || f.type === "number" || f.type === "date" ? null : ""; continue; }
    if (f.type === "number") { out[f.name] = Number(v); continue; }
    out[f.name] = v;
  }
  if (Object.keys(errors).length) throw errors;
  return out;
}

/** Map a DRF 400 response onto field names. */
export function apiFieldErrors(error: unknown): { fields: Record<string, string>; general?: string } {
  if (!axios.isAxiosError(error) || !error.response?.data || typeof error.response.data !== "object") {
    return { fields: {}, general: error instanceof Error ? error.message : "Something went wrong." };
  }
  const data = error.response.data as Record<string, unknown>;
  const fields: Record<string, string> = {};
  let general: string | undefined;
  for (const [key, value] of Object.entries(data)) {
    const message = Array.isArray(value) ? value.map(String).join(" ") : typeof value === "object" && value ? Object.entries(value).map(([k, m]) => `${k}: ${m}`).join("; ") : String(value);
    if (key === "detail" || key === "non_field_errors") general = message;
    else fields[key] = message;
  }
  if (error.response.status === 403 && !general) general = "You don't have permission to do that.";
  return { fields, general };
}

