import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { attachmentDownloadUrl, getAttachments, uploadAttachment } from "../api/tickets";
import { apiErrorMessage } from "../api/client";
import { formatBytes, formatDate } from "../utils/format";

export function AttachmentsPanel({ publicId, canUpload }: { publicId: string; canUpload: boolean }) {
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const query = useQuery({ queryKey: ["attachments", publicId], queryFn: () => getAttachments(publicId) });
  const upload = useMutation({
    mutationFn: (file: File) => uploadAttachment(publicId, file),
    onSuccess: async () => {
      if (input.current) input.current.value = "";
      await queryClient.invalidateQueries({ queryKey: ["attachments", publicId] });
    },
  });

  return (
    <div className="panel">
      <h2>Attachments</h2>
      {query.data?.length === 0 && <p className="muted">No attachments.</p>}
      <ul className="file-list">
        {query.data?.map((a) => (
          <li key={a.id}>
            {/* Downloads go through Django so authorization is checked on every request. */}
            <a href={attachmentDownloadUrl(publicId, a.id)}>{a.original_name}</a>
            <span className="muted"> {formatBytes(a.size_bytes)} · {a.uploaded_by_name} · {formatDate(a.created_at)}</span>
          </li>
        ))}
      </ul>
      {canUpload && (
        <div className="inline-form">
          <input ref={input} type="file" onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate(f); }} disabled={upload.isPending} />
        </div>
      )}
      {upload.isError && <div className="alert alert--error">{apiErrorMessage(upload.error)}</div>}
    </div>
  );
}
