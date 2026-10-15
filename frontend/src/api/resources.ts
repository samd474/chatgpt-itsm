import { api } from "./client";
import type { Paginated } from "../types";

// Generic REST helpers for list/create/update/delete screens.
export type ListResult<T> = { items: T[]; count: number; next: string | null; previous: string | null };

export async function listResource<T>(endpoint: string, params: Record<string, unknown> = {}): Promise<ListResult<T>> {
  const response = await api.get<Paginated<T> | T[]>(endpoint, { params });
  if (Array.isArray(response.data)) {
    return { items: response.data, count: response.data.length, next: null, previous: null };
  }
  return { items: response.data.results, count: response.data.count, next: response.data.next, previous: response.data.previous };
}

export async function listAll<T>(endpoint: string, params: Record<string, unknown> = {}): Promise<T[]> {
  return (await listResource<T>(endpoint, params)).items;
}

export async function getResource<T>(endpoint: string, id: number | string): Promise<T> {
  return (await api.get<T>(`${endpoint}${id}/`)).data;
}

export async function createResource<T>(endpoint: string, data: Record<string, unknown>): Promise<T> {
  return (await api.post<T>(endpoint, data)).data;
}

export async function updateResource<T>(endpoint: string, id: number | string, data: Record<string, unknown>): Promise<T> {
  return (await api.patch<T>(`${endpoint}${id}/`, data)).data;
}

export async function deleteResource(endpoint: string, id: number | string): Promise<void> {
  await api.delete(`${endpoint}${id}/`);
}

export async function postAction<T>(url: string, data: Record<string, unknown> = {}): Promise<T> {
  return (await api.post<T>(url, data)).data;
}

export async function getAction<T>(url: string, params: Record<string, unknown> = {}): Promise<T> {
  return (await api.get<T>(url, { params })).data;
}

export const ENDPOINTS = {
  users: "/admin/users/",
  roles: "/admin/roles/",
  supportGroups: "/support-groups/",
  categories: "/categories/",
  services: "/services/",
  templates: "/ticket-templates/",
  queues: "/queues/",
  customFields: "/custom-fields/",
  catalogItems: "/admin/catalog-items/",
  slaPolicies: "/admin/sla-policies/",
  calendars: "/admin/business-calendars/",
  notificationTemplates: "/admin/notification-templates/",
  assets: "/assets/items/",
  assetTypes: "/assets/types/",
  locations: "/assets/locations/",
  vendors: "/contracts/vendors/",
  contracts: "/contracts/items/",
  projects: "/projects/items/",
  milestones: "/projects/milestones/",
  projectTasks: "/projects/tasks/",
  changes: "/changes/items/",
  changeApprovals: "/changes/approvals/",
  technicians: "/technicians/",
  people: "/people/",
  exports: "/exports/",
} as const;
