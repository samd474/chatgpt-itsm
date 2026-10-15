import { api } from "./client";
import type {
  Approval,
  Attachment,
  CustomFieldDef,
  ExportJob,
  FulfillmentTask,
  Lookup,
  Paginated,
  Queue,
  Ticket,
  TicketComment,
  TicketStatus,
  TicketTemplate,
  UserLookup,
} from "../types";

export type TicketListParams = {
  page?: number;
  search?: string;
  status?: string;
  priority?: string;
  assignment_group?: string;
  technician?: string;
  category?: string;
  ordering?: string;
  open?: boolean;
};

export type CreateTicketInput = {
  request_type: "incident" | "request";
  subject: string;
  description: string;
  impact: number;
  urgency: number;
  category?: number | null;
  service?: number | null;
  template?: number | null;
  custom_fields?: Record<string, unknown>;
};

export type TicketUpdateInput = Partial<
  Pick<Ticket, "subject" | "description" | "technician" | "assignment_group" | "category" | "service" | "impact" | "urgency" | "custom_fields">
>;

const base = "/help-requests";

export async function getTickets(params: TicketListParams = {}): Promise<Paginated<Ticket>> {
  const response = await api.get<Paginated<Ticket>>(`${base}/`, { params });
  return response.data;
}

export async function getTicket(publicId: string): Promise<Ticket> {
  const response = await api.get<Ticket>(`${base}/${publicId}/`);
  return response.data;
}

export async function createTicket(input: CreateTicketInput): Promise<Ticket> {
  const response = await api.post<Ticket>(`${base}/`, input);
  return response.data;
}

export async function patchTicket(publicId: string, input: TicketUpdateInput): Promise<Ticket> {
  const response = await api.patch<Ticket>(`${base}/${publicId}/`, input);
  return response.data;
}

export async function getComments(publicId: string): Promise<TicketComment[]> {
  const response = await api.get<TicketComment[]>(`${base}/${publicId}/comments/`);
  return response.data;
}

export async function addComment(
  publicId: string,
  input: { body: string; visibility: "public" | "private" },
): Promise<TicketComment> {
  const response = await api.post<TicketComment>(`${base}/${publicId}/comments/`, input);
  return response.data;
}

export async function transitionTicket(
  publicId: string,
  input: {
    status: TicketStatus;
    reason?: string;
    resolution_code?: string;
    resolution_body?: string;
  },
): Promise<Ticket> {
  const response = await api.post<Ticket>(`${base}/${publicId}/transition/`, input);
  return response.data;
}

export async function getAttachments(publicId: string): Promise<Attachment[]> {
  const response = await api.get<Attachment[]>(`${base}/${publicId}/attachments/`);
  return response.data;
}

export async function uploadAttachment(publicId: string, file: File): Promise<Attachment> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post<Attachment>(`${base}/${publicId}/attachments/`, formData);
  return response.data;
}

export function attachmentDownloadUrl(publicId: string, attachmentId: number): string {
  return `/api${base}/${publicId}/attachments/${attachmentId}/download/`;
}


export async function getTicketApprovals(publicId: string): Promise<Approval[]> {
  const response = await api.get<Approval[]>(`${base}/${publicId}/approvals/`);
  return response.data;
}

export async function getMyApprovals(state?: string): Promise<Paginated<Approval>> {
  const response = await api.get<Paginated<Approval>>("/approvals/", { params: { state } });
  return response.data;
}

export async function decideApproval(id: number, state: "approved" | "rejected", comment: string): Promise<Approval> {
  const response = await api.post<Approval>(`/approvals/${id}/decide/`, { state, comment });
  return response.data;
}

export async function getSupportGroups(): Promise<Lookup[]> {
  return (await api.get<Lookup[]>("/support-groups/")).data;
}

export async function getCategories(): Promise<Lookup[]> {
  return (await api.get<Lookup[]>("/categories/")).data;
}

export async function getServices(): Promise<Lookup[]> {
  return (await api.get<Lookup[]>("/services/")).data;
}

export async function getTechnicians(group?: number | null): Promise<UserLookup[]> {
  const params = group ? { support_groups: group } : {};
  return (await api.get<UserLookup[]>("/technicians/", { params })).data;
}

export async function getTicketTasks(publicId: string): Promise<FulfillmentTask[]> {
  return (await api.get<FulfillmentTask[]>(`${base}/${publicId}/tasks/`)).data;
}

export async function addTicketTask(publicId: string, input: { title: string; description?: string; assignee?: number | null }): Promise<FulfillmentTask> {
  return (await api.post<FulfillmentTask>(`${base}/${publicId}/tasks/`, input)).data;
}

export async function updateTask(id: number, input: Partial<Pick<FulfillmentTask, "status" | "assignee" | "title">>): Promise<FulfillmentTask> {
  return (await api.patch<FulfillmentTask>(`/tasks/${id}/`, input)).data;
}

export async function getTemplates(): Promise<TicketTemplate[]> {
  return (await api.get<TicketTemplate[]>("/ticket-templates/")).data;
}

export async function getQueues(): Promise<Queue[]> {
  return (await api.get<Queue[]>("/queues/")).data;
}

export async function getQueueTickets(id: number, params: { page?: number; search?: string }): Promise<Paginated<Ticket>> {
  return (await api.get<Paginated<Ticket>>(`/queues/${id}/tickets/`, { params })).data;
}

export async function getCustomFields(entity: string): Promise<CustomFieldDef[]> {
  return (await api.get<CustomFieldDef[]>("/custom-fields/", { params: { entity, active: true } })).data;
}

/** Small exports download immediately; large ones are queued (202) and appear under Reports > Exports. */
export async function requestExport(params: TicketListParams): Promise<{ queued: boolean; rows?: number }> {
  const response = await api.get(`${base}/export/`, { params: { ...params, page: undefined }, responseType: "blob" });
  if (response.status === 202) {
    const body = JSON.parse(await (response.data as Blob).text()) as { row_count: number };
    return { queued: true, rows: body.row_count };
  }
  const url = URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "help-requests.csv";
  link.click();
  URL.revokeObjectURL(url);
  return { queued: false };
}

export async function getExports(): Promise<ExportJob[]> {
  return (await api.get<ExportJob[]>("/exports/")).data;
}

export function exportDownloadUrl(id: string) {
  return `/api/exports/${id}/download/`;
}
