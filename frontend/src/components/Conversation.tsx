import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Lock } from "lucide-react";
import { useState } from "react";
import { addComment, getComments } from "../api/tickets";
import { apiErrorMessage } from "../api/client";
import { Avatar, Badge, Card, ErrorState, Notice } from "./ui";
import { relativeTime } from "../utils/format";

/** Ticket conversation. Staff get an explicit public/private toggle; requesters only post public replies
 *  (and the API never sends them private notes). */
export function Conversation({ publicId, staff, onPosted }: { publicId: string; staff: boolean; onPosted?: () => void }) {
  const queryClient = useQueryClient();
  const [body, setBody] = useState("");
  const [mode, setMode] = useState<"public" | "private">(staff ? "private" : "public");
  const comments = useQuery({ queryKey: ["ticket-comments", publicId], queryFn: () => getComments(publicId) });
  const post = useMutation({
    mutationFn: () => addComment(publicId, { body, visibility: mode }),
    onSuccess: async () => {
      setBody("");
      await queryClient.invalidateQueries({ queryKey: ["ticket-comments", publicId] });
      onPosted?.();
    },
  });

  return (
    <Card title="Activity">
      {comments.isError && <ErrorState message={apiErrorMessage(comments.error)} />}
      {comments.data?.length === 0 && <p className="subtle">No replies yet.</p>}
      <div className="timeline">
        {comments.data?.map((c) => (
          <article key={c.id} className={`entry${c.visibility === "private" ? " private" : ""}`}>
            <Avatar name={c.author_name} />
            <div>
              <div className="entry-head">
                <strong>{c.author_name}</strong>
                {c.visibility === "private" && <Badge tone="amber"><Lock size={11} />Internal note</Badge>}
                <span className="subtle">{relativeTime(c.created_at)}</span>
              </div>
              <div className="entry-body">{c.body}</div>
            </div>
          </article>
        ))}
      </div>
      <div className={`composer${mode === "public" && staff ? " public" : ""}`}>
        {staff && (
          <div className="row">
            <div className="segmented" role="group" aria-label="Visibility">
              <button type="button" className={mode === "private" ? "on" : ""} onClick={() => setMode("private")}>Internal note</button>
              <button type="button" className={mode === "public" ? "on" : ""} onClick={() => setMode("public")}>Reply to requester</button>
            </div>
            {mode === "public" && <span className="subtle">The requester will see and be emailed this reply.</span>}
          </div>
        )}
        <textarea className="textarea" rows={3} value={body} onChange={(e) => setBody(e.target.value)}
          placeholder={staff ? (mode === "private" ? "Only staff can see this…" : "Write a reply to the requester…") : "Add a reply…"} />
        {post.isError && <Notice tone="error">{apiErrorMessage(post.error)}</Notice>}
        <div className="form-actions">
          <button className="btn btn-primary" disabled={!body.trim() || post.isPending} onClick={() => post.mutate()}>
            {staff && mode === "private" ? "Add note" : "Send reply"}
          </button>
        </div>
      </div>
    </Card>
  );
}
