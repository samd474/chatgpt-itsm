import type { Page, Route } from "@playwright/test";
import type { Article, Paginated, Ticket, TicketRule, User } from "../src/types";

// The browser only ever talks to /api; these tests answer it in-process, so they need no backend.

export const ROLE_USERS = {
  requester: { id: 2, username: "rita", name: "Rita Requester", groups: ["Requester"], is_superuser: false },
  technician: { id: 3, username: "tom", name: "Tom Technician", groups: ["Technician"], is_superuser: false },
  auditor: { id: 4, username: "ada", name: "Ada Auditor", groups: ["Auditor"], is_superuser: false },
  admin: { id: 1, username: "root", name: "Root Admin", groups: ["Administrator"], is_superuser: true },
} satisfies Record<string, User>;

export const TICKET: Ticket = {
  public_id: "6f1c2b9e-4d3a-4b5c-9e8f-0a1b2c3d4e5f",
  request_number: "INC-000001",
  request_type: "incident",
  subject: "VPN drops every few minutes",
  description: "Started after the laptop update.",
  requester: 2,
  requester_name: "Rita Requester",
  technician: 3,
  technician_name: "Tom Technician",
  assignment_group: 1,
  assignment_group_name: "Network",
  category: null,
  category_name: null,
  service: null,
  service_name: null,
  impact: 2,
  urgency: 2,
  priority: 2,
  status: "in_progress",
  request_payload: {},
  custom_fields: {},
  open_tasks: 0,
  resolution_code: "",
  resolution_body: "",
  first_response_time: null,
  resolved_at: null,
  closed_at: null,
  created_at: "2026-10-20T09:00:00Z",
  updated_at: "2026-10-20T10:00:00Z",
  sla: null,
};

export const ARTICLE: Article = {
  id: 7,
  number: "KB-000007",
  title: "Fix VPN error 809",
  summary: "When the VPN drops with error 809.",
  body: "Open Settings, then Network.\nForget the VPN profile and sign in again.",
  keywords: "error 809",
  status: "published",
  visibility: "public",
  category: null,
  category_name: null,
  service: null,
  service_name: null,
  author: 3,
  author_name: "Tom Technician",
  published_at: "2026-10-01T09:00:00Z",
  created_at: "2026-10-01T09:00:00Z",
  updated_at: "2026-10-01T09:00:00Z",
};

export const RULE: TicketRule = {
  id: 1, name: "VPN to Network", description: "", position: 10, active: true, stop_processing: false,
  conditions: { keywords: ["vpn"] }, actions: { set_assignment_group: 1, set_impact: 2 },
  created_at: "2026-10-01T09:00:00Z", updated_at: "2026-10-01T09:00:00Z",
};

const page = <T>(results: T[]): Paginated<T> => ({ count: results.length, next: null, previous: null, results });

// [method, path pattern, response body]. First match wins; anything unmatched fails the test.
const ROUTES: [string, RegExp, unknown][] = [
  ["GET", /^\/api\/auth\/csrf\/$/, {}],
  ["POST", /^\/api\/auth\/logout\/$/, {}],
  ["GET", /^\/api\/help-requests\/$/, page([TICKET])],
  ["GET", /^\/api\/help-requests\/[\w-]+\/$/, TICKET],
  ["GET", /^\/api\/help-requests\/[\w-]+\/comments\/$/, [
    { id: 1, author: 3, author_name: "Tom Technician", body: "Looking into it.", visibility: "public", created_at: "2026-10-20T10:00:00Z" },
    { id: 2, author: null, author_name: null, body: "Check the VPN status page first.", visibility: "private", created_at: "2026-10-20T09:00:01Z" },
  ]],
  ["GET", /^\/api\/help-requests\/[\w-]+\/(attachments|approvals|tasks|articles)\/$/, []],
  ["POST", /^\/api\/help-requests\/[\w-]+\/articles\/$/, [ARTICLE]],
  ["GET", /^\/api\/solutions\/articles\/$/, page([ARTICLE])],
  ["GET", /^\/api\/rules\/ticket-rules\/$/, [RULE]],
  ["POST", /^\/api\/rules\/ticket-rules\/$/, RULE],
  ["GET", /^\/api\/support-groups\/$/, [{ id: 1, name: "Network" }, { id: 2, name: "Service desk" }]],
  ["GET", /^\/api\/solutions\/articles\/\d+\/$/, ARTICLE],
  ["GET", /^\/api\/queues\/$/, [{ id: 1, name: "My groups", description: "", filters: {}, ordering: "-created_at", visible_to_roles: [], position: 0, active: true }]],
  ["GET", /^\/api\/queues\/\d+\/tickets\/$/, page([TICKET])],
  ["GET", /^\/api\/approvals\/$/, page([])],
  ["GET", /^\/api\/audit\/$/, page([])],
  ["GET", /^\/api\/reports\/service-desk\/$/, {
    open_tickets: 1, unassigned: 0, sla_at_risk: 0, sla_breached: 0,
    by_priority: { P2: 1 }, by_status: { in_progress: 1 },
    backlog_by_age: { under_1_day: 1, "1_to_3_days": 0, "3_to_7_days": 0, over_7_days: 0 },
  }],
  // Lookups and resource lists: an empty array is valid for every remaining list endpoint.
  ["GET", /^\/api\/.+\/$/, []],
];

export type ApiLog = { unmatched: string[] };

/** Serve the mock API. `user` is who /auth/me/ returns; `null` means signed out until a login succeeds. */
export async function mockApi(page: Page, user: User | null, loginAs: User = ROLE_USERS.requester): Promise<ApiLog> {
  let current = user;
  const log: ApiLog = { unmatched: [] };
  await page.route((url) => url.pathname.startsWith("/api/"), async (route: Route) => {
    const request = route.request();
    const { pathname } = new URL(request.url());
    if (pathname === "/api/auth/me/") {
      return current ? route.fulfill({ json: current }) : route.fulfill({ status: 403, json: { detail: "Not signed in." } });
    }
    if (request.method() === "POST" && pathname === "/api/auth/login/") {
      current = loginAs;
      return route.fulfill({ json: {} });
    }
    const match = ROUTES.find(([method, pattern]) => method === request.method() && pattern.test(pathname));
    if (match) return route.fulfill({ json: match[2] });
    log.unmatched.push(`${request.method()} ${pathname}`);
    return route.fulfill({ status: 500, json: { detail: "No mock for this request." } });
  });
  return log;
}
