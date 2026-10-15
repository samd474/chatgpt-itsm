import { api } from "./client";
import type { Approval, Attachment, Lookup, Paginated, Ticket, TicketComment, TicketStatus, UserLookup } from "../types";

export type TicketListParams = {
  page?: number;
  search?: string;
  status?: string;
  priority?: string;
  assignment_group?: string;
  technician?: string;
  category?: string;
  ordering?: string;
};

export type CreateTicketInput = {
  request_type: "incident" | "request";
  subject: string;
  description: string;
  impact: number;
  urgency: number;
  category?: number | null;
  service?: number | null;
};

export type TicketUpdateInput = Partial<
  Pick<Ticket, "subject" | "description" | "technician" | "assignment_group" | "category" | "service" | "impact" | "urgency">
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

export function exportUrl(params: TicketListParams): string {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => [k, String(v)]),
  );
  return `/api${base}/export/?${query}`;
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
