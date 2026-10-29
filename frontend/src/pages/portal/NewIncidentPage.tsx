import { useQuery } from "@tanstack/react-query";
import { BookOpen } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { suggestArticles } from "../../api/solutions";
import { createTicket, getCategories, getCustomFields, getServices, getTemplates, uploadAttachment } from "../../api/tickets";
import { apiFieldErrors } from "../../components/form";
import { CustomFieldsForm } from "../../components/DynamicField";
import { Card, Field, Notice, PageHeader } from "../../components/ui";
import type { TicketTemplate } from "../../types";
import { LEVELS } from "../../utils/format";

type Form = { subject: string; description: string; impact: number; urgency: number; category: string; service: string };
const EMPTY: Form = { subject: "", description: "", impact: 3, urgency: 3, category: "", service: "" };

/** Knowledge-base articles that might fix the problem before it's submitted. Opens in a new tab so the draft survives. */
function Suggestions({ subject }: { subject: string }) {
  const [term, setTerm] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setTerm(subject.trim()), 400);
    return () => clearTimeout(timer);
  }, [subject]);
  const query = useQuery({ queryKey: ["article-suggestions", term], enabled: term.length >= 3, queryFn: () => suggestArticles(term) });
  if (term.length < 3 || !query.data || query.data.length === 0) return null;
  return (
    <div className="suggestions" aria-live="polite">
      <strong>These articles might fix it</strong>
      <div className="list">
        {query.data.map((a) => (
          <a className="list-item" key={a.id} href={`/knowledge/${a.id}`} target="_blank" rel="noopener noreferrer">
            <BookOpen /><span><span>{a.title}</span>{a.summary && <span className="subtle"> · {a.summary}</span>}</span>
          </a>
        ))}
      </div>
    </div>
  );
}

export function NewIncidentPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<Form>(EMPTY);
  const [template, setTemplate] = useState<TicketTemplate | null>(null);
  const [custom, setCustom] = useState<Record<string, unknown>>({});
  const [files, setFiles] = useState<File[]>([]);
  const [errors, setErrors] = useState<{ fields: Record<string, string>; general?: string }>({ fields: {} });
  const [submitting, setSubmitting] = useState(false);
  const categories = useQuery({ queryKey: ["lookup", "categories"], queryFn: getCategories });
  const services = useQuery({ queryKey: ["lookup", "services"], queryFn: getServices });
  const templates = useQuery({ queryKey: ["templates"], queryFn: getTemplates });
  const customDefs = useQuery({ queryKey: ["custom-fields", "ticket"], queryFn: () => getCustomFields("ticket") });
  const set = <K extends keyof Form>(key: K, value: Form[K]) => setForm((f) => ({ ...f, [key]: value }));

  function applyTemplate(id: string) {
    const t = templates.data?.find((x) => String(x.id) === id) ?? null;
    setTemplate(t);
    if (t) setForm({ subject: t.subject, description: t.description, impact: t.impact, urgency: t.urgency,
      category: t.category ? String(t.category) : "", service: t.service ? String(t.service) : "" });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const local: Record<string, string> = {};
    if (form.subject.trim().length < 5) local.subject = "Use at least 5 characters.";
    if (form.description.trim().length < 10) local.description = "Describe the issue in at least 10 characters.";
    if (Object.keys(local).length) { setErrors({ fields: local }); return; }
    setSubmitting(true);
    setErrors({ fields: {} });
    try {
      const ticket = await createTicket({
        request_type: template?.request_type ?? "incident",
        subject: form.subject.trim(), description: form.description.trim(), impact: form.impact, urgency: form.urgency,
        category: form.category ? Number(form.category) : null, service: form.service ? Number(form.service) : null,
        template: template?.id ?? null, custom_fields: custom,
      });
      const failed: string[] = [];
      for (const file of files) {
        try { await uploadAttachment(ticket.public_id, file); } catch (e) { failed.push(`${file.name}: ${apiFieldErrors(e).fields.file ?? "upload failed"}`); }
      }
      navigate(`/portal/tickets/${ticket.public_id}`, { replace: true, state: { uploadErrors: failed } });
    } catch (error) {
      setErrors(apiFieldErrors(error));
      setSubmitting(false);
    }
  }

  return (
    <div style={{ maxWidth: 760 }}>
      <PageHeader title="Report an issue" description="Tell us what's wrong. Priority is worked out from impact and urgency." />
      <form onSubmit={submit} noValidate className="stack">
        {templates.data && templates.data.length > 0 && (
          <Card>
            <Field label="Start from a template" hint={template?.help_text || "Optional. Templates fill in common details and route your request to the right team."}>
              <select className="select" value={template?.id ?? ""} onChange={(e) => applyTemplate(e.target.value)}>
                <option value="">Blank request</option>
                {templates.data.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </Field>
          </Card>
        )}
        <Card>
          <div className="form-grid">
            <Field label="Summary" span error={errors.fields.subject}>
              <input className="input" value={form.subject} onChange={(e) => set("subject", e.target.value)} placeholder="VPN disconnects every few minutes" />
              <Suggestions subject={form.subject} />
            </Field>
            <Field label="Description" span error={errors.fields.description}>
              <textarea className="textarea" rows={6} value={form.description} onChange={(e) => set("description", e.target.value)} placeholder="What happened, what you expected, and what you've tried." />
            </Field>
            <Field label="Impact" hint="How many people are affected?">
              <select className="select" value={form.impact} onChange={(e) => set("impact", Number(e.target.value))}>{LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}</select>
            </Field>
            <Field label="Urgency" hint="How soon does it need fixing?">
              <select className="select" value={form.urgency} onChange={(e) => set("urgency", Number(e.target.value))}>{LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}</select>
            </Field>
            <Field label="Category">
              <select className="select" value={form.category} onChange={(e) => set("category", e.target.value)}>
                <option value="">Not sure</option>{categories.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </Field>
            <Field label="Affected service">
              <select className="select" value={form.service} onChange={(e) => set("service", e.target.value)}>
                <option value="">Not sure</option>{services.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </Field>
          </div>
          {customDefs.data && customDefs.data.length > 0 && <div style={{ marginTop: 14 }}><CustomFieldsForm defs={customDefs.data} values={custom} onChange={setCustom} /></div>}
          {errors.fields.custom_fields && <div className="field-error" style={{ marginTop: 8 }}>{errors.fields.custom_fields}</div>}
        </Card>
        <Card>
          <Field label="Attachments" hint="Up to 10 MB each. Files are scanned for malware; executables and scripts are blocked.">
            <input className="input" type="file" multiple onChange={(e) => setFiles(Array.from(e.target.files ?? []))} style={{ paddingTop: 5 }} />
          </Field>
        </Card>
        {errors.general && <Notice tone="error">{errors.general}</Notice>}
        <div className="form-actions"><button className="btn btn-primary" disabled={submitting}>{submitting ? "Submitting…" : "Submit request"}</button></div>
      </form>
    </div>
  );
}
