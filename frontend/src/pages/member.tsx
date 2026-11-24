import { useRef } from "react";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { CircleCheck, ShieldAlert, Copy, KeyRound } from "lucide-react";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import { useQuery, stamp } from "../lib/hooks";
import {
  PageHeading,
  Panel,
  Table,
  Badge,
  FieldsForm,
  Loading,
  ErrorState,
  Button,
  Alert,
} from "../components/ui";
import type { AuditEvent, AccessInput } from "../lib/types";
import { useState } from "react";

export function MyAccess() {
  const { session } = useAuth();
  const s = session!;
  return (
    <>
      <PageHeading
        eyebrow="YOUR WORKSPACE"
        title="My access"
        description="Your active roles and the resource permissions they provide."
        action={
          s.category !== "auditor" && (
            <Link to="/request" className="btn btn-primary">
              <KeyRound size={16} />
              Request access
            </Link>
          )
        }
      />
      <Panel
        title="Assigned roles"
        description="Permissions from multiple active roles are combined."
      >
        <Table
          headers={["Role", "Description", "Category"]}
          count={s.roles.length}
          empty="No active roles assigned."
        >
          {s.roles.map((r) => (
            <tr key={r.id}>
              <td>
                <strong>{r.name}</strong>
              </td>
              <td>{r.description}</td>
              <td className="capitalize">{r.kind}</td>
            </tr>
          ))}
        </Table>
      </Panel>
      <Panel
        title="Effective resource permissions"
        description="Your account and the resource must also be active."
        className="mt-6"
      >
        <Table
          headers={["Resource type", "Permitted operation"]}
          count={s.permissions.length}
          empty="No resource permissions assigned."
        >
          {s.permissions.map((p) => (
            <tr key={`${p.action}:${p.resource_type}`}>
              <td className="capitalize">{p.resource_type}</td>
              <td className="action-cell">{p.action}</td>
            </tr>
          ))}
        </Table>
      </Panel>
      {s.category === "auditor" && (
        <p className="section-note">
          The Auditor category provides read-only access to investigation
          reports and policy history.
        </p>
      )}
    </>
  );
}
export function Account() {
  const { session } = useAuth();
  const s = session!;
  return (
    <>
      <PageHeading
        eyebrow="YOUR WORKSPACE"
        title="Account"
        description="Your workspace identity and current session information."
      />
      <Panel title="Account details" className="narrow-panel">
        <dl className="detail-list">
          {[
            ["Full name", s.user.name],
            ["Email address", s.user.email],
            [
              "Workspace category",
              s.category === "admin" ? "Administrator" : s.category,
            ],
            ["Active roles", s.roles.map((r) => r.name).join(", ") || "None"],
            ["Account created (UTC)", stamp(s.user.created_at)],
            ["Session expires (UTC)", stamp(s.expires_at)],
          ].map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
          <div>
            <dt>Account status</dt>
            <dd>
              <Badge value={s.user.active} />
            </dd>
          </div>
        </dl>
        <div className="panel-footer">
          Contact an administrator to change account details or role
          assignments.
        </div>
      </Panel>
    </>
  );
}
export function RequestAccess() {
  const { session } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const attempt = useRef<{ signature: string; id: string } | null>(null);
  return (
    <>
      <PageHeading
        eyebrow="YOUR WORKSPACE"
        title="Request access"
        description="Check whether your roles permit an operation on a registered resource."
      />
      <div className="request-grid">
        <Panel
          title="New access request"
          description="Choose a resource and the operation you want to perform."
        >
          <FieldsForm
            initial={{
              resource_id: params.get("resource") || "",
              action: "READ",
            }}
            fields={[
              {
                name: "resource_id",
                label: "Resource",
                collection: "resources",
              },
              {
                name: "action",
                label: "Operation",
                options: [
                  ["READ", "Read — view information"],
                  ["CREATE", "Create — add information"],
                  ["UPDATE", "Update — modify information"],
                  ["DELETE", "Delete — remove information"],
                ],
              },
            ]}
            submitLabel="Evaluate access"
            footer={
              <p className="form-help">
                This checks access only. It does not change the resource itself.
              </p>
            }
            onSubmit={async (values) => {
              const signature = `${values.resource_id}:${values.action}`;
              if (attempt.current?.signature !== signature)
                attempt.current = { signature, id: crypto.randomUUID() };
              const payload: AccessInput = {
                action: values.action as AccessInput["action"],
                resource_id: Number(values.resource_id),
                request_id: attempt.current!.id,
              };
              const event = await api<AuditEvent>("/access", {
                method: "POST",
                body: payload,
                csrf: session!.csrf_token,
              });
              navigate(`/events/${event.id}`);
            }}
          />
        </Panel>
        <aside className="request-note">
          <ShieldAlert size={22} />
          <h2>How decisions work</h2>
          <p>
            Your account, the resource, and at least one assigned role must be
            active.
          </p>
          <p>
            A matching permission allows the request. All other requests are
            denied.
          </p>
          <p>
            Each completed evaluation is saved in your access history with its
            outcome and time.
          </p>
          <Link className="text-link" to="/my-access">
            Review my permissions
          </Link>
        </aside>
      </div>
    </>
  );
}
export function EventDetail() {
  const { id } = useParams();
  const { session } = useAuth();
  const {
    data: event,
    loading,
    error,
    refresh,
  } = useQuery<AuditEvent>(`/events/${id}`);
  const [copied, setCopied] = useState("");
  if (loading) return <Loading label="Loading access decision…" />;
  if (error || !event) return <ErrorState message={error} retry={refresh} />;
  const allowed = event.decision === "ALLOWED";
  const reasons: Record<string, string> = {
    ALLOWED_BY_ROLE:
      "An active role permitted this operation at the time of the request.",
    NO_MATCHING_PERMISSION:
      "No active role grants this operation. Contact an administrator if you need access.",
    INACTIVE_ACCOUNT: "This account is inactive. Contact an administrator.",
    INACTIVE_RESOURCE:
      "This resource is inactive. Contact an administrator to check its availability.",
    RESOURCE_NOT_FOUND: "The selected resource could not be found.",
  };
  return (
    <>
      <PageHeading
        eyebrow="RECORDED ACCESS DECISION"
        title={allowed ? "Access allowed" : "Access denied"}
        description={`${event.action.charAt(0) + event.action.slice(1).toLowerCase()} on ${event.resource_type} ${event.resource_key}`}
        action={
          <Link
            className="btn btn-outline"
            to={session!.category === "auditor" ? "/audit" : "/request"}
          >
            {session!.category === "auditor"
              ? "Back to audit events"
              : "New request"}
          </Link>
        }
      />
      {copied && (
        <Alert
          success={copied === "Request reference copied."}
          onClose={() => setCopied("")}
        >
          {copied}
        </Alert>
      )}
      <Panel className="narrow-panel">
        <div
          className={`decision-summary ${allowed ? "is-allowed" : "is-denied"}`}
        >
          {allowed ? <CircleCheck size={26} /> : <ShieldAlert size={26} />}
          <div>
            <Badge value={event.decision} />
            <p>{reasons[event.reason_code] || event.reason_code}</p>
          </div>
        </div>
        <dl className="detail-list">
          <div>
            <dt>Actor</dt>
            <dd>{event.actor_email}</dd>
          </div>
          <div>
            <dt>Operation</dt>
            <dd>{event.action}</dd>
          </div>
          <div>
            <dt>Resource</dt>
            <dd>
              {event.resource_type} · {event.resource_key}
            </dd>
          </div>
          <div>
            <dt>Recorded (UTC)</dt>
            <dd>{stamp(event.occurred_at)}</dd>
          </div>
          {session!.category !== "user" && (
            <>
              <div>
                <dt>Reason code</dt>
                <dd className="mono">{event.reason_code}</dd>
              </div>
              <div>
                <dt>Matching role at evaluation</dt>
                <dd>{event.matching_role_name || "None"}</dd>
              </div>
            </>
          )}
          <div>
            <dt>Request reference</dt>
            <dd className="reference-value">
              <code>{event.request_id}</code>
              <Button
                variant="ghost"
                aria-label="Copy request reference"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(event.request_id);
                    setCopied("Request reference copied.");
                  } catch {
                    setCopied(
                      "Clipboard is unavailable. Select the reference to copy it.",
                    );
                  }
                }}
              >
                <Copy size={15} />
              </Button>
            </dd>
          </div>
          <div>
            <dt>Event reference</dt>
            <dd className="mono">{event.id}</dd>
          </div>
        </dl>
        <div className="panel-footer">
          This decision is retained when role assignments or permissions change.
        </div>
      </Panel>
      <Link
        className="text-link inline-block mt-6"
        to={session!.category === "user" ? "/history" : "/audit"}
      >
        View access history
      </Link>
    </>
  );
}
