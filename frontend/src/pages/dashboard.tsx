import { Link } from "react-router-dom";
import {
  Users,
  Layers,
  FolderClosed,
  Activity,
  ShieldCheck,
  CircleCheck,
  ShieldAlert,
  Clock,
  Plus,
  LockKeyhole,
} from "lucide-react";
import { useAuth } from "../lib/auth";
import { useQuery, stamp, actionLabel } from "../lib/hooks";
import type { Dashboard as DashboardData, AuditEvent } from "../lib/types";
import {
  Badge,
  Panel,
  PageHeading,
  Loading,
  ErrorState,
  Table,
} from "../components/ui";
export function EventRows({ events }: { events: AuditEvent[] }) {
  return (
    <>
      {events.map((e) => (
        <tr key={e.id}>
          <td>
            <strong>{e.actor_email}</strong>
            <small>
              {e.resource_type} · {e.resource_key}
            </small>
          </td>
          <td className="action-cell">{e.action}</td>
          <td>
            <Badge value={e.decision} />
          </td>
          <td className="muted nowrap">{stamp(e.occurred_at)}</td>
          <td>
            <Link to={`/events/${e.id}`} className="text-link">
              Details
            </Link>
          </td>
        </tr>
      ))}
    </>
  );
}
export function Dashboard() {
  const auth = useAuth();
  const kind = auth.session!.category;
  const { data, loading, error, refresh } =
    useQuery<DashboardData>("/dashboard");
  if (loading) return <Loading label="Loading workspace overview…" />;
  if (error || !data) return <ErrorState message={error} retry={refresh} />;
  const s = data.stats;
  const metrics =
    kind === "admin"
      ? [
          {
            label: "Active users",
            value: s.users,
            caption: "Accounts enabled to sign in",
            icon: Users,
          },
          {
            label: "Active roles",
            value: s.roles,
            caption: "Roles available for assignment",
            icon: Layers,
          },
          {
            label: "Active resources",
            value: s.resources,
            caption: "Registered and available",
            icon: FolderClosed,
          },
          {
            label: "Policy changes",
            value: s.policies,
            caption: "Recorded administrative updates",
            icon: Activity,
          },
        ]
      : [
          {
            label: "Access decisions",
            value: s.events,
            caption: "All recorded evaluations",
            icon: Activity,
          },
          {
            label: "Allowed",
            value: s.allowed,
            caption: "Matched an active permission",
            icon: CircleCheck,
          },
          {
            label: "Denied",
            value: s.denied,
            caption: "Stopped by the access policy",
            icon: ShieldAlert,
          },
          {
            label: "Active resources",
            value: s.resources,
            caption: "Available in the registry",
            icon: FolderClosed,
          },
        ];
  return (
    <>
      <PageHeading
        eyebrow={
          kind === "admin"
            ? "ADMINISTRATION"
            : kind === "auditor"
              ? "INVESTIGATION"
              : "YOUR WORKSPACE"
        }
        title="Workspace overview"
        description={
          kind === "admin"
            ? "Manage identities, maintain policy, and monitor access."
            : kind === "auditor"
              ? "Investigate access decisions and trace administrative changes."
              : "Review your permissions and request operations on registered resources."
        }
        action={
          <Link
            className="btn btn-primary"
            to={
              kind === "admin"
                ? "/users?create=1"
                : kind === "auditor"
                  ? "/audit"
                  : "/request"
            }
          >
            {kind === "admin" ? (
              <Plus size={16} />
            ) : kind === "auditor" ? (
              <Activity size={16} />
            ) : (
              <LockKeyhole size={16} />
            )}
            {kind === "admin"
              ? "Create user"
              : kind === "auditor"
                ? "Explore audit events"
                : "Request access"}
          </Link>
        }
      />
      <div className="metrics">
        {metrics.map((m) => (
          <div className="metric" key={m.label}>
            <div>
              <p>{m.label}</p>
              <strong>{m.value.toLocaleString()}</strong>
              <small>{m.caption}</small>
            </div>
            <div className="metric-icon">
              <m.icon size={18} />
            </div>
          </div>
        ))}
      </div>
      <div className="dashboard-grid">
        <Panel
          title="Recent access decisions"
          description={
            kind === "user"
              ? "Your latest requests and their recorded outcomes."
              : "Latest evaluations across the workspace."
          }
          action={
            <Link
              to={kind === "user" ? "/history" : "/audit"}
              className="text-link"
            >
              View all events
            </Link>
          }
        >
          <Table
            headers={[
              "Actor / resource",
              "Action",
              "Decision",
              "Time (UTC)",
              "",
            ]}
            count={data.recent.length}
          >
            <EventRows events={data.recent} />
          </Table>
          <div className="panel-footer">
            <ShieldCheck size={14} />
            Every completed evaluation is recorded, including denials.
          </div>
        </Panel>
        <div className="dashboard-aside">
          <Panel title="Last 7 days">
            <div className="activity-summary">
              <strong>
                {s.recent}
                <span> evaluations</span>
              </strong>
              <div>
                <span className="success-text">
                  {s.recent - s.recent_denied} allowed
                </span>
                <span className="danger-text">{s.recent_denied} denied</span>
              </div>
              <p>
                Each decision reflects the policy in effect at the time of the
                request.
              </p>
            </div>
          </Panel>
          <Panel
            title={kind === "user" ? "Your active roles" : "Workspace controls"}
          >
            <div className="quick-links">
              {kind === "user" ? (
                <>
                  <div className="tags">
                    {auth.session!.roles.map((r) => (
                      <span className="tag" key={r.id}>
                        {r.name}
                      </span>
                    ))}
                    {!auth.session!.roles.length && (
                      <p className="muted">No active roles assigned.</p>
                    )}
                  </div>
                  <Link to="/my-access" className="text-link">
                    Review effective permissions
                  </Link>
                </>
              ) : (
                (kind === "admin"
                  ? [
                      [
                        "/assignments",
                        "Role assignments",
                        "Maintain who has access",
                      ],
                      [
                        "/permissions",
                        "Permission mappings",
                        "Review what each role can do",
                      ],
                      [
                        "/policy",
                        "Policy history",
                        "Trace administrative changes",
                      ],
                    ]
                  : [
                      [
                        "/audit",
                        "Access investigation",
                        "Filter decisions and export reports",
                      ],
                      [
                        "/policy",
                        "Policy history",
                        "Review administrative changes",
                      ],
                      [
                        "/security",
                        "Sign-in activity",
                        "Inspect authentication events",
                      ],
                    ]
                ).map(([path, label, caption]) => (
                  <Link to={path} key={path}>
                    <strong>{label}</strong>
                    <span>{caption}</span>
                  </Link>
                ))
              )}
            </div>
          </Panel>
        </div>
      </div>
      {kind !== "user" && (
        <Panel
          className="mt-6"
          title="Latest policy changes"
          description="Administrative updates recorded with the operation."
          action={
            <Link className="text-link" to="/policy">
              View policy history
            </Link>
          }
        >
          <Table
            headers={["Administrator", "Operation", "Target", "Time (UTC)"]}
            count={data.changes.length}
          >
            {data.changes.map((c) => (
              <tr key={c.id}>
                <td>{c.actor_email}</td>
                <td>{actionLabel(c.operation)}</td>
                <td className="mono">
                  {c.target_type} / {c.target_id}
                </td>
                <td className="muted nowrap">{stamp(c.occurred_at)}</td>
              </tr>
            ))}
          </Table>
        </Panel>
      )}
    </>
  );
}
