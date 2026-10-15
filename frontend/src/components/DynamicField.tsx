import type { CatalogField, CustomFieldDef } from "../types";
import { Field } from "./ui";

function toCatalogField(def: CustomFieldDef): CatalogField {
  return { key: def.key, label: def.label, type: def.field_type, required: def.required, options: def.options };
}

export function DynamicField({ field, value, setValue, disabled }: { field: CatalogField; value: unknown; setValue: (value: unknown) => void; disabled?: boolean }) {
  const label = <>{field.label}{field.required && <span className="muted"> *</span>}</>;
  if (field.type === "boolean") {
    return <label className="checkbox"><input type="checkbox" disabled={disabled} checked={Boolean(value)} onChange={(e) => setValue(e.target.checked)} />{label}</label>;
  }
  if (field.type === "select") {
    return (
      <Field label={label}>
        <select className="select" disabled={disabled} value={String(value ?? "")} onChange={(e) => setValue(e.target.value)}>
          <option value="">Select…</option>
          {field.options?.map((option) => <option key={option}>{option}</option>)}
        </select>
      </Field>
    );
  }
  if (field.type === "textarea") {
    return <Field label={label} span><textarea className="textarea" disabled={disabled} rows={4} value={String(value ?? "")} onChange={(e) => setValue(e.target.value)} /></Field>;
  }
  return <Field label={label}><input className="input" disabled={disabled} type={field.type === "date" ? "date" : "text"} value={String(value ?? "")} onChange={(e) => setValue(e.target.value)} /></Field>;
}

export function CustomFieldsForm({ defs, values, onChange, disabled }: { defs: CustomFieldDef[]; values: Record<string, unknown>; onChange: (v: Record<string, unknown>) => void; disabled?: boolean }) {
  if (defs.length === 0) return null;
  return (
    <div className="form-grid">
      {defs.map((def) => (
        <DynamicField key={def.key} field={toCatalogField(def)} value={values[def.key]} disabled={disabled}
          setValue={(v) => onChange({ ...values, [def.key]: v })} />
      ))}
    </div>
  );
}
