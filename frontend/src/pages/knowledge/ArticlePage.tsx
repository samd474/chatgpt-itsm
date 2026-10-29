import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiErrorMessage } from "../../api/client";
import { getArticle, saveArticle, type ArticleInput } from "../../api/solutions";
import { getCategories, getServices } from "../../api/tickets";
import { useAuth } from "../../auth/context";
import { hasRole, isStaff } from "../../auth/roles";
import { Pill } from "../../components/badges";
import { Card, ErrorState, Field, LoadingState, Notice, PageHeader } from "../../components/ui";
import type { Article } from "../../types";
import { formatDate } from "../../utils/format";

const toId = (value: string) => (value === "" ? null : Number(value));

function ArticleEditor({ article, canPublish, onSaved, onCancel }: {
  article: Article | null; canPublish: boolean; onSaved: (a: Article) => void; onCancel: () => void;
}) {
  const [form, setForm] = useState<ArticleInput>(() => ({
    title: article?.title ?? "", summary: article?.summary ?? "", body: article?.body ?? "", keywords: article?.keywords ?? "",
    visibility: article?.visibility ?? "public", status: article?.status ?? "draft",
    category: article?.category ?? null, service: article?.service ?? null,
  }));
  const categories = useQuery({ queryKey: ["lookup", "categories"], queryFn: getCategories });
  const services = useQuery({ queryKey: ["lookup", "services"], queryFn: getServices });
  const save = useMutation({
    // Technicians can't change status, so don't send it and trip the publish check.
    mutationFn: () => saveArticle(article?.id ?? null, canPublish ? form : { ...form, status: undefined }),
    onSuccess: onSaved,
  });
  const set = <K extends keyof ArticleInput>(key: K, value: ArticleInput[K]) => setForm((f) => ({ ...f, [key]: value }));

  return (
    <Card title={article ? "Edit article" : "New article"}>
      <form className="stack" style={{ gap: 12 }} onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        <Field label="Title"><input className="input" required value={form.title} onChange={(e) => set("title", e.target.value)} /></Field>
        <Field label="Summary" hint="One line shown in search results.">
          <input className="input" value={form.summary} onChange={(e) => set("summary", e.target.value)} />
        </Field>
        <Field label="Solution" hint="Plain text; line breaks are kept.">
          <textarea className="textarea" required rows={12} value={form.body} onChange={(e) => set("body", e.target.value)} />
        </Field>
        <Field label="Keywords" hint="Extra search terms, such as error messages or product names.">
          <input className="input" value={form.keywords} onChange={(e) => set("keywords", e.target.value)} />
        </Field>
        <div className="grid-2">
          <Field label="Category">
            <select className="select" value={form.category ?? ""} onChange={(e) => set("category", toId(e.target.value))}>
              <option value="">None</option>{categories.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Service">
            <select className="select" value={form.service ?? ""} onChange={(e) => set("service", toId(e.target.value))}>
              <option value="">None</option>{services.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="Who can read it">
            <select className="select" value={form.visibility} onChange={(e) => set("visibility", e.target.value as Article["visibility"])}>
              <option value="public">Everyone (once published)</option><option value="internal">Staff only</option>
            </select>
          </Field>
          {canPublish ? (
            <Field label="Status">
              <select className="select" value={form.status} onChange={(e) => set("status", e.target.value as Article["status"])}>
                <option value="draft">Draft</option><option value="published">Published</option><option value="retired">Retired</option>
              </select>
            </Field>
          ) : <Field label="Status"><p className="muted">Draft. A manager publishes it.</p></Field>}
        </div>
        {save.isError && <Notice tone="error">{apiErrorMessage(save.error)}</Notice>}
        <div className="row">
          <span className="spacer" />
          <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
          <button className="btn btn-primary" disabled={save.isPending}>Save</button>
        </div>
      </form>
    </Card>
  );
}

export function ArticlePage() {
  const { id = "" } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canPublish = hasRole(user, "Manager", "Administrator");
  const [editing, setEditing] = useState(isNew);
  const query = useQuery({ queryKey: ["article", id], queryFn: () => getArticle(id), enabled: !isNew });

  const onSaved = (saved: Article) => {
    queryClient.setQueryData(["article", String(saved.id)], saved);
    void queryClient.invalidateQueries({ queryKey: ["articles"] });
    setEditing(false);
    if (isNew) navigate(`/knowledge/${saved.id}`, { replace: true });
  };

  if (isNew) {
    return <><PageHeader title="New article" /><ArticleEditor article={null} canPublish={canPublish} onSaved={onSaved} onCancel={() => navigate("/knowledge")} /></>;
  }
  if (query.isPending) return <LoadingState />;
  if (query.isError) return <ErrorState message={apiErrorMessage(query.error)} />;
  const a = query.data;
  // Technicians edit drafts; published and retired articles are for managers (the API enforces the same).
  const canEdit = canPublish || (isStaff(user) && !hasRole(user, "Auditor") && a.status === "draft");

  return (
    <>
      <PageHeader eyebrow={a.number} title={a.title} description={a.summary || undefined}
        actions={canEdit && !editing && <button className="btn btn-secondary" onClick={() => setEditing(true)}><Pencil />Edit</button>} />
      {editing ? <ArticleEditor article={a} canPublish={canPublish} onSaved={onSaved} onCancel={() => setEditing(false)} /> : (
        <div className="grid-main">
          <Card><p className="pre-wrap">{a.body}</p></Card>
          <Card title="Details">
            <dl className="props">
              {isStaff(user) && <><dt>Status</dt><dd><Pill value={a.status} /></dd><dt>Readers</dt><dd><Pill value={a.visibility} /></dd></>}
              <dt>Category</dt><dd>{a.category_name || "—"}</dd>
              <dt>Service</dt><dd>{a.service_name || "—"}</dd>
              <dt>Author</dt><dd>{a.author_name}</dd>
              <dt>Updated</dt><dd>{formatDate(a.updated_at)}</dd>
            </dl>
          </Card>
        </div>
      )}
    </>
  );
}
