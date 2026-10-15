// What the frontend expects from the Django API. These types are not security
// controls; Django serializers remain the authoritative schema.

export type User = {
  id: number;
  username: string;
  name: string;
  groups: string[];
  is_superuser: boolean;
};

export type TicketStatus =
  | "new"
  | "assigned"
  | "in_progress"
  | "pending_user_response"
  | "resolved"
  | "closed"
  | "cancelled";

export type SlaSummary = {
  policy: string;
  response_due_at: string;
  resolution_due_at: string;
  response_breached: boolean;
  resolution_breached: boolean;
  paused: boolean;
  warning: boolean;
};

export type Ticket = {
  public_id: string;
  request_number: string | null;
  request_type: "incident" | "request";
  subject: string;
  description: string;
  requester: number;
  requester_name: string | null;
  technician: number | null;
  technician_name: string | null;
  assignment_group: number | null;
  assignment_group_name: string | null;
  category: number | null;
  category_name: string | null;
  service: number | null;
  service_name: string | null;
  impact: number;
  urgency: number;
  priority: number;
  status: TicketStatus;
  request_payload: Record<string, unknown>;
  resolution_code: string;
  resolution_body: string;
  first_response_time: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
  sla: SlaSummary | null;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type TicketComment = {
  id: number;
  author: number;
  author_name?: string;
  body: string;
  visibility: "public" | "private";
  created_at: string;
};

export type Attachment = {
  id: number;
  original_name: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  uploaded_by: number;
  uploaded_by_name: string | null;
  created_at: string;
};

export type Approval = {
  id: number;
  help_request: string;
  request_number: string | null;
  subject: string;
  approver: number;
  approver_name: string | null;
  state: "pending" | "approved" | "rejected" | "cancelled";
  comment: string;
  decided_at: string | null;
  created_at: string;
};

export type CatalogField = {
  key: string;
  label: string;
  type: "text" | "textarea" | "date" | "boolean" | "select";
  required?: boolean;
  options?: string[];
  show_when?: { field: string; equals: unknown };
};

export type CatalogItem = {
  id: number;
  name: string;
  slug: string;
  short_description: string;
  description: string;
  form_schema: CatalogField[];
  requires_approval: boolean;
  active: boolean;
};

export type AuditEvent = {
  id: number;
  event_type: string;
  object_type: string;
  object_id: string;
  actor: number | null;
  actor_name: string | null;
  request_id: string;
  source_ip: string | null;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type Lookup = { id: number; name: string };
export type UserLookup = { id: number; username: string; name: string };

export type ImportJob = {
  id: number;
  kind: "categories" | "services";
  state: "validated" | "applied" | "failed";
  original_name: string;
  preview: {
    valid: Record<string, unknown>[];
    errors: { row: number; error: string }[];
    warnings: { row: number; warning: string }[];
  };
  result: { created?: number; updated?: number; skipped_errors?: number };
  created_at: string;
  applied_at: string | null;
};
