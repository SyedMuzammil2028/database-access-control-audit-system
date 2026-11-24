import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
const password = "AccessDemo!2026#";
async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email address", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Workspace overview" }),
  ).toBeVisible();
}
async function request(page: Page, action: string) {
  await page.goto("/request?resource=1");
  await page.getByLabel("Resource", { exact: true }).selectOption("1");
  await page.getByLabel("Operation", { exact: true }).selectOption(action);
  await page.getByRole("button", { name: "Evaluate access" }).click();
}
async function screenshot(page: Page, name: string) {
  await page.screenshot({
    path: `test-results/screenshots/${name}.png`,
    fullPage: true,
  });
}

test("administrator shell, every page, both themes and collapse persistence", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await login(page, "admin@example.com");
  await expect(page.locator("html")).toHaveClass("dark");
  await screenshot(page, "admin-dark");
  await page.getByRole("button", { name: "Switch to light theme" }).click();
  await expect(page.locator("html")).not.toHaveClass("dark");
  await screenshot(page, "admin-light");
  await page.reload();
  await expect(page.locator("html")).not.toHaveClass("dark");
  await page.getByRole("button", { name: "Collapse sidebar" }).click();
  await expect(page.locator(".sidebar")).toHaveCSS("width", "76px");
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Expand sidebar" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Expand sidebar" }).click();
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  for (const [path, heading] of [
    ["/users", "Users"],
    ["/roles", "Roles"],
    ["/permissions", "Permissions"],
    ["/assignments", "Role assignments"],
    ["/resources", "Resources"],
    ["/my-access", "My access"],
    ["/request", "Request access"],
    ["/history", "My access history"],
    ["/audit", "Audit events"],
    ["/policy", "Policy history"],
    ["/security", "Sign-in activity"],
    ["/account", "Account"],
  ]) {
    await page.goto(path);
    await expect(
      page.getByRole("heading", { name: heading, exact: true }),
    ).toBeVisible();
    if (!["/request", "/account"].includes(path))
      await expect(page.getByRole("table").first()).toBeVisible();
    await expect(
      page.getByText("Unable to load this view", { exact: true }),
    ).toHaveCount(0);
  }
  expect(
    await page.evaluate(() =>
      Object.keys(localStorage).every((k) =>
        ["ledger-theme", "ledger-sidebar-collapsed"].includes(k),
      ),
    ),
  ).toBe(true);
  expect(
    await page.evaluate(() => document.cookie.includes("dac_session")),
  ).toBe(false);
  expect(errors).toEqual([]);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back" }),
  ).toBeVisible();
});

test("ordinary-user requests persist allowed, denied and inactive outcomes", async ({
  page,
}) => {
  await login(page, "analyst@example.com");
  await screenshot(page, "member-dark");
  await request(page, "READ");
  await expect(
    page.getByRole("heading", { name: "Access allowed" }),
  ).toBeVisible();
  const allowedUrl = page.url();
  await screenshot(page, "decision-allowed");
  await request(page, "DELETE");
  await expect(
    page.getByRole("heading", { name: "Access denied" }),
  ).toBeVisible();
  await expect(
    page.getByText("No active role grants this operation.", { exact: false }),
  ).toBeVisible();
  await screenshot(page, "decision-denied");
  await page.goto("/request?resource=5");
  await page.getByLabel("Resource", { exact: true }).selectOption("5");
  await page.getByRole("button", { name: "Evaluate access" }).click();
  await expect(
    page.getByRole("heading", { name: "Access denied" }),
  ).toBeVisible();
  await expect(
    page.getByText("This resource is inactive.", { exact: false }),
  ).toBeVisible();
  await page.goto(allowedUrl);
  await expect(
    page.getByRole("heading", { name: "Access allowed" }),
  ).toBeVisible();
  await page.goto("/history?resource=R42");
  await expect(page.getByRole("table")).toContainText("R42");
  await expect(page.getByRole("table")).not.toContainText("admin@example.com");
  await page.goto("/users");
  await expect(
    page.getByRole("heading", { name: "Access restricted" }),
  ).toBeVisible();
});

