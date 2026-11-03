import type { Page, Route } from "@playwright/test";
import type { Article, Paginated, SlaReport, Ticket, TicketRule, User } from "../src/types";

// The browser only ever talks to /api; these tests answer it in-process, so they need no backend.

const NO_2FA = { two_factor_enabled: false, two_factor_required: false, two_factor_setup_needed: false };

export const ROLE_USERS = {
  requester: { id: 2, username: "rita", name: "Rita Requester", groups: ["Requester"], is_superuser: false, ...NO_2FA },
  technician: { id: 3, username: "tom", name: "Tom Technician", groups: ["Technician"], is_superuser: false, ...NO_2FA },
  auditor: { id: 4, username: "ada", name: "Ada Auditor", groups: ["Auditor"], is_superuser: false, ...NO_2FA },
  // Administrators must use 2FA; this one already has it set up.
  admin: { id: 1, username: "root", name: "Root Admin", groups: ["Administrator"], is_superuser: true,
    two_factor_enabled: true, two_factor_required: true, two_factor_setup_needed: false },
} satisfies Record<string, User>;

export const VALID_CODE = "123456";
export const RECOVERY_CODES = ["aaaa1111", "bbbb2222", "cccc3333"];

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
  my_feedback: null,
};

export const RULE: TicketRule = {
  id: 1, name: "VPN to Network", description: "", position: 10, active: true, stop_processing: false, runs_on: "created",
  conditions: { keywords: ["vpn"] }, actions: { set_assignment_group: 1, set_impact: 2 },
  created_at: "2026-10-01T09:00:00Z", updated_at: "2026-10-01T09:00:00Z",
};

const page = <T>(results: T[]): Paginated<T> => ({ count: results.length, next: null, previous: null, results });

// [method, path pattern, response body]. First match wins; anything unmatched fails the test.
// A fixed 30-day picture: one breached ticket, one at risk, and a trend with a few late days.
const DAY = 86_400_000;
const TODAY = Date.UTC(2026, 10, 3);
export const SLA_REPORT: SlaReport = {
  generated_at: new Date().toISOString(),
  days: 30,
  now: { breached: 1, at_risk: 1, paused: 2, on_track: 7, no_sla: 0 },
  attention: [
    { public_id: TICKET.public_id, request_number: "INC-000001", subject: "VPN drops every few minutes", priority: 2,
      status: "in_progress", assignment_group: "Network", technician: "Tom Technician", state: "breached",
      target: "resolution", due_at: new Date(Date.now() - 3 * 3_600_000).toISOString(), paused: false },
    { public_id: "0b8e7d6c-5b4a-4392-8170-6f5e4d3c2b1a", request_number: "INC-000002", subject: "Printer offline on floor 3",
      priority: 3, status: "new", assignment_group: "Desktop", technician: null, state: "at_risk",
      target: "resolution", due_at: new Date(Date.now() + 45 * 60_000).toISOString(), paused: false },
  ],
  period: { resolved: 84, resolution_met_percent: 91.7, responded: 96, response_met_percent: 95.8 },
  trend: Array.from({ length: 30 }, (_, i) => ({
    date: new Date(TODAY - (29 - i) * DAY).toISOString().slice(0, 10),
    met: [2, 3, 1, 4, 2, 0, 0][i % 7] + (i % 5 === 0 ? 1 : 0),
    breached: i % 9 === 4 ? 1 : i === 27 ? 2 : 0,
  })),
  by_group: [
    { key: 1, name: "Network", resolved: 40, resolution_met_percent: 87.5, responded: 44, response_met_percent: 93.2, open_breached: 1 },
    { key: 2, name: "Desktop", resolved: 44, resolution_met_percent: 95.5, responded: 52, response_met_percent: 98.1, open_breached: 0 },
  ],
  by_priority: [
    { key: 1, name: "P1", resolved: 6, resolution_met_percent: 100, responded: 6, response_met_percent: 100, open_breached: 0 },
    { key: 2, name: "P2", resolved: 30, resolution_met_percent: 86.7, responded: 34, response_met_percent: 94.1, open_breached: 1 },
    { key: 3, name: "P3", resolved: 48, resolution_met_percent: 93.8, responded: 56, response_met_percent: 96.4, open_breached: 0 },
  ],
};

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
  ["GET", /^\/api\/solutions\/articles\/suggest\/$/, [{ id: ARTICLE.id, number: ARTICLE.number, title: ARTICLE.title, summary: ARTICLE.summary }]],
  ["POST", /^\/api\/solutions\/articles\/\d+\/feedback\/$/, { ...ARTICLE, my_feedback: true }],
  ["GET", /^\/api\/rules\/ticket-rules\/$/, [RULE]],
  ["POST", /^\/api\/rules\/ticket-rules\/$/, RULE],
  ["POST", /^\/api\/rules\/ticket-rules\/preview\/$/, {
    scanned: 3, matched: 1, ignored_conditions: ["changed"],
    tickets: [{ public_id: TICKET.public_id, request_number: TICKET.request_number, subject: TICKET.subject, status: TICKET.status,
      changes: [{ field: "assignment_group", from: null, to: "Network" }] }],
  }],
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
  ["GET", /^\/api\/reports\/sla\/$/, SLA_REPORT],
  // Lookups and resource lists: an empty array is valid for every remaining list endpoint.
  ["GET", /^\/api\/.+\/$/, []],
];

