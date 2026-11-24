import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Plus, RefreshCw, Pencil, Link2, UserPlus } from "lucide-react";
import { useQuery } from "../lib/hooks";
import { queryString } from "../lib/api";
import { useActions } from "../lib/actions";
import { stamp } from "../lib/hooks";
import {
  PageHeading,
  Panel,
  Button,
  Badge,
  Filters,
  Table,
  Pagination,
  Modal,
  FieldsForm,
  Loading,
  ErrorState,
  Alert,
  useConfirm,
} from "../components/ui";
import type { Field, FilterField } from "../components/ui";
import type {
  Page,
  User,
  Role,
  Assignment,
  Permission,
  Mapping,
  UserInput,
  RoleInput,
  AssignmentInput,
  PermissionInput,
  MappingInput,
} from "../lib/types";

export function useListParams() {
  const [params, setParams] = useSearchParams();
  return {
    params,
    query: params.toString() ? `?${params}` : "",
    apply: (values: Record<string, string>) =>
      setParams(
        Object.fromEntries(Object.entries(values).filter(([, v]) => v)),
      ),
    page: (page: number) => {
      const next = new URLSearchParams(params);
      next.set("page", String(page));
      setParams(next);
    },
  };
}
export function Feedback({
  actions,
}: {
  actions: ReturnType<typeof useActions>;
}) {
  return (
    <>
      {actions.error && (
        <Alert onClose={actions.clearError}>{actions.error}</Alert>
      )}
      {actions.success && (
        <Alert success onClose={actions.clearSuccess}>
          {actions.success}
        </Alert>
      )}
    </>
  );
}
export const nameSearch: FilterField = {
  name: "q",
  label: "Search",
  placeholder: "Search name or email…",
};
export const statusFilter: FilterField = {
  name: "status",
  label: "Status",
  options: [
    ["", "All statuses"],
    ["active", "Active"],
    ["inactive", "Inactive"],
  ],
};
export const typeField: Field = {
  name: "resource_type",
  label: "Resource type",
  pattern: "[a-z][a-z0-9_]{0,39}",
  maxLength: 40,
  help: "Lowercase letters, numbers and underscores; start with a letter.",
};
const roleFields: Field[] = [
  { name: "name", label: "Role name", minLength: 2, maxLength: 60 },
  {
    name: "description",
    label: "Description",
    required: false,
    maxLength: 300,
  },
];
const userFields: Field[] = [
  { name: "name", label: "Full name", minLength: 2, maxLength: 100 },
  { name: "email", label: "Email address", type: "email", maxLength: 254 },
  {
    name: "password",
    label: "Initial password",
    type: "password",
    minLength: 12,
    maxLength: 128,
    help: "At least 12 characters. Share securely with the user.",
  },
];
export const actionOptions: [string, string][] = [
  "READ",
  "CREATE",
  "UPDATE",
  "DELETE",
].map((a) => [a, a]);

