import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import type { Session } from "../lib/types";

const date = "2026-11-21T12:00:00Z";
const role = {
  id: 3,
  name: "Report Analyst",
  description: "Read reports",
  kind: "user" as const,
  active: true,
};
const user = {
  id: 7,
  name: "Samira Khan",
  email: "analyst@example.com",
  active: true,
  created_at: date,
  updated_at: date,
};
function session(category: Session["category"] = "user"): Session {
  return {
    user,
    category,
    csrf_token: "session-csrf",
    expires_at: date,
    roles: [role],
    permissions: [{ action: "READ", resource_type: "report" }],
  };
}
const event = {
  id: "event-1",
  actor_user_id: 7,
  actor_email: user.email,
  action: "READ",
  resource_id: 1,
  resource_type: "report",
  resource_key: "R42",
  decision: "ALLOWED",
  reason_code: "ALLOWED_BY_ROLE",
  matching_role_id: 3,
  matching_role_name: "Report Analyst",
  request_id: "request-1",
  occurred_at: date,
};
const dashboard = {
  stats: {
    events: 7,
    allowed: 5,
    denied: 2,
    users: 9,
    roles: 5,
    resources: 14,
    policies: 13,
    recent: 4,
    recent_denied: 1,
  },
  recent: [event],
  changes: [],
};
function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
function mockApi(
  auth: Session | null,
  extra?: (path: string, init?: RequestInit) => Response | undefined,
) {
  return vi.fn(async (input: string | Request | URL, init?: RequestInit) => {
    const path = String(input);
    const special = extra?.(path, init);
    if (special) return special;
    if (path === "/api/auth/session")
      return response(
        auth || { message: "Sign in required." },
        auth ? 200 : 401,
      );
    if (path === "/api/auth/csrf")
      return response({ csrf_token: "login-csrf" });
    if (path === "/api/dashboard") return response(dashboard);
    if (path.startsWith("/api/options/"))
      return response({
        items: [
          { id: 1, label: "Report · R42 · Quarterly report", active: true },
        ],
        has_more: false,
      });
    if (path === "/api/events/event-1") return response(event);
    if (path.startsWith("/api/"))
      return response({
        items: [],
        total: 0,
        page: 1,
        pages: 1,
        page_size: 20,
      });
    return response({ message: "Unexpected endpoint." }, 404);
  });
}
beforeEach(() => {
  window.history.replaceState({}, "", "/");
  localStorage.clear();
  document.documentElement.className = "dark";
});

describe("authentication and protected navigation", () => {
  it("posts login CSRF and credentials, then displays real API dashboard data", async () => {
    const fetcher = mockApi(null, (path, init) =>
      path === "/api/auth/login" ? response(session()) : undefined,
    );
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    const ui = userEvent.setup();
    await ui.type(await screen.findByLabelText("Email address"), user.email);
    await ui.type(screen.getByLabelText("Password"), "AccessDemo!2026#");
    await ui.click(screen.getByRole("button", { name: "Sign in" }));
    expect(
      await screen.findByRole("heading", { name: "Workspace overview" }),
    ).toBeInTheDocument();
    const login = fetcher.mock.calls.find(
      ([path]) => path === "/api/auth/login",
    )!;
    expect(JSON.parse(login[1]!.body as string)).toEqual({
      email: user.email,
      password: "AccessDemo!2026#",
      csrf_token: "login-csrf",
    });
    expect(
      screen.getByText("7", { selector: ".metric strong" }),
    ).toBeInTheDocument();
    expect(localStorage.getItem("dac_session")).toBeNull();
  });
  it("keeps failed login on the sign-in page with the server error", async () => {
    vi.stubGlobal(
      "fetch",
      mockApi(null, (path) =>
        path === "/api/auth/login"
          ? response({ message: "Email or password is incorrect." }, 400)
          : undefined,
      ),
    );
    render(<App />);
    const ui = userEvent.setup();
    await ui.type(await screen.findByLabelText("Email address"), user.email);
    await ui.type(screen.getByLabelText("Password"), "wrong");
    await ui.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email or password is incorrect.",
    );
    expect(
      screen.queryByRole("heading", { name: "Workspace overview" }),
    ).not.toBeInTheDocument();
  });
  it("prevents auditor navigation to administrator routes", async () => {
    window.history.replaceState({}, "", "/users");
    const fetcher = mockApi(session("auditor"));
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    expect(
      await screen.findByRole("heading", { name: "Access restricted" }),
    ).toBeInTheDocument();
    expect(fetcher.mock.calls.some(([path]) => path === "/api/users")).toBe(
      false,
    );
    expect(
      screen.queryByRole("link", { name: "Request access" }),
    ).not.toBeInTheDocument();
  });
  it("logs out only after a confirmed backend response", async () => {
    const fetcher = mockApi(session(), (path) =>
      path === "/api/auth/logout"
        ? response({ message: "Signed out." })
        : undefined,
    );
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Sign out" }),
    );
    expect(await screen.findByLabelText("Email address")).toBeInTheDocument();
    const call = fetcher.mock.calls.find(
      ([path]) => path === "/api/auth/logout",
    )!;
    expect(call[1]!.headers).toMatchObject({ "X-CSRF-Token": "session-csrf" });
  });
});

