import { MultiSelect } from "./MultiSelect";
import { Field } from "./ui";
import { useLookup, type FieldDef, type Values } from "./form";

function SelectField({ def, value, onChange, disabled, multiple }: { def: FieldDef; value: unknown; onChange: (v: unknown) => void; disabled?: boolean; multiple?: boolean }) {
  const lookup = useLookup(def.lookup);
  const options = def.options ?? lookup.data ?? [];
  const numeric = options.length > 0 && typeof options[0].value === "number";
  if (multiple) {
    return <MultiSelect options={options} value={(value as (string | number)[]) ?? []} onChange={onChange} disabled={disabled} />;
  }
  return (
    <select className="select" disabled={disabled} value={String(value ?? "")}
      onChange={(e) => onChange(e.target.value === "" ? "" : numeric ? Number(e.target.value) : e.target.value)}>
      <option value="">{def.required ? "Select…" : "None"}</option>
      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

export function EntityForm({ fields, values, onChange, errors = {}, editing = false, disabled = false }: {
  fields: FieldDef[]; values: Values; onChange: (v: Values) => void; errors?: Record<string, string>; editing?: boolean; disabled?: boolean;
}) {
  const set = (name: string, v: unknown) => onChange({ ...values, [name]: v });
  return (
    <div className="form-grid">
      {fields.filter((f) => !(editing && f.createOnly)).map((f) => {
        const isDisabled = disabled || (editing && f.readOnlyOnEdit);
        const value = values[f.name];
        const common = { disabled: isDisabled };
        let control;
        switch (f.type) {
          case "checkbox":
            return (
              <div key={f.name} className={f.span ? "span-2" : undefined}>
                <label className="checkbox"><input type="checkbox" {...common} checked={Boolean(value)} onChange={(e) => set(f.name, e.target.checked)} />{f.label}</label>
                {f.hint && <div className="field-hint">{f.hint}</div>}
                {errors[f.name] && <div className="field-error">{errors[f.name]}</div>}
              </div>
            );
          case "textarea":
          case "json":
            control = <textarea className={`textarea${f.type === "json" ? " mono" : ""}`} rows={f.rows ?? (f.type === "json" ? 8 : 4)} {...common}
              value={String(value ?? "")} onChange={(e) => set(f.name, e.target.value)} />;
            break;
          case "select":
            control = <SelectField def={f} value={value} onChange={(v) => set(f.name, v)} disabled={isDisabled} />;
            break;
          case "multiselect":
            control = <SelectField def={f} value={value} onChange={(v) => set(f.name, v)} disabled={isDisabled} multiple />;
            break;
          default:
            control = <input className="input" {...common}
              type={f.type === "datetime" ? "datetime-local" : f.type ?? "text"} autoComplete={f.type === "password" ? "new-password" : undefined}
              value={String(value ?? "")} onChange={(e) => set(f.name, e.target.value)} />;
        }
        return (
          <Field key={f.name} label={<>{f.label}{f.required && <span className="muted"> *</span>}</>} hint={f.hint} error={errors[f.name]}
            span={f.span || f.type === "textarea" || f.type === "json" || f.type === "multiselect"}>
            {control}
          </Field>
        );
      })}
    </div>
  );
}
