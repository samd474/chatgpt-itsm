import { api } from "./client";
import type { CatalogItem, Paginated, Ticket } from "../types";

export async function getCatalogItems(): Promise<CatalogItem[]> {
  const response = await api.get<Paginated<CatalogItem> | CatalogItem[]>("/catalog/items/");
  return Array.isArray(response.data) ? response.data : response.data.results;
}

export async function getCatalogItem(slug: string): Promise<CatalogItem> {
  const response = await api.get<CatalogItem>(`/catalog/items/${slug}/`);
  return response.data;
}

export async function submitCatalogItem(slug: string, requestPayload: Record<string, unknown>): Promise<Ticket> {
  const response = await api.post<Ticket>(`/catalog/items/${slug}/submit/`, {
    request_payload: requestPayload,
  });
  return response.data;
}
