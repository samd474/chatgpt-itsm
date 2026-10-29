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
  custom_fields: Record<string, unknown>;
  open_tasks: number;
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

export type CustomFieldDef = {
  id: number;
  entity: "ticket" | "asset" | "change" | "project" | "contract";
  key: string;
  label: string;
  field_type: "text" | "textarea" | "date" | "boolean" | "select";
  options: string[];
  required: boolean;
  visible_to_requester: boolean;
  position: number;
  active: boolean;
};

export type TicketTemplate = {
  id: number;
  name: string;
  help_text: string;
  request_type: "incident" | "request";
  subject: string;
  description: string;
  category: number | null;
  service: number | null;
  assignment_group: number | null;
  impact: number;
  urgency: number;
  available_to_requesters: boolean;
  active: boolean;
};

export type Queue = { id: number; name: string; description: string; filters: Record<string, unknown>; ordering: string; visible_to_roles: string[]; position: number; active: boolean };

export type FulfillmentTask = {
  id: number;
  title: string;
  description: string;
  assignment_group: number | null;
  assignment_group_name: string | null;
  assignee: number | null;
  assignee_name: string | null;
  status: "open" | "in_progress" | "done" | "cancelled";
  position: number;
  created_at: string;
  completed_at: string | null;
};

export type ExportJob = {
  public_id: string;
  kind: string;
  params: Record<string, string>;
  state: "queued" | "running" | "done" | "failed";
  row_count: number;
  error: string;
  created_at: string;
  finished_at: string | null;
  expires_at: string | null;
};

export type Asset = {
  id: number;
  asset_tag: string;
  name: string;
  asset_type: number;
  asset_type_name: string;
  status: string;
  serial_number: string;
  manufacturer: string;
  model: string;
  location: number | null;
  location_name: string | null;
  owner?: number | null;
  owner_name?: string | null;
  assigned_to?: number | null;
  assigned_to_name?: string | null;
  support_group?: number | null;
  purchase_date?: string | null;
  purchase_cost?: string | null;
  warranty_expires: string | null;
  notes?: string;
  custom_fields?: Record<string, unknown>;
  linked_tickets?: { public_id: string; request_number: string | null; subject: string; status: TicketStatus }[];
  created_at?: string;
  updated_at?: string;
};

export type AssetRelationship = { id: number; source: number; source_label: string; target: number; target_label: string; kind: string };

export type Contract = {
  id: number;
  number: string;
  name: string;
  vendor: number;
  vendor_name: string;
  contract_type: string;
  status: string;
  start_date: string;
  end_date: string;
  days_remaining: number;
  value?: string | null;
  currency?: string;
  billing_frequency?: string;
  auto_renew: boolean;
  renewal_notice_days: number;
  owner: number | null;
  owner_name: string | null;
  notes: string;
  custom_fields: Record<string, unknown>;
  assets: number[];
  services: number[];
};

export type ProjectMember = { user: number; name: string; role: "contributor" | "viewer" };

export type Project = {
  id: number;
  key: string;
  name: string;
  description: string;
  status: string;
  manager: number;
  manager_name: string;
  members: ProjectMember[];
  start_date: string | null;
  target_date: string | null;
  completed_at: string | null;
  budget: string | null;
  custom_fields: Record<string, unknown>;
  progress: { total: number; done: number; percent: number };
};

export type Milestone = { id: number; project: number; name: string; due_date: string | null; completed: boolean };

export type ProjectTask = {
  id: number;
  project: number;
  number: string;
  title: string;
  description: string;
  status: "todo" | "in_progress" | "blocked" | "done";
  priority: number;
  assignee: number | null;
  assignee_name: string | null;
  milestone: number | null;
  depends_on: number[];
  due_date: string | null;
  estimate_hours: string | null;
  position: number;
};

export type ChangeApproval = {
  id: number;
  change: number;
  change_number: string;
  change_title: string;
  approver: number;
  approver_name: string | null;
  state: "pending" | "approved" | "rejected" | "cancelled";
  comment: string;
  decided_at: string | null;
  created_at: string;
};

export type ChangeStatus = "draft" | "awaiting_approval" | "approved" | "scheduled" | "implementing" | "review" | "closed" | "rejected" | "cancelled";

export type Change = {
  id: number;
  number: string;
  title: string;
  description: string;
  justification: string;
  change_type: "standard" | "normal" | "emergency";
  status: ChangeStatus;
  risk: "low" | "medium" | "high";
  impact: number;
  service: number | null;
  assignment_group: number | null;
  requested_by: number;
  requested_by_name: string | null;
  implementer: number | null;
  implementer_name: string | null;
  implementation_plan: string;
  backout_plan: string;
  test_plan: string;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  outcome: string;
  closure_notes: string;
  custom_fields: Record<string, unknown>;
  assets: number[];
  help_requests: string[];
  approvals: ChangeApproval[];
  conflict_count: number;
  created_at: string;
  updated_at: string;
};

export type ArticleStatus = "draft" | "published" | "retired";

export type Article = {
  id: number;
  number: string | null;
  title: string;
  summary: string;
  body: string;
  keywords: string;
  status: ArticleStatus;
  visibility: "public" | "internal";
  category: number | null;
  category_name: string | null;
  service: number | null;
  service_name: string | null;
  author: number;
  author_name: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};
