import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { confirmImport, uploadImport } from "../../api/operations";
import { apiErrorMessage } from "../../api/client";
import type { ImportJob } from "../../types";

function CsvImport() {
  const [kind, setKind] = useState<ImportJob["kind"]>("categories");
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<ImportJob | null>(null);
  const upload = useMutation({ mutationFn: () => uploadImport(kind, file as File), onSuccess: setJob });
  const confirm = useMutation({ mutationFn: () => confirmImport((job as ImportJob).id), onSuccess: setJob });

  return (
    <div className="panel">
      <h2>CSV import</h2>
      <p className="muted">Upload, review the preview, then confirm. Nothing changes until you confirm.</p>
      <p className="help-text">Columns: categories <code>name,parent,active</code> · services <code>name,owner_group,active</code></p>
      <div className="form-grid">
        <label>Import
          <select value={kind} onChange={(e) => { setKind(e.target.value as ImportJob["kind"]); setJob(null); }}>
            <option value="categories">Categories</option>
            <option value="services">Services</option>
          </select>
        </label>
        <label>CSV file<input type="file" accept=".csv,text/csv" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setJob(null); }} /></label>
      </div>
      <button className="button button--secondary" disabled={!file || upload.isPending} onClick={() => upload.mutate()}>Validate</button>
      {upload.isError && <div className="alert alert--error">{apiErrorMessage(upload.error)}</div>}

      {job && (
        <div className="import-preview">
          <p><strong>{job.preview.valid.length}</strong> valid rows, <strong>{job.preview.errors.length}</strong> errors, <strong>{job.preview.warnings.length}</strong> warnings.</p>
          {job.preview.errors.map((e) => <div key={`e${e.row}`} className="field-error">Row {e.row}: {e.error}</div>)}
          {job.preview.warnings.map((w, i) => <div key={`w${i}`} className="muted">Row {w.row}: {w.warning}</div>)}
          {job.state === "validated" ? (
            <button className="button" disabled={confirm.isPending || job.preview.valid.length === 0} onClick={() => confirm.mutate()}>
              Import {job.preview.valid.length} rows
            </button>
          ) : (
            <div className="alert">Imported: {job.result.created} created, {job.result.updated} updated.</div>
          )}
          {confirm.isError && <div className="alert alert--error">{apiErrorMessage(confirm.error)}</div>}
        </div>
      )}
    </div>
  );
}

export function AdminConfigPage() {
  return (
    <section>
      <div className="page-heading"><div><h1>Configuration</h1><p>Use Django admin for setup; dedicated screens replace it where they add safety or speed.</p></div></div>
      <div className="card-grid">
        <a className="catalog-card" href="/admin/" target="_blank" rel="noreferrer">
          <h2>Django administration</h2>
          <p>Users and roles, support groups, categories, services, catalog items, business calendars and SLA policies.</p>
        </a>
        <a className="catalog-card" href="/admin/slas/slapolicy/" target="_blank" rel="noreferrer">
          <h2>SLA policies</h2><p>Response and resolution targets per ticket type and priority.</p>
        </a>
        <a className="catalog-card" href="/admin/catalog/catalogitem/" target="_blank" rel="noreferrer">
          <h2>Catalog items</h2><p>Form schemas, routing and approval rules for service requests.</p>
        </a>
      </div>
      <CsvImport />
    </section>
  );
}