export type ApiLog = { unmatched: string[] };

/** Serve the mock API. `user` is who /auth/me/ returns; `null` means signed out until a login succeeds. */
export async function mockApi(page: Page, user: User | null, loginAs: User = ROLE_USERS.requester): Promise<ApiLog> {
  let current = user;
  let awaitingCode = false;
  let body: Record<string, unknown> | null = null;
  const token = () => String(body?.token ?? "");
  const wrongCode = (route: Route) => route.fulfill({ status: 400, json: { detail: "That code isn't valid." } });
  const setTwoFactor = (enabled: boolean) => {
    if (current) current = { ...current, two_factor_enabled: enabled, two_factor_setup_needed: current.two_factor_required && !enabled };
  };
  const log: ApiLog = { unmatched: [] };
  await page.route((url) => url.pathname.startsWith("/api/"), async (route: Route) => {
    const request = route.request();
    const { pathname } = new URL(request.url());
    if (pathname === "/api/auth/me/") {
      return current ? route.fulfill({ json: current }) : route.fulfill({ status: 403, json: { detail: "Not signed in." } });
    }
    body = request.method() === "POST" ? (request.postDataJSON() as Record<string, unknown> | null) : null;
    if (request.method() === "POST" && pathname === "/api/auth/login/") {
      if (loginAs.two_factor_enabled) {
        awaitingCode = true;
        return route.fulfill({ json: { two_factor_required: true } });
      }
      current = loginAs;
      return route.fulfill({ json: { id: loginAs.id, username: loginAs.username, two_factor_required: false } });
    }
    if (request.method() === "POST" && pathname === "/api/auth/2fa/verify/") {
      if (!awaitingCode || token() !== VALID_CODE) return wrongCode(route);
      current = loginAs;
      return route.fulfill({ json: { id: loginAs.id, username: loginAs.username, two_factor_required: false } });
    }
    if (current && pathname.startsWith("/api/auth/2fa/")) {
      if (request.method() === "GET" && pathname === "/api/auth/2fa/") {
        return route.fulfill({ json: { enabled: current.two_factor_enabled, required_by_role: current.two_factor_required,
          recovery_codes_left: current.two_factor_enabled ? RECOVERY_CODES.length : 0 } });
      }
      if (pathname === "/api/auth/2fa/setup/") {
        return route.fulfill({ json: { otpauth_url: "otpauth://totp/ITSM:mock?secret=JBSWY3DPEHPK3PXP", secret: "JBSWY3DPEHPK3PXP",
          qr_svg: "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciLz4=" } });
      }
      if (token() !== VALID_CODE) return wrongCode(route);
      if (pathname === "/api/auth/2fa/confirm/") { setTwoFactor(true); return route.fulfill({ json: { recovery_codes: RECOVERY_CODES } }); }
      if (pathname === "/api/auth/2fa/recovery-codes/") return route.fulfill({ json: { recovery_codes: RECOVERY_CODES } });
      if (pathname === "/api/auth/2fa/disable/") { setTwoFactor(false); return route.fulfill({ status: 204 }); }
    }
    const match = ROUTES.find(([method, pattern]) => method === request.method() && pattern.test(pathname));
    if (match) return route.fulfill({ json: match[2] });
    log.unmatched.push(`${request.method()} ${pathname}`);
    return route.fulfill({ status: 500, json: { detail: "No mock for this request." } });
  });
  return log;
}
