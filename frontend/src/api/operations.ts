import { api } from "./client";
import type { AuditEvent, ImportJob, Paginated } from "../types";

export type ServiceDeskReport = {
  open_tickets: number;
  unassigned: number;
  sla_at_risk: number;
  sla_breached: number;
  by_priority: Record<string, number>;
  by_status: Record<string, number>;
  backlog_by_age: Record<string, number>;
};

export async function getServiceDeskReport(): Promise<ServiceDeskReport> {
  const response = await api.get<ServiceDeskReport>("/reports/service-desk/");
  return response.data;
}

export type AuditParams = { page?: number; activity_type?: string; object_id?: string; request_id?: string };

export async function getAuditEvents(params: AuditParams = {}): Promise<Paginated<AuditEvent>> {
  const response = await api.get<Paginated<AuditEvent>>("/audit/", { params });
  return response.data;
}

export async function uploadImport(kind: ImportJob["kind"], file: File): Promise<ImportJob> {
  const formData = new FormData();
  formData.append("kind", kind);
  formData.append("file", file);
  return (await api.post<ImportJob>("/imports/", formData)).data;
}

export async function confirmImport(id: number): Promise<ImportJob> {
  return (await api.post<ImportJob>(`/imports/${id}/confirm/`)).data;
}
