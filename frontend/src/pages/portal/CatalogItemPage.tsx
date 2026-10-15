import { useMutation, useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getCatalogItem, submitCatalogItem } from "../../api/catalog";
import { apiErrorMessage } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/Feedback";
import type { CatalogField } from "../../types";

// UI convenience only: Django re-validates required fields, types, options and
// conditional visibility against the same schema.
function visible(field: CatalogField, values: Record<string, unknown>) {
  if (!field.show_when) return true;
  return values[field.show_when.field] === field.show_when.equals;
}

export function CatalogItemPage() {
  const { slug = "" } = useParams();
  const navigate = useNavigate();
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [validationError, setValidationError] = useState("");
  const query = useQuery({ queryKey: ["catalog-item", slug], queryFn: () => getCatalogItem(slug), enabled: !!slug });
  const fields = query.data?.form_schema ?? [];
  const mutation = useMutation({
    // Only send answers for visible fields.
    mutationFn: () => submitCatalogItem(slug, Object.fromEntries(
      fields.filter((f) => visible(f, values) && values[f.key] !== undefined).map((f) => [f.key, values[f.key]]),
    )),
    onSuccess: (ticket) => navigate(`/portal/tickets/${ticket.public_id}`),
  });

  if (query.isPending) return <LoadingState />;
  if (query.isError) return <ErrorState message={apiErrorMessage(query.error)} />;

  function submit(event: FormEvent) {
    event.preventDefault();
    const missing = fields.filter((f) => visible(f, values) && f.required && f.type !== "boolean" && (values[f.key] === undefined || values[f.key] === ""));
    if (missing.length) {
      setValidationError(`Complete required field: ${missing[0].label}`);
      return;
    }
    setValidationError("");
    mutation.mutate();
  }

  return (
    <section className="form-card">
      <h1>{query.data.name}</h1><p>{query.data.description || query.data.short_description}</p>
      {query.data.requires_approval && <div className="alert">This request needs approval before it is fulfilled.</div>}
      <form onSubmit={submit}>
        {fields.filter((field) => visible(field, values)).map((field) => (
          <DynamicField key={field.key} field={field} value={values[field.key]} setValue={(value) => setValues((old) => ({ ...old, [field.key]: value }))} />
        ))}
        {validationError && <div className="alert alert--error">{validationError}</div>}
        {mutation.isError && <div className="alert alert--error">{apiErrorMessage(mutation.error)}</div>}
        <button className="button" disabled={mutation.isPending}>{mutation.isPending ? "Submitting..." : "Submit request"}</button>
      </form>
    </section>
  );
}

function DynamicField({ field, value, setValue }: { field: CatalogField; value: unknown; setValue: (value: unknown) => void }) {
  const label = <>{field.label}{field.required && " *"}</>;
  if (field.type === "boolean") return <label className="checkbox-row"><input type="checkbox" checked={Boolean(value)} onChange={(e) => setValue(e.target.checked)} />{label}</label>;
  if (field.type === "select") return <label>{label}<select value={String(value ?? "")} onChange={(e) => setValue(e.target.value)}><option value="">Select...</option>{field.options?.map((option) => <option key={option}>{option}</option>)}</select></label>;
  if (field.type === "textarea") return <label>{label}<textarea rows={5} value={String(value ?? "")} onChange={(e) => setValue(e.target.value)} /></label>;
  return <label>{label}<input type={field.type === "date" ? "date" : "text"} value={String(value ?? "")} onChange={(e) => setValue(e.target.value)} /></label>;
}
