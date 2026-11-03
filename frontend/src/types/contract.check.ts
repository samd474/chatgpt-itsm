/**
 * Compile-time contract between the hand-written frontend types and the backend API.
 *
 * `src/api/schema.d.ts` is generated from the backend's OpenAPI schema (`npm run api:types`).
 * Each line below asserts that what the API returns is assignable to the type the UI uses, so
 * `tsc` fails if the backend drops, renames or retypes a field the UI reads. Nothing here is
 * bundled; the file only contains types.
 */
import type { components } from "../api/schema";
import type { ServiceDeskReport } from "../api/operations";
import type * as UI from "./index";

type Api = components["schemas"];
/** Compiles only when `Returned` (the API's response type) satisfies `Expected` (the UI's type). */
type Satisfies<Returned extends Expected, Expected> = Returned;
/**
 * JSON-blob fields (filters, audit before/after, rule conditions, ...) are `unknown` in the API
 * schema, since their shape lives in validation code rather than the serializer. Their contents
 * aren't checked, but the field must still exist in the API.
 */
type Json<T, Keys extends keyof T> = Omit<T, Keys> & { [K in Keys]: unknown };

export type Contract = [
  Satisfies<Api["CurrentUser"], UI.User>,
  Satisfies<Api["HelpRequestsRead"], Json<UI.Ticket, "request_payload">>,
  Satisfies<Api["SlaSummary"], UI.SlaSummary>,
  Satisfies<Api["Comment"], UI.TicketComment>,
  Satisfies<Api["Attachment"], UI.Attachment>,
  Satisfies<Api["Approval"], UI.Approval>,
  Satisfies<Api["CatalogItem"], Json<UI.CatalogItem, "form_schema">>,
  Satisfies<Api["AuditEvent"], Json<UI.AuditEvent, "before" | "after" | "metadata">>,
  Satisfies<Api["UserLookup"], UI.UserLookup>,
  Satisfies<Api["Category"], UI.Lookup>,
  Satisfies<Api["Service"], UI.Lookup>,
  Satisfies<Api["SupportGroup"], UI.Lookup>,
  Satisfies<Api["ImportJob"], Json<UI.ImportJob, "preview" | "result">>,
  Satisfies<Api["CustomFieldDefinition"], Json<UI.CustomFieldDef, "options">>,
  Satisfies<Api["TicketTemplate"], UI.TicketTemplate>,
  Satisfies<Api["Queue"], Json<UI.Queue, "filters" | "visible_to_roles">>,
  Satisfies<Api["FulfillmentTask"], UI.FulfillmentTask>,
  Satisfies<Api["ExportJob"], Json<UI.ExportJob, "params">>,
  Satisfies<Api["Asset"], UI.Asset>,
  Satisfies<Api["AssetRelationship"], UI.AssetRelationship>,
  Satisfies<Api["Contract"], UI.Contract>,
  Satisfies<Api["ProjectMember"], UI.ProjectMember>,
  Satisfies<Api["Project"], UI.Project>,
  Satisfies<Api["Milestone"], UI.Milestone>,
  Satisfies<Api["ProjectTask"], UI.ProjectTask>,
  Satisfies<Api["ChangeApproval"], UI.ChangeApproval>,
  Satisfies<Api["ChangeRequest"], UI.Change>,
  Satisfies<Api["Article"], UI.Article>,
  Satisfies<Api["TicketRule"], Json<UI.TicketRule, "conditions" | "actions">>,
  Satisfies<Api["RulePreview"], UI.RulePreview>,
  Satisfies<Api["ServiceDeskReport"], ServiceDeskReport>,
];
