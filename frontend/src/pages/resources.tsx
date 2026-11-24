import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, FileText, FileBarChart } from "lucide-react";
import { useAuth } from "../lib/auth";
import { useQuery } from "../lib/hooks";
import { useActions } from "../lib/actions";
import {
  useListParams,
  Feedback,
  nameSearch,
  statusFilter,
  typeField,
} from "./management";
import {
  PageHeading,
  Button,
  Panel,
  Filters,
  Table,
  Badge,
  Pagination,
  Loading,
  ErrorState,
  Modal,
  FieldsForm,
  useConfirm,
} from "../components/ui";
import type { Page, Resource, ResourceInput } from "../lib/types";
export function Resources() {
  const { session } = useAuth();
  const kind = session!.category;
  const list = useListParams();
  const result = useQuery<Page<Resource>>(`/resources${list.query}`);
  const actions = useActions(result.refresh);
  const confirm = useConfirm();
  const [create, setCreate] = useState(false);
  return (
    <>
      <PageHeading
        eyebrow="RESOURCE REGISTRY"
        title="Resources"
        description="Browse registered resources and their current availability."
        action={
          kind === "admin" && (
            <Button onClick={() => setCreate(true)}>
              <Plus size={16} />
              Register resource
            </Button>
          )
        }
      />
      <Feedback actions={actions} />
      <Panel>
        <Filters
          fields={[
            { ...nameSearch, placeholder: "Search resource name or key…" },
            {
              name: "type",
              label: "Resource type",
              placeholder: "e.g. report",
            },
            statusFilter,
            {
              name: "sort",
              label: "Sort",
              options: [
                ["", "Name A–Z"],
                ["key", "Resource key"],
                ["type", "Resource type"],
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
              headers={["Resource", "Type / key", "Owner", "Status", "Actions"]}
              count={result.data.items.length}
            >
              {result.data.items.map((r) => (
                <tr key={r.id}>
                  <td>
                    <div className="resource-cell">
                      {r.resource_type === "report" ? (
                        <FileBarChart size={18} />
                      ) : (
                        <FileText size={18} />
                      )}
                      <strong>{r.name}</strong>
                    </div>
                  </td>
                  <td>
                    <span className="capitalize">{r.resource_type}</span>
                    <small className="mono">{r.resource_key}</small>
                  </td>
                  <td>{r.owner_name}</td>
                  <td>
                    <Badge value={r.active} />
                  </td>
                  <td>
                    <div className="table-actions">
                      {kind !== "auditor" && (
                        <Link
                          className="text-link"
                          to={`/request?resource=${r.id}`}
                        >
                          Request access
                        </Link>
                      )}
                      {kind === "auditor" && (
                        <Link
                          className="text-link"
                          to={`/audit?resource=${encodeURIComponent(r.resource_key)}`}
                        >
                          View history
                        </Link>
                      )}
                      {kind === "admin" && (
                        <button
                          className={`text-button ${r.active ? "danger-text" : ""}`}
                          disabled={actions.busy}
                          onClick={async () => {
                            if (
                              await confirm(
                                `${r.active ? "Deactivate" : "Activate"} ${r.name}? This changes authorization outcomes immediately.`,
                              )
                            )
                              await actions.run(
                                `/resources/${r.id}/status`,
                                { active: !r.active },
                                "Resource status updated. Policy history recorded.",
                                "PATCH",
                              );
                          }}
                        >
                          {r.active ? "Deactivate" : "Activate"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </Table>
            <Pagination data={result.data} onChange={list.page} />
          </>
        )}
      </Panel>
      <p className="section-note">
        The registry defines authorization targets. Resource content and
        external files are not stored here.
      </p>
      {kind === "admin" && (
        <Modal
          title="Register resource"
          description="Add a uniquely identified target for access evaluations."
          open={create}
          onOpenChange={setCreate}
        >
          <FieldsForm
            fields={[
              {
                name: "name",
                label: "Resource name",
                minLength: 2,
                maxLength: 120,
              },
              { name: "resource_key", label: "Resource key", maxLength: 80 },
              typeField,
              { name: "owner_user_id", label: "Owner", collection: "users" },
            ]}
            submitLabel="Register resource"
            onSubmit={async (values) => {
              await actions.save(
                "/resources",
                values as unknown as ResourceInput,
                "Resource registered. Policy history recorded.",
              );
              setCreate(false);
            }}
          />
        </Modal>
      )}
    </>
  );
}
