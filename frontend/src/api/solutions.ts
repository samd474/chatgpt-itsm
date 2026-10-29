import { api } from "./client";
import { listResource } from "./resources";
import type { Article } from "../types";

const BASE = "/solutions/articles/";

export type ArticleInput = Partial<Pick<Article, "title" | "summary" | "body" | "keywords" | "status" | "visibility" | "category" | "service">>;

export function listArticles(params: { page?: number; search?: string; status?: string }) {
  return listResource<Article>(BASE, params);
}

export async function getArticle(id: number | string): Promise<Article> {
  return (await api.get<Article>(`${BASE}${id}/`)).data;
}

export async function saveArticle(id: number | null, input: ArticleInput): Promise<Article> {
  return id === null ? (await api.post<Article>(BASE, input)).data : (await api.patch<Article>(`${BASE}${id}/`, input)).data;
}

export async function getTicketArticles(publicId: string): Promise<Article[]> {
  return (await api.get<Article[]>(`/help-requests/${publicId}/articles/`)).data;
}

export async function linkTicketArticle(publicId: string, article: number, unlink = false): Promise<Article[]> {
  return (await api.post<Article[]>(`/help-requests/${publicId}/articles/`, { article, unlink })).data;
}