test("complete administrator account, role, mapping, grant and revocation workflow", async ({
  page,
  browser,
}) => {
  const suffix = Date.now().toString(36);
  const name = `Review Reader ${suffix}`;
  const email = `review.${suffix}@example.com`;
  await login(page, "admin@example.com");
  await page.goto("/users");
  await page.getByRole("button", { name: "Create user", exact: true }).click();
  const userDialog = page.getByRole("dialog", { name: "Create user" });
  await userDialog
    .getByLabel("Full name", { exact: true })
    .fill("Taylor Review");
  await userDialog.getByLabel("Email address", { exact: true }).fill(email);
  await userDialog
    .getByLabel("Initial password", { exact: true })
    .fill(password);
  await userDialog.getByRole("button", { name: "Create account" }).click();
  await expect(userDialog).toBeHidden();
  await expect(
    page.getByRole("status").filter({ hasText: "Account created." }),
  ).toContainText("Account created.");
  await page.goto("/roles");
  await page.getByRole("button", { name: "Create role", exact: true }).click();
  const roleDialog = page.getByRole("dialog", { name: "Create role" });
  await roleDialog.getByLabel("Role name").fill(name);
  await roleDialog
    .getByLabel("Description", { exact: true })
    .fill("Browser-tested report reader");
  await roleDialog.getByRole("button", { name: "Create role" }).click();
  await expect(roleDialog).toBeHidden();
  await page.goto("/permissions");
  await page
    .getByRole("button", { name: "Map permission", exact: true })
    .click();
  const map = page.getByRole("dialog", { name: "Map permission" });
  await map.getByLabel("Role", { exact: true }).selectOption({ label: name });
  await map
    .getByLabel("Permission", { exact: true })
    .selectOption({ label: "READ · report" });
  await map
    .getByRole("button", { name: "Map permission", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm change" }).click();
  await expect(map).toBeHidden();
  await page.goto("/assignments");
  await page.getByRole("button", { name: "Assign role", exact: true }).click();
  const assign = page.getByRole("dialog", { name: "Assign role" });
  await assign
    .getByLabel("User", { exact: true })
    .selectOption({ label: `Taylor Review · ${email}` });
  await assign
    .getByLabel("Role", { exact: true })
    .selectOption({ label: name });
  await assign
    .getByRole("button", { name: "Assign role", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm change" }).click();
  await expect(assign).toBeHidden();
  const memberContext = await browser.newContext({
    baseURL: test.info().project.use.baseURL as string,
  });
  const member = await memberContext.newPage();
  await login(member, email);
  await request(member, "READ");
  await expect(
    member.getByRole("heading", { name: "Access allowed" }),
  ).toBeVisible();
  const historic = member.url();
  await page.getByLabel("Search", { exact: true }).fill(email);
  await page.getByRole("button", { name: "Apply filters" }).click();
  await page
    .getByRole("row")
    .filter({ hasText: email })
    .getByRole("button", { name: "Revoke role" })
    .click();
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(
    page
      .getByRole("row")
      .filter({ hasText: email })
      .getByRole("button", { name: "Revoke role" }),
  ).toBeVisible();
  await page
    .getByRole("row")
    .filter({ hasText: email })
    .getByRole("button", { name: "Revoke role" })
    .click();
  await page.getByRole("button", { name: "Confirm change" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Role revoked." }),
  ).toContainText("Role revoked.");
  await request(member, "READ");
  await expect(
    member.getByRole("heading", { name: "Access denied" }),
  ).toBeVisible();
  await member.goto(historic);
  await expect(
    member.getByRole("heading", { name: "Access allowed" }),
  ).toBeVisible();
  await memberContext.close();
  await page.goto("/policy?q=revoke_role");
  await page.getByRole("button", { name: "Inspect change" }).first().click();
  await expect(page.getByRole("dialog")).toContainText(email);
  await screenshot(page, "policy-change");
});

test("auditor filters details and downloads the exact bounded CSV", async ({
  page,
}) => {
  await login(page, "auditor@example.com");
  await screenshot(page, "auditor-dark");
  await page.goto("/audit");
  const now = new Date();
  const end = now.toISOString().slice(0, 10);
  const start = new Date(now.getTime() - 25 * 86400000)
    .toISOString()
    .slice(0, 10);
  await page.getByLabel("Search", { exact: true }).fill("analyst@example.com");
  await page.getByLabel("Decision", { exact: true }).selectOption("ALLOWED");
  await page.getByLabel("Action", { exact: true }).selectOption("READ");
  await page.getByLabel("Resource key", { exact: true }).fill("R42");
  await page.getByLabel("From (UTC)", { exact: true }).fill(start);
  await page.getByLabel("Through (UTC)", { exact: true }).fill(end);
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page.getByRole("table")).toContainText("analyst@example.com");
  await expect(page.getByRole("table")).not.toContainText("DENIED");
  await screenshot(page, "audit-filtered");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("access-audit.csv");
  const stream = await download.createReadStream();
  const chunks = [];
  for await (const chunk of stream!) chunks.push(chunk);
  const csv = Buffer.concat(chunks).toString();
  expect(csv).toContain("ALLOWED_BY_ROLE");
  expect(csv).not.toContain("DENIED");
  expect(csv).not.toContain("password_hash");
  await page
    .getByRole("link", { name: "Details", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Access allowed" }),
  ).toBeVisible();
  await expect(
    page.getByText("ALLOWED_BY_ROLE", { exact: true }),
  ).toBeVisible();
  await page.goto("/request");
  await expect(
    page.getByRole("heading", { name: "Access restricted" }),
  ).toBeVisible();
  expect(
    await page.getByRole("link", { name: "Users", exact: true }).count(),
  ).toBe(0);
});

test("mobile navigation, forms and tables remain within the viewport in both themes", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/login");
  await screenshot(page, "login-mobile-dark");
  await login(page, "admin@example.com");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await screenshot(page, "mobile-dark");
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(
    page.getByRole("dialog", { name: "Workspace navigation" }),
  ).toBeVisible();
  await page
    .getByRole("dialog")
    .getByRole("link", { name: "Users", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Users", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(page.getByRole("table")).toBeVisible();
  await screenshot(page, "users-mobile-dark");
  await page.getByRole("button", { name: "Create user", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "Create user" })).toBeVisible();
  await screenshot(page, "user-form-mobile");
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: "Switch to light theme" }).click();
  await screenshot(page, "users-mobile-light");
  for (const path of [
    "/users",
    "/audit",
    "/request",
    "/roles",
    "/resources",
    "/permissions",
  ]) {
    await page.goto(path);
    await expect(page.locator("main h1")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
  await screenshot(page, "permissions-mobile-light");
});
