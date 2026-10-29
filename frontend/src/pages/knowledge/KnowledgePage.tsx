import { useQuery } from "@tanstack/react-query";
import { BookOpen, Plus } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiErrorMessage } from "../../api/client";
import { listArticles } from "../../api/solutions";
import { useAuth } from "../../auth/context";
import { isStaff } from "../../auth/roles";
import { Pill } from "../../components/badges";
import { EmptyState, ErrorState, LoadingState, PageHeader, Pager, SearchInput } from "../../components/ui";

export function KnowledgePage() {
  const { user } = useAuth();
  const staff = isStaff(user);
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState(staff ? "" : "published");
  const [ordering, setOrdering] = useState("");
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["articles", search, status, ordering, page],
    queryFn: () => listArticles({ page, search: search || undefined, status: status || undefined, ordering: ordering || undefined }),
  });

  return (
    <>
      <PageHeader title="Knowledge base" description="Answers to common problems, written by the service desk."
        actions={staff && <button className="btn btn-primary" onClick={() => navigate("/knowledge/new")}><Plus />New article</button>} />
      <div className="toolbar">
        <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search articles, e.g. an error message" />
        {staff && (
          <select className="select" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} aria-label="Status">
            <option value="">Any status</option><option value="published">Published</option><option value="draft">Draft</option><option value="retired">Retired</option>
          </select>
        )}
        {staff && (
          <select className="select" value={ordering} onChange={(e) => { setOrdering(e.target.value); setPage(1); }} aria-label="Sort">
            <option value="">Recently updated</option><option value="-not_helpful_count">Least helpful first</option><option value="-helpful_count">Most helpful first</option>
          </select>
        )}
      </div>
      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState message={apiErrorMessage(query.error)} />}
      {query.data && query.data.items.length === 0 && (
        <EmptyState title={search ? "No matching articles" : "No articles yet"}
          message={search ? "Try different words, or report an issue and we'll help." : undefined} />
      )}
      <div className="tiles">
        {query.data?.items.map((a) => (
          <Link className="tile" key={a.id} to={`/knowledge/${a.id}`}>
            <div className="row">
              <span className="tile-icon"><BookOpen /></span><span className="subtle">{a.number}</span><span className="spacer" />
              {staff && <>{a.status !== "published" && <Pill value={a.status} />}{a.visibility === "internal" && <Pill value="internal" />}</>}
            </div>
            <h3>{a.title}</h3>
            {a.summary && <p>{a.summary}</p>}
            {staff && a.helpful_count != null && (a.helpful_count > 0 || (a.not_helpful_count ?? 0) > 0) && (
              <span className="subtle">{a.helpful_count} helpful · {a.not_helpful_count} not helpful</span>
            )}
          </Link>
        ))}
      </div>
      {query.data && (query.data.next || query.data.previous) && (
        <Pager count={query.data.count} page={page} hasNext={!!query.data.next} hasPrev={!!query.data.previous} onPage={setPage} noun="articles" />
      )}
    </>
  );
}
