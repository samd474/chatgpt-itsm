import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { createTicket, getCategories, getServices, uploadAttachment } from "../../api/tickets";
import { apiErrorMessage } from "../../api/client";
import { LEVELS } from "../../utils/format";

const optionalId = z.preprocess((v) => (v === "" || v === undefined ? null : Number(v)), z.number().int().nullable());

const schema = z.object({
  subject: z.string().trim().min(5, "Use at least 5 characters.").max(240),
  description: z.string().trim().min(10, "Describe the issue in at least 10 characters."),
  impact: z.coerce.number().int().min(1).max(3),
  urgency: z.coerce.number().int().min(1).max(3),
  category: optionalId,
  service: optionalId,
});

type IncidentFormInput = z.input<typeof schema>;
type IncidentForm = z.output<typeof schema>;

export function NewIncidentPage() {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const categories = useQuery({ queryKey: ["lookup", "categories"], queryFn: getCategories });
  const services = useQuery({ queryKey: ["lookup", "services"], queryFn: getServices });
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<IncidentFormInput, unknown, IncidentForm>({
    resolver: zodResolver(schema),
    defaultValues: { impact: 3, urgency: 3, category: "", service: "" },
  });

  async function onSubmit(values: IncidentForm) {
    setServerError("");
    try {
      const ticket = await createTicket({ request_type: "incident", ...values });
      const failed: string[] = [];
      for (const file of files) {
        try {
          await uploadAttachment(ticket.public_id, file);
        } catch (error) {
          failed.push(`${file.name}: ${apiErrorMessage(error)}`);
        }
      }
      navigate(`/portal/tickets/${ticket.public_id}`, { replace: true, state: { uploadErrors: failed } });
    } catch (error) {
      setServerError(apiErrorMessage(error));
    }
  }

  return (
    <section className="form-card">
      <h1>Report an incident</h1>
      <p className="muted">Priority is calculated by the service desk from impact and urgency.</p>
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <label>Short summary
          <input {...register("subject")} placeholder="VPN disconnects every few minutes" />
        </label>
        {errors.subject && <div className="field-error">{errors.subject.message}</div>}

        <label>Description
          <textarea rows={7} {...register("description")} placeholder="What happened, what you expected, and what you already tried." />
        </label>
        {errors.description && <div className="field-error">{errors.description.message}</div>}

        <div className="form-grid">
          <label>Impact
            <select {...register("impact")}>{LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}</select>
          </label>
          <label>Urgency
            <select {...register("urgency")}>{LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}</select>
          </label>
          <label>Category
            <select {...register("category")}>
              <option value="">Not sure</option>
              {categories.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          <label>Affected service
            <select {...register("service")}>
              <option value="">Not sure</option>
              {services.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
        </div>

        <label>Attachments
          <input type="file" multiple onChange={(e) => setFiles(Array.from(e.target.files ?? []))} />
        </label>
        <div className="help-text">Up to 10 MB each. Executables and scripts are blocked.</div>

        {serverError && <div className="alert alert--error">{serverError}</div>}
        <button className="button" disabled={isSubmitting}>{isSubmitting ? "Submitting..." : "Create incident"}</button>
      </form>
    </section>
  );
}
