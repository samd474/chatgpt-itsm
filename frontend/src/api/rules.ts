import { api } from "./client";
import type { RuleActions, RuleConditions, RulePreview, TicketRule } from "../types";

const BASE = "/rules/ticket-rules/";

export type RuleInput = Pick<TicketRule, "name" | "description" | "position" | "active" | "stop_processing" | "runs_on" | "conditions" | "actions">;

export async function listRules(): Promise<TicketRule[]> {
  return (await api.get<TicketRule[]>(BASE)).data;
}

export async function saveRule(id: number | null, input: RuleInput): Promise<TicketRule> {
  return id === null ? (await api.post<TicketRule>(BASE, input)).data : (await api.patch<TicketRule>(`${BASE}${id}/`, input)).data;
}

export async function deleteRule(id: number): Promise<void> {
  await api.delete(`${BASE}${id}/`);
}

/** Dry run against recent tickets; changes nothing. */
export async function previewRule(conditions: RuleConditions, actions: RuleActions): Promise<RulePreview> {
  return (await api.post<RulePreview>(`${BASE}preview/`, { conditions, actions })).data;
}
