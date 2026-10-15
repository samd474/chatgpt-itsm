import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { CustomFieldsForm } from "./DynamicField";
import { EntityForm } from "./EntityForm";
import { apiFieldErrors, toFormValues, toPayload, type FieldDef, type Values } from "./form";
import { Card, Notice } from "./ui";
import type { CustomFieldDef } from "../types";

/** Inline edit card for a record: shows a form, saves with PATCH (or POST for new). */
export function RecordEditor<T>({ title = "Details", fields, record, customDefs, save, onSaved, readOnly, saveLabel = "Save changes" }: {
  title?: string;
  fields: FieldDef[];
  record: Values | null;
  customDefs?: CustomFieldDef[];
  save: (payload: Values) => Promise<T>;
  onSaved: (saved: T) => void;
  readOnly?: boolean;
  saveLabel?: string;
}) {
  const editing = record !== null;
  const [values, setValues] = useState<Values>(() => toFormValues(fields, record ?? {}));
  const [custom, setCustom] = useState<Record<string, unknown>>(() => ((record?.custom_fields as Record<string, unknown>) ?? {}));
  const [errors, setErrors] = useState<{ fields: Record<string, string>; general?: string }>({ fields: {} });
  const mutation = useMutation({
    mutationFn: () => {
      let payload: Values;
      try { payload = toPayload(fields, values, editing); } catch (local) { return Promise.reject({ local }); }
      if (customDefs && customDefs.length) payload.custom_fields = custom;
      return save(payload);
    },
    onSuccess: (saved) => { setErrors({ fields: {} }); onSaved(saved); },
    onError: (error: unknown) => {
      if (error && typeof error === "object" && "local" in error) setErrors({ fields: (error as { local: Record<string, string> }).local });
      else setErrors(apiFieldErrors(error));
    },
  });

  return (
    <Card title={title} actions={!readOnly && <button className="btn btn-primary btn-sm" disabled={mutation.isPending} onClick={() => mutation.mutate()}>{mutation.isPending ? "Saving…" : saveLabel}</button>}>
      <div className="stack">
        {errors.general && <Notice tone="error">{errors.general}</Notice>}
        {mutation.isSuccess && !errors.general && <Notice tone="success">Saved.</Notice>}
        <EntityForm fields={fields} values={values} onChange={setValues} errors={errors.fields} editing={editing} disabled={readOnly} />
        {customDefs && customDefs.length > 0 && <CustomFieldsForm defs={customDefs} values={custom} onChange={setCustom} disabled={readOnly} />}
        {errors.fields.custom_fields && <div className="field-error">{errors.fields.custom_fields}</div>}
      </div>
    </Card>
  );
}
