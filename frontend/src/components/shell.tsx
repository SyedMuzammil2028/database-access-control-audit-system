import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  ShieldCheck,
  KeyRound,
  Layers,
  FolderClosed,
  ListChecks,
  ClipboardList,
  History,
  LockKeyhole,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Menu,
  Sun,
  Moon,
  X,
  UserRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import { useAuth } from "../lib/auth";
import { useStoredState } from "../lib/hooks";
import { Alert, Button, IconButton } from "./ui";

export function ThemeToggle() {
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem("ledger-theme") === "light"
        ? "light"
        : "dark";
    } catch {
      return "dark";
    }
  });
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    try {
      localStorage.setItem("ledger-theme", theme);
    } catch {
      /* UI preferences are optional. */
    }
  }, [theme]);
  return (
    <IconButton
      label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
    </IconButton>
  );
}
export function Brand({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <Link to="/" className="brand" aria-label="Access Ledger home">
      <div className="brand-mark">
        <ShieldCheck size={21} />
      </div>
      {!collapsed && (
        <div>
          <strong>Access Ledger</strong>
          <span>Database security</span>
        </div>
      )}
    </Link>
  );
}
interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
}
const titles: Record<string, string> = {
  "/": "Overview",
  "/users": "Users",
  "/roles": "Roles",
  "/permissions": "Permissions",
  "/assignments": "Role assignments",
  "/resources": "Resources",
  "/my-access": "My access",
  "/request": "Request access",
  "/history": "My access history",
  "/audit": "Audit events",
  "/policy": "Policy history",
  "/security": "Sign-in activity",
  "/account": "Account",
};
export function Shell() {
  const { session, logout } = useAuth();
  const { pathname } = useLocation();
  const [collapsed, setCollapsed] = useStoredState<boolean>(
    "ledger-sidebar-collapsed",
    false,
  );
  const [mobile, setMobile] = useState(false);
  const [error, setError] = useState("");
  const [signingOut, setSigningOut] = useState(false);
  const kind = session!.category;
  const user = session!.user;
  const groups: { title: string; items: NavItem[] }[] = [
    {
      title: "Workspace",
      items: [
        { path: "/", label: "Overview", icon: LayoutDashboard },
        { path: "/my-access", label: "My access", icon: KeyRound },
        { path: "/resources", label: "Resources", icon: FolderClosed },
        ...(kind !== "auditor"
          ? [
              { path: "/request", label: "Request access", icon: LockKeyhole },
              { path: "/history", label: "My access history", icon: History },
            ]
          : []),
      ],
    },
  ];
  if (kind === "admin")
    groups.push({
      title: "Administration",
      items: [
        { path: "/users", label: "Users", icon: Users },
        { path: "/roles", label: "Roles", icon: Layers },
        { path: "/permissions", label: "Permissions", icon: KeyRound },
        { path: "/assignments", label: "Role assignments", icon: ListChecks },
      ],
    });
  if (kind !== "user")
    groups.push({
      title: "Investigation",
      items: [
        { path: "/audit", label: "Audit events", icon: ClipboardList },
        { path: "/policy", label: "Policy history", icon: History },
        { path: "/security", label: "Sign-in activity", icon: LockKeyhole },
      ],
    });
  useEffect(() => {
    setMobile(false);
    document.title = `${titles[pathname] || "Access decision"} · Access Ledger`;
  }, [pathname]);
  async function signOut() {
    setSigningOut(true);
    setError("");
    try {
      await logout();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to sign out.");
    } finally {
      setSigningOut(false);
    }
  }
  function Navigation({ compact = false }: { compact?: boolean }) {
    return (
      <>
        <nav aria-label="Main navigation">
          {groups.map((group) => (
            <div className="nav-group" key={group.title}>
              <div className={`nav-section ${compact ? "sr-only" : ""}`}>
                {group.title}
              </div>
              {group.items.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end
                  title={compact ? item.label : undefined}
                  aria-label={compact ? item.label : undefined}
                  className={({ isActive }) =>
                    `nav-link ${isActive ? "active" : ""}`
                  }
                >
                  <item.icon size={18} />
                  {!compact && <span>{item.label}</span>}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          {!compact && (
            <div className="policy-note">
              <ShieldCheck size={17} />
              <div>
                Default-deny policy<small>Explicit permission required</small>
              </div>
            </div>
          )}
          <NavLink
            to="/account"
            className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            aria-label={compact ? "Account" : undefined}
          >
            <UserRound size={18} />
            {!compact && "Account"}
          </NavLink>
          <button
            className="nav-link"
            onClick={() => void signOut()}
            disabled={signingOut}
            aria-label="Sign out"
          >
            <LogOut size={18} />
            {!compact && (signingOut ? "Signing out…" : "Sign out")}
          </button>
        </div>
      </>
    );
  }
  return (
    <div className={`app-shell ${collapsed ? "collapsed" : ""}`}>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">
        <div className="sidebar-brand">
          <Brand collapsed={collapsed} />
        </div>
        <Navigation compact={collapsed} />
        <div className="collapse-control">
          <IconButton
            label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? (
              <PanelLeftOpen size={18} />
            ) : (
              <PanelLeftClose size={18} />
            )}
          </IconButton>
          {!collapsed && <span>Collapse sidebar</span>}
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="topbar-title">
            <div className="mobile-menu">
              <IconButton
                label="Open navigation"
                onClick={() => setMobile(true)}
              >
                <Menu size={20} />
              </IconButton>
            </div>
            <span className="header-workspace">
              Workspace <span>/</span>
            </span>
            <strong>{titles[pathname] || "Access decision"}</strong>
          </div>
          <div className="topbar-actions">
            <span className="environment">Development</span>
            <ThemeToggle />
            <Link to="/account" className="user-profile">
              <span className="avatar">
                {user.name
                  .split(" ")
                  .map((x) => x[0])
                  .slice(0, 2)
                  .join("")}
              </span>
              <div>
                <span>{user.name}</span>
                <small>
                  {kind === "admin"
                    ? "Administrator"
                    : kind === "auditor"
                      ? "Auditor"
                      : "Member"}
                </small>
              </div>
            </Link>
          </div>
        </header>
        <main id="main" className="main-content">
          {error && <Alert onClose={() => setError("")}>{error}</Alert>}
          <Outlet />
        </main>
        <footer className="workspace-footer">
          <span>Database Access Control &amp; Audit System</span>
          <span>All event times in UTC</span>
        </footer>
      </div>
      <Dialog.Root open={mobile} onOpenChange={setMobile}>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay mobile-only" />
          <Dialog.Content className="mobile-drawer">
            <Dialog.Title className="sr-only">
              Workspace navigation
            </Dialog.Title>
            <Dialog.Description className="sr-only">
              Navigate your access control workspace.
            </Dialog.Description>
            <div className="sidebar-brand">
              <Brand />
              <Dialog.Close asChild>
                <IconButton label="Close navigation">
                  <X size={18} />
                </IconButton>
              </Dialog.Close>
            </div>
            <Navigation />
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