export function Users() {
  const list = useListParams();
  const result = useQuery<Page<User>>(`/users${list.query}`);
  const actions = useActions(result.refresh);
  const confirm = useConfirm();
  const [create, setCreate] = useState(list.params.get("create") === "1");
  return (
    <>
      <PageHeading
        eyebrow="IDENTITY MANAGEMENT"
        title="Users"
        description="Manage workspace accounts and control who can sign in."
        action={
          <Button onClick={() => setCreate(true)}>
            <Plus size={16} />
            Create user
          </Button>
        }
      />
      <Feedback actions={actions} />
      <Panel>
        <Filters
          fields={[
            nameSearch,
            statusFilter,
            {
              name: "sort",
              label: "Sort",
              options: [
                ["", "Name A–Z"],
                ["email", "Email A–Z"],
                ["newest", "Newest first"],
              ],
            },
          ]}
          initial={list.params}
          onApply={list.apply}
        />
        {result.loading ? (
          <Loading />
        ) : result.error || !result.data ? (
          <ErrorState message={result.error} retry={result.refresh} />
        ) : (
          <>
            <Table
              headers={[
                "User",
                "Assigned roles",
                "Status",
                "Created (UTC)",
                "Account action",
              ]}
              count={result.data.items.length}
            >
              {result.data.items.map((u) => (
                <tr key={u.id}>
                  <td>
                    <div className="identity-cell">
                      <span className="avatar square">
                        {u.name
                          .split(" ")
                          .map((n) => n[0])
                          .slice(0, 2)
                          .join("")}
                      </span>
                      <div>
                        <strong>{u.name}</strong>
                        <small>{u.email}</small>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div className="tags">
                      {u.roles.map((r) => (
                        <span className="tag" key={r.id}>
                          {r.name}
                        </span>
                      ))}
                      {!u.roles.length && (
                        <span className="muted">No active roles</span>
                      )}
                    </div>
                  </td>
                  <td>
                    <Badge value={u.active} />
                  </td>
                  <td className="muted nowrap">{stamp(u.created_at)}</td>
                  <td>
                    <button
                      className={`text-button ${u.active ? "danger-text" : ""}`}
                      disabled={actions.busy}
                      onClick={async () => {
                        if (
                          await confirm(
                            `${u.active ? "Deactivate" : "Activate"} ${u.name}? This changes their access immediately.`,
                          )
                        )
                          await actions.run(
                            `/users/${u.id}/status`,
                            { active: !u.active },
                            "Account status updated. Policy history recorded.",
                            "PATCH",
                          );
                      }}
                    >
                      {u.active ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                </tr>
              ))}
            </Table>
            <Pagination data={result.data} onChange={list.page} />
          </>
        )}
      </Panel>
      <Modal
        title="Create user"
        description="Create an account, then assign its roles from Role assignments."
        open={create}
        onOpenChange={setCreate}
      >
        <FieldsForm
          fields={userFields}
          submitLabel="Create account"
          onSubmit={async (values) => {
            await actions.save(
              "/users",
              values as unknown as UserInput,
              "Account created. Assign a role to provide access.",
            );
            setCreate(false);
          }}
        />
      </Modal>
    </>
  );
}
export function Roles() {
  const list = useListParams();
  const result = useQuery<Page<Role>>(`/roles${list.query}`);
  const actions = useActions(result.refresh);
  const confirm = useConfirm();
  const [create, setCreate] = useState(false);
  const [editing, setEditing] = useState<Role | null>(null);
  return (
    <>
      <PageHeading
        eyebrow="ACCESS POLICY"
        title="Roles"
        description="Group permissions into clear, reusable responsibilities."
        action={
          <Button onClick={() => setCreate(true)}>
            <Plus size={16} />
            Create role
          </Button>
        }
      />
      <Feedback actions={actions} />
      <Panel>
        <Filters
          fields={[
            { name: "q", label: "Search", placeholder: "Search role name…" },
            statusFilter,
            {
              name: "sort",
              label: "Sort",
              options: [
                ["", "Name A–Z"],
                ["category", "Category"],
              ],
            },
          ]}
          initial={list.params}
          onApply={list.apply}
        />
        {result.loading ? (
          <Loading />
        ) : result.error || !result.data ? (
          <ErrorState message={result.error} retry={result.refresh} />
        ) : (
          <>
            <Table
              headers={[
                "Role",
                "Category",
                "Members",
                "Permissions",
                "Status",
                "Actions",
              ]}
              count={result.data.items.length}
            >
              {result.data.items.map((r) => (
                <tr key={r.id}>
                  <td>
                    <strong>{r.name}</strong>
                    <small>{r.description}</small>
                  </td>
                  <td className="capitalize">
                    {r.kind === "admin" ? "Administrator" : r.kind}
                  </td>
                  <td>{r.member_count}</td>
                  <td>{r.permission_count}</td>
                  <td>
                    <Badge value={r.active} />
                  </td>
                  <td>
                    <div className="table-actions">
                      <button
                        className="text-button"
                        onClick={() => setEditing(r)}
                      >
                        <Pencil size={14} />
                        Edit
                      </button>
                      <button
                        className={`text-button ${r.active ? "danger-text" : ""}`}
                        disabled={actions.busy}
                        onClick={async () => {
                          if (
                            await confirm(
                              `${r.active ? "Deactivate" : "Activate"} ${r.name}? This affects all members of the role.`,
                            )
                          )
                            await actions.run(
                              `/roles/${r.id}/status`,
                              { active: !r.active },
                              "Role status updated. Policy history recorded.",
                              "PATCH",
                            );
                        }}
                      >
                        {r.active ? "Deactivate" : "Activate"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </Table>
            <Pagination data={result.data} onChange={list.page} />
          </>
        )}
      </Panel>
      <Modal
        title="Create role"
        description="Custom roles provide resource permissions. Administrator and Auditor are system categories."
        open={create}
        onOpenChange={setCreate}
      >
        <FieldsForm
          fields={roleFields}
          submitLabel="Create role"
          onSubmit={async (values) => {
            await actions.save(
              "/roles",
              values as unknown as RoleInput,
              "Role created. Map permissions to define its access.",
            );
            setCreate(false);
          }}
        />
      </Modal>
      <Modal
        title="Edit role"
        description="Update the role name and description. System role names are protected."
        open={Boolean(editing)}
        onOpenChange={(open) => {
          if (!open) setEditing(null);
        }}
      >
        {editing && (
          <FieldsForm
            key={editing.id}
            initial={{ name: editing.name, description: editing.description }}
            fields={roleFields.map((f) => ({
              ...f,
              readOnly: f.name === "name" && editing.kind !== "user",
            }))}
            submitLabel="Save changes"
            onSubmit={async (values) => {
              await actions.save(
                `/roles/${editing.id}`,
                values as unknown as RoleInput,
                "Role updated. Policy history recorded.",
                "PUT",
              );
              setEditing(null);
            }}
          />
        )}
      </Modal>
    </>
  );
}
export function Assignments() {
  const list = useListParams();
  const result = useQuery<Page<Assignment>>(`/assignments${list.query}`);
  const actions = useActions(result.refresh);
  const confirm = useConfirm();
  const [create, setCreate] = useState(false);
  return (
    <>
      <PageHeading
        eyebrow="ACCESS POLICY"
        title="Role assignments"
        description="Manage who receives access. Every assignment and revocation is recorded."
        action={
          <Button onClick={() => setCreate(true)}>
            <UserPlus size={16} />
            Assign role
          </Button>
        }
      />
      <Feedback actions={actions} />
      <Panel>
        <Filters
          fields={[
            { name: "q", label: "Search", placeholder: "Search user or role…" },
            statusFilter,
          ]}
          initial={list.params}
          onApply={list.apply}
        />
        {result.loading ? (
          <Loading />
        ) : result.error || !result.data ? (
          <ErrorState message={result.error} retry={result.refresh} />
        ) : (
          <>
            <Table
              headers={[
                "User",
                "Role",
                "Assigned (UTC)",
                "Assignment",
                "Action",
              ]}
              count={result.data.items.length}
            >
              {result.data.items.map((a) => (
                <tr key={`${a.user_id}:${a.role_id}`}>
                  <td>
                    <strong>{a.user_name}</strong>
                    <small>{a.user_email}</small>
                  </td>
                  <td>
                    {a.role_name}
                    {!a.role_active && <small>Role inactive</small>}
                  </td>
                  <td className="muted nowrap">{stamp(a.assigned_at)}</td>
                  <td>
                    <Badge value={a.active} />
                  </td>
                  <td>
                    {a.active ? (
                      <button
                        className="text-button danger-text"
                        disabled={actions.busy}
                        onClick={async () => {
                          if (
                            await confirm(
                              `Revoke ${a.role_name} from ${a.user_name}? Access provided by this role ends immediately.`,
                            )
                          )
                            await actions.run(
                              `/assignments/${a.user_id}/${a.role_id}`,
                              undefined,
                              "Role revoked. Policy history recorded.",
                              "DELETE",
                            );
                        }}
                      >
                        Revoke role
                      </button>
                    ) : (
                      <span className="muted">Revoked</span>
                    )}
                  </td>
                </tr>
              ))}
            </Table>
            <Pagination data={result.data} onChange={list.page} />
          </>
        )}
      </Panel>
      <Modal
        title="Assign role"
        description="The account and role must be active. Permissions take effect immediately."
        open={create}
        onOpenChange={setCreate}
      >
        <FieldsForm
          fields={[
            { name: "user_id", label: "User", collection: "users" },
            { name: "role_id", label: "Role", collection: "roles" },
          ]}
          submitLabel="Assign role"
          onSubmit={async (values) => {
            if (
              !(await confirm(
                "Assign this role? The selected user will immediately receive its active permissions.",
              ))
            )
              return;
            await actions.save(
              "/assignments",
              values as unknown as AssignmentInput,
              "Role assigned. Policy history recorded.",
            );
            setCreate(false);
          }}
        />
      </Modal>
    </>
  );
}
export function Permissions() {
  const list = useListParams();
  const catalog = list.params.get("view") === "catalog";
  const result = useQuery<Page<Mapping | Permission>>(
    `/${catalog ? "permissions" : "mappings"}${list.query}`,
  );
  const actions = useActions(result.refresh);
  const confirm = useConfirm();
  const [create, setCreate] = useState(false);
  const [map, setMap] = useState(false);
  return (
    <>
      <PageHeading
        eyebrow="ACCESS POLICY"
        title="Permissions"
        description="Define resource operations and map them to roles. No mapping means no access."
        action={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setCreate(true)}>
              <Plus size={16} />
              Define permission
            </Button>
            <Button onClick={() => setMap(true)}>
              <Link2 size={16} />
              Map permission
            </Button>
          </div>
        }
      />
      <Feedback actions={actions} />
      <div className="tabs" role="group" aria-label="Permission view">
        <button
          className={!catalog ? "active" : ""}
          onClick={() => list.apply({ view: "mappings" })}
        >
          Role mappings
        </button>
        <button
          className={catalog ? "active" : ""}
          onClick={() => list.apply({ view: "catalog" })}
        >
          Permission catalog
        </button>
      </div>
      <Panel>
        <Filters
          fields={[
            {
              name: "q",
              label: "Search",
              placeholder: catalog
                ? "Search action or resource type…"
                : "Search role or resource type…",
            },
          ]}
          initial={list.params}
          onApply={(values) =>
            list.apply({ ...values, view: catalog ? "catalog" : "mappings" })
          }
        />
        {result.loading ? (
          <Loading />
        ) : result.error || !result.data ? (
          <ErrorState message={result.error} retry={result.refresh} />
        ) : (
          <>
            <Table
              headers={
                catalog
                  ? ["Permission ID", "Action", "Resource type"]
                  : ["Role", "Action", "Resource type", "Action"]
              }
              count={result.data.items.length}
            >
              {result.data.items.map((record) =>
                catalog ? (
                  <tr key={(record as Permission).id}>
                    <td className="mono muted">{(record as Permission).id}</td>
                    <td className="action-cell">{record.action}</td>
                    <td>{record.resource_type}</td>
                  </tr>
                ) : (
                  <MappingTableRow
                    key={`${(record as Mapping).role_id}:${(record as Mapping).permission_id}`}
                    mapping={record as Mapping}
                    busy={actions.busy}
                    onRemove={async (m) => {
                      if (
                        await confirm(
                          `Remove ${m.action} on ${m.resource_type} from ${m.role_name}? Members lose access provided by this mapping.`,
                        )
                      )
                        await actions.run(
                          `/mappings/${m.role_id}/${m.permission_id}`,
                          undefined,
                          "Mapping removed. Policy history recorded.",
                          "DELETE",
                        );
                    }}
                  />
                ),
              )}
            </Table>
            <Pagination data={result.data} onChange={list.page} />
          </>
        )}
      </Panel>
      <Modal
        title="Define permission"
        description="Each action and resource type combination is unique."
        open={create}
        onOpenChange={setCreate}
      >
        <FieldsForm
          fields={[
            { name: "action", label: "Action", options: actionOptions },
            typeField,
          ]}
          submitLabel="Create permission"
          onSubmit={async (values) => {
            await actions.save(
              "/permissions",
              values as unknown as PermissionInput,
              "Permission created. It can now be mapped to a role.",
            );
            setCreate(false);
          }}
        />
      </Modal>
      <Modal
        title="Map permission"
        description="Give a role permission to perform an operation on a resource type."
        open={map}
        onOpenChange={setMap}
      >
        <FieldsForm
          fields={[
            { name: "role_id", label: "Role", collection: "roles" },
            {
              name: "permission_id",
              label: "Permission",
              collection: "permissions",
            },
          ]}
          submitLabel="Map permission"
          onSubmit={async (values) => {
            if (
              !(await confirm(
                "Map this permission? All active members of this role receive the access.",
              ))
            )
              return;
            await actions.save(
              "/mappings",
              values as unknown as MappingInput,
              "Permission mapped. Policy history recorded.",
            );
            setMap(false);
          }}
        />
      </Modal>
    </>
  );
}
function MappingTableRow({
  mapping: m,
  busy,
  onRemove,
}: {
  mapping: Mapping;
  busy: boolean;
  onRemove: (m: Mapping) => Promise<void>;
}) {
  return (
    <tr>
      <td>
        <strong>{m.role_name}</strong>
      </td>
      <td className="action-cell">{m.action}</td>
      <td>{m.resource_type}</td>
      <td>
        <button
          className="text-button danger-text"
          disabled={busy}
          onClick={() => void onRemove(m)}
        >
          Remove mapping
        </button>
      </td>
    </tr>
  );
}
