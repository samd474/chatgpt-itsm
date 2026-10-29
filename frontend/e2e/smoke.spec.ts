import { expect, test, type Page } from "@playwright/test";
import { ARTICLE, mockApi, ROLE_USERS, TICKET } from "./mockApi";

// Fail any test whose page throws or logs an error.
let problems: string[] = [];
test.beforeEach(({ page }) => {
  problems = [];
  page.on("pageerror", (error) => problems.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    // The browser logs the expected 403 from /api/auth/me/ while signed out; anything else is a problem.
    if (message.type() === "error" && !message.text().includes("status of 403")) problems.push(`console: ${message.text()}`);
  });
});
test.afterEach(() => expect(problems).toEqual([]));

async function expectPage(page: Page, path: string) {
  await expect(page).toHaveURL(new RegExp(`${path}$`));
  await expect(page.locator("h1").first()).toBeVisible();
}

test("signed-out visitors are sent to the login page", async ({ page }) => {
  await mockApi(page, null);
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});

test("signing in lands on the role's home page", async ({ page }) => {
  await mockApi(page, null, ROLE_USERS.technician);
  await page.goto("/login");
  await page.getByLabel("Username").fill("tom");
  await page.getByLabel("Password").fill("correct horse");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expectPage(page, "/tech/queue");
});

for (const [role, home] of [["requester", "/portal"], ["technician", "/tech/queue"], ["auditor", "/audit"], ["admin", "/tech/queue"]] as const) {
  test(`/ takes a ${role} to ${home}`, async ({ page }) => {
    await mockApi(page, ROLE_USERS[role]);
    await page.goto("/");
    await expectPage(page, home);
  });
}

test("requesters are kept out of staff screens", async ({ page }) => {
  await mockApi(page, ROLE_USERS.requester);
  for (const path of ["/tech/queue", "/assets", "/manage/users"]) {
    await page.goto(path);
    await expectPage(page, "/portal");
  }
});

test("a requester can open their ticket and see the conversation", async ({ page }) => {
  await mockApi(page, ROLE_USERS.requester);
  await page.goto(`/portal/tickets/${TICKET.public_id}`);
  await expect(page.getByText(TICKET.subject).first()).toBeVisible();
  await expect(page.getByText("Looking into it.")).toBeVisible();
});

test("a technician can open a ticket from the queue", async ({ page }) => {
  await mockApi(page, ROLE_USERS.technician);
  await page.goto("/tech/queue");
  await page.getByText(TICKET.subject).first().click();
  await expect(page).toHaveURL(new RegExp(`/tech/tickets/${TICKET.public_id}$`));
  await expect(page.getByText("Looking into it.")).toBeVisible();
});

test("a requester can search the knowledge base and read an article", async ({ page }) => {
  await mockApi(page, ROLE_USERS.requester);
  await page.goto("/knowledge");
  await page.getByPlaceholder("Search articles, e.g. an error message").fill("809");
  await page.getByText(ARTICLE.title).click();
  await expect(page).toHaveURL(new RegExp(`/knowledge/${ARTICLE.id}$`));
  await expect(page.getByText("Forget the VPN profile and sign in again.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Edit" })).toHaveCount(0);
});

test("a technician links an article and uses it as the resolution", async ({ page }) => {
  await mockApi(page, ROLE_USERS.technician);
  await page.goto(`/tech/tickets/${TICKET.public_id}`);
  await page.getByLabel("Search published articles").fill("vpn");
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("button", { name: "Link" }).click();
  await page.getByRole("button", { name: "Use as resolution" }).click();
  await expect(page.getByLabel("New status")).toHaveValue("resolved");
  await expect(page.getByPlaceholder("What fixed it? The requester sees this.")).toHaveValue(/Forget the VPN profile[\s\S]*KB-000007/);
});

test("an administrator reads and creates automation rules", async ({ page }) => {
  await mockApi(page, ROLE_USERS.admin);
  await page.goto("/manage/tickets");
  await page.getByRole("tab", { name: "Automation" }).click();
  await expect(page.getByText('When mentions "vpn": route to Network, impact High')).toBeVisible();

  await page.getByRole("button", { name: "New rule" }).click();
  await page.getByLabel("Name").fill("Printers to the desk");
  await page.getByLabel("Keywords").fill("printer\n  toner  \n");
  await page.getByLabel("Route to group").selectOption({ label: "Service desk" });
  const saved = page.waitForRequest((r) => r.method() === "POST" && r.url().endsWith("/api/rules/ticket-rules/"));
  await page.getByRole("button", { name: "Save" }).click();
  const body = (await saved).postDataJSON();
  expect(body.conditions).toEqual({ keywords: ["printer", "toner"] });
  expect(body.actions).toEqual({ set_assignment_group: 2 });
  // Saving closes the drawer and refetches the list; let that finish while the API is still mocked.
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.waitForLoadState("networkidle");
});

test("notes added by automation are labelled as such", async ({ page }) => {
  await mockApi(page, ROLE_USERS.technician);
  await page.goto(`/tech/tickets/${TICKET.public_id}`);
  await expect(page.getByText("Check the VPN status page first.")).toBeVisible();
  await expect(page.locator(".entry-head strong", { hasText: "Automation" })).toBeVisible();
});

// Every list screen renders for an administrator, who can reach all of them.
const SCREENS = [
  "/portal", "/portal/incidents/new", "/portal/catalog", "/portal/equipment", "/approvals",
  "/tech/queue", "/assets", "/contracts", "/changes", "/changes/calendar", "/projects",
  "/reports", "/audit", "/manage/users", "/manage/tickets", "/manage/settings", "/knowledge", "/knowledge/new",
];
for (const path of SCREENS) {
  test(`${path} renders`, async ({ page }) => {
    const api = await mockApi(page, ROLE_USERS.admin);
    await page.goto(path);
    await expectPage(page, path);
    await page.waitForLoadState("networkidle");
    expect(api.unmatched).toEqual([]);
  });
}
