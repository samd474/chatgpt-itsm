import { useMutation, useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getCatalogItem, submitCatalogItem } from "../../api/catalog";
import { apiErrorMessage } from "../../api/client";
import { DynamicField } from "../../components/DynamicField";
import { Card, ErrorState, LoadingState, Notice, PageHeader } from "../../components/ui";
import type { CatalogField } from "../../types";

// UI convenience only: Django re-validates required fields, types, options and visibility.
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
    if (missing.length) { setValidationError(`Please complete "${missing[0].label}".`); return; }
    setValidationError("");
    mutation.mutate();
  }

  return (
    <div style={{ maxWidth: 720 }}>
      <PageHeader eyebrow="Service catalog" title={query.data.name} description={query.data.description || query.data.short_description} />
      <form onSubmit={submit} className="stack">
        {query.data.requires_approval && <Notice tone="warn">This request needs approval before work starts.</Notice>}
        <Card>
          {fields.length === 0 ? <p className="muted">No extra details needed — just submit.</p> : (
            <div className="form-grid">
              {fields.filter((f) => visible(f, values)).map((field) => (
                <DynamicField key={field.key} field={field} value={values[field.key]} setValue={(v) => setValues((old) => ({ ...old, [field.key]: v }))} />
              ))}
            </div>
          )}
        </Card>
        {validationError && <Notice tone="error">{validationError}</Notice>}
        {mutation.isError && <Notice tone="error">{apiErrorMessage(mutation.error)}</Notice>}
        <div className="form-actions"><button className="btn btn-primary" disabled={mutation.isPending}>{mutation.isPending ? "Submitting…" : "Submit request"}</button></div>
      </form>
    </div>
  );
}
