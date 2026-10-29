import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Link2, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { apiErrorMessage } from "../api/client";
import { getTicketArticles, linkTicketArticle, listArticles } from "../api/solutions";
import type { Article } from "../types";
import { Pill } from "./badges";
import { Card, Notice } from "./ui";

/** Knowledge-base articles linked to a ticket. Staff link, unlink and reuse them; requesters only read. */
export function ArticlesPanel({ publicId, staff, onUse }: { publicId: string; staff: boolean; onUse?: (article: Article) => void }) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [term, setTerm] = useState("");
  const linked = useQuery({ queryKey: ["ticket-articles", publicId], queryFn: () => getTicketArticles(publicId) });
  const results = useQuery({
    queryKey: ["articles", "link-search", term],
    enabled: staff && term.length > 0,
    queryFn: () => listArticles({ search: term, status: "published" }),
  });
  const link = useMutation({
    mutationFn: ({ id, unlink }: { id: number; unlink: boolean }) => linkTicketArticle(publicId, id, unlink),
    onSuccess: (rows) => queryClient.setQueryData(["ticket-articles", publicId], rows),
  });

  const rows = linked.data ?? [];
  if (!staff && rows.length === 0) return null;
  const linkedIds = new Set(rows.map((a) => a.id));
  const candidates = (results.data?.items ?? []).filter((a) => !linkedIds.has(a.id));

  return (
    <Card title={staff ? "Solutions" : "Helpful articles"}>
      <div className="list">
        {rows.map((a) => (
          <div className="list-item" key={a.id}>
            <BookOpen />
            <Link to={`/knowledge/${a.id}`}>{a.title}</Link>
            {staff && a.status !== "published" && <Pill value={a.status} />}
            <span className="spacer" />
            {staff && onUse && a.visibility === "public" && <button className="btn btn-ghost btn-sm" onClick={() => onUse(a)}>Use as resolution</button>}
            {staff && (
              <button className="btn btn-ghost btn-icon btn-sm" aria-label={`Unlink ${a.title}`} disabled={link.isPending}
                onClick={() => link.mutate({ id: a.id, unlink: true })}><X /></button>
            )}
          </div>
        ))}
        {staff && rows.length === 0 && <p className="muted">No articles linked yet.</p>}
      </div>
      {staff && (
        <>
          <form className="row" style={{ marginTop: 8 }} onSubmit={(e) => { e.preventDefault(); setTerm(search.trim()); }}>
            <input className="input" style={{ flex: 1 }} value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search published articles…" aria-label="Search published articles" />
            <button className="btn btn-secondary" disabled={!search.trim()}>Search</button>
          </form>
          {term && results.data && (
            <div className="list" style={{ marginTop: 8 }}>
              {candidates.length === 0 && <p className="muted">No other published articles match.</p>}
              {candidates.map((a) => (
                <div className="list-item" key={a.id}>
                  <span>{a.title}</span><span className="spacer" />
                  <button className="btn btn-secondary btn-sm" disabled={link.isPending} onClick={() => link.mutate({ id: a.id, unlink: false })}>
                    <Link2 />Link
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}
      {(link.isError || linked.isError) && <div style={{ marginTop: 8 }}><Notice tone="error">{apiErrorMessage(link.error ?? linked.error)}</Notice></div>}
    </Card>
  );
}