describe("workspace interactions", () => {
  it("persists both theme changes and sidebar collapse", async () => {
    vi.stubGlobal("fetch", mockApi(session("admin")));
    render(<App />);
    const ui = userEvent.setup();
    await ui.click(
      await screen.findByRole("button", { name: "Switch to light theme" }),
    );
    expect(document.documentElement).not.toHaveClass("dark");
    expect(localStorage.getItem("ledger-theme")).toBe("light");
    await ui.click(screen.getByRole("button", { name: "Collapse sidebar" }));
    expect(
      screen.getByRole("button", { name: "Expand sidebar" }),
    ).toBeInTheDocument();
    expect(localStorage.getItem("ledger-sidebar-collapsed")).toBe("true");
  });
  it("opens and closes the mobile navigation with accessible controls", async () => {
    vi.stubGlobal("fetch", mockApi(session()));
    render(<App />);
    const ui = userEvent.setup();
    await ui.click(
      await screen.findByRole("button", { name: "Open navigation" }),
    );
    expect(
      await screen.findByRole("dialog", { name: "Workspace navigation" }),
    ).toBeInTheDocument();
    await ui.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  it("does not claim a role was created when the backend rejects it", async () => {
    window.history.replaceState({}, "", "/roles");
    vi.stubGlobal(
      "fetch",
      mockApi(session("admin"), (path, init) =>
        path === "/api/roles" && init?.method === "POST"
          ? response({ message: "This role already exists." }, 409)
          : undefined,
      ),
    );
    render(<App />);
    const ui = userEvent.setup();
    await ui.click(await screen.findByRole("button", { name: "Create role" }));
    const dialog = screen.getByRole("dialog", { name: "Create role" });
    await ui.type(within(dialog).getByLabelText("Role name"), "Report Analyst");
    await ui.click(within(dialog).getByRole("button", { name: "Create role" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "This role already exists.",
    );
    expect(
      screen.queryByText("Role created. Map permissions to define its access."),
    ).not.toBeInTheDocument();
  });
  it("displays server validation errors beside the relevant field", async () => {
    window.history.replaceState({}, "", "/roles");
    vi.stubGlobal(
      "fetch",
      mockApi(session("admin"), (path, init) =>
        path === "/api/roles" && init?.method === "POST"
          ? response(
              {
                message: "Check fields.",
                errors: [{ field: "name", message: "This name is reserved." }],
              },
              422,
            )
          : undefined,
      ),
    );
    render(<App />);
    const ui = userEvent.setup();
    await ui.click(await screen.findByRole("button", { name: "Create role" }));
    const dialog = screen.getByRole("dialog");
    await ui.type(within(dialog).getByLabelText("Role name"), "Reserved");
    await ui.click(within(dialog).getByRole("button", { name: "Create role" }));
    expect(
      await within(dialog).findByText("This name is reserved."),
    ).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Role name")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });
  it("requires confirmation before deactivating an account", async () => {
    window.history.replaceState({}, "", "/users");
    const fetcher = mockApi(session("admin"), (path, init) =>
      path === "/api/users" && init?.method === "GET"
        ? response({
            items: [{ ...user, roles: [role] }],
            total: 1,
            page: 1,
            pages: 1,
            page_size: 20,
          })
        : String(path).endsWith("/status")
          ? response({ ...user, active: false })
          : undefined,
    );
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    const ui = userEvent.setup();
    await ui.click(await screen.findByRole("button", { name: "Deactivate" }));
    await ui.click(screen.getByRole("button", { name: "Cancel" }));
    expect(
      fetcher.mock.calls.some(([path]) => String(path).endsWith("/status")),
    ).toBe(false);
    await ui.click(screen.getByRole("button", { name: "Deactivate" }));
    await ui.click(screen.getByRole("button", { name: "Confirm change" }));
    await waitFor(() =>
      expect(
        fetcher.mock.calls.some(([path]) => String(path).endsWith("/status")),
      ).toBe(true),
    );
  });
  it("submits a UUID and session CSRF for a resource decision", async () => {
    window.history.replaceState({}, "", "/request");
    const fetcher = mockApi(session(), (path) =>
      path === "/api/access" ? response(event) : undefined,
    );
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    const ui = userEvent.setup();
    const select = await screen.findByLabelText("Resource");
    await waitFor(() =>
      expect(
        within(select).getByRole("option", {
          name: "Report · R42 · Quarterly report",
        }),
      ).toBeInTheDocument(),
    );
    await ui.selectOptions(select, "1");
    await ui.click(screen.getByRole("button", { name: "Evaluate access" }));
    expect(
      await screen.findByRole("heading", { name: "Access allowed" }),
    ).toBeInTheDocument();
    const call = fetcher.mock.calls.find(([path]) => path === "/api/access")!;
    const payload = JSON.parse(call[1]!.body as string);
    expect(payload).toMatchObject({ action: "READ", resource_id: 1 });
    expect(payload.request_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(call[1]!.headers).toMatchObject({ "X-CSRF-Token": "session-csrf" });
  });
  it("applies report filters to the API and resets pagination", async () => {
    window.history.replaceState({}, "", "/audit?page=3");
    const fetcher = mockApi(session("auditor"));
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    const ui = userEvent.setup();
    await ui.selectOptions(await screen.findByLabelText("Decision"), "DENIED");
    await ui.type(screen.getByLabelText("Resource key"), "R42");
    await ui.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() =>
      expect(
        fetcher.mock.calls.some(
          ([path]) =>
            String(path).includes("/audit?") &&
            String(path).includes("decision=DENIED") &&
            String(path).includes("resource=R42") &&
            !String(path).includes("page=3"),
        ),
      ).toBe(true),
    );
  });
  it("shows a recoverable API error instead of fake dashboard metrics", async () => {
    vi.stubGlobal(
      "fetch",
      mockApi(session(), (path) =>
        path === "/api/dashboard"
          ? response({ message: "Database unavailable." }, 503)
          : undefined,
      ),
    );
    render(<App />);
    expect(
      await screen.findByText("Database unavailable."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Access decisions")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Try again" }),
    ).toBeInTheDocument();
  });
});
