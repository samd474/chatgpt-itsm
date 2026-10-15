import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Paperclip, Upload } from "lucide-react";
import { useRef } from "react";
import { attachmentDownloadUrl, getAttachments, uploadAttachment } from "../api/tickets";
import { apiFieldErrors } from "./form";
import { Card, Notice } from "./ui";
import { formatBytes, relativeTime } from "../utils/format";

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
    <Card title="Attachments" actions={canUpload && (
      <label className="btn btn-secondary btn-sm"><Upload />{upload.isPending ? "Scanning…" : "Upload"}
        <input ref={input} type="file" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate(f); }} disabled={upload.isPending} />
      </label>
    )}>
      {query.data?.length === 0 && <p className="subtle">No files attached.</p>}
      <div className="list">
        {query.data?.map((a) => (
          <div className="list-item" key={a.id}>
            <Paperclip />
            {/* Downloads go through Django so authorization is checked every time. */}
            <a href={attachmentDownloadUrl(publicId, a.id)}>{a.original_name}</a>
            <span className="spacer" />
            <span className="subtle">{formatBytes(a.size_bytes)} · {relativeTime(a.created_at)}</span>
          </div>
        ))}
      </div>
      {upload.isError && <div style={{ marginTop: 10 }}><Notice tone="error">{apiFieldErrors(upload.error).fields.file ?? apiFieldErrors(upload.error).general}</Notice></div>}
    </Card>
  );
}
