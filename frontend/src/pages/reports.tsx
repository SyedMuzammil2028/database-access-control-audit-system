import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Download, RefreshCw } from "lucide-react";
import { useQuery, stamp, actionLabel } from "../lib/hooks";
import { downloadCsv } from "../lib/api";
import { useListParams } from "./management";
import {
  PageHeading,
  Panel,
  Filters,
  Table,
  Pagination,
  Badge,
  Loading,
  ErrorState,
  Button,
  Alert,
  Modal,
} from "../components/ui";
import type { FilterField } from "../components/ui";
import type {
  AuditEvent,
  Page,
  PolicyChange,
  SecurityEvent,
  Options,
} from "../lib/types";
const search: FilterField = {
  name: "q",
  label: "Search",
  placeholder: "Actor email or resource key…",
};
const dates: FilterField[] = [
  { name: "start", label: "From (UTC)", type: "date" },
  { name: "end", label: "Through (UTC)", type: "date" },
];
function InvestigationFilters({
  fields,
  params,
  apply,
}: {
  fields: FilterField[];
  params: URLSearchParams;
  apply: (values: Record<string, string>) => void;
}) {
  const { data } = useQuery<Options>(
    `/options/users${params.get("actor") ? `?selected_id=${params.get("actor")}` : ""}`,
  );
  return (
    <Filters
      fields={[
        fields[0],
        {
          name: "actor",
          label: "Actor",
          options: [
            ["", "All actors"],
            ...(data?.items.map(
              (o) => [String(o.id), o.label] as [string, string],
            ) || []),
          ],
        },
        ...fields.slice(1),
      ]}
      initial={params}
      onApply={apply}
    />
  );
}
export function AuditEvents() {
  const personal = useLocation().pathname === "/history";
  const list = useListParams();
  const result = useQuery<Page<AuditEvent>>(
    `/${personal ? "history" : "audit"}${list.query}`,
  );
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const fields: FilterField[] = [
    search,
    {
      name: "action",
      label: "Action",
      options: [
        ["", "All actions"],
        ...["READ", "CREATE", "UPDATE", "DELETE"].map(
          (a) => [a, a] as [string, string],
        ),
      ],
    },
    {
      name: "decision",
      label: "Decision",
      options: [
        ["", "All decisions"],
        ["ALLOWED", "Allowed"],
        ["DENIED", "Denied"],
      ],
    },
    { name: "resource", label: "Resource key", placeholder: "e.g. R42" },
    ...dates,
    {
      name: "sort",
      label: "Sort",
      options: [
        ["", "Newest first"],
        ["oldest", "Oldest first"],
        ["actor", "Actor A–Z"],
        ["action", "Action A–Z"],
      ],
    },
  ];
  return (
    <>
      <PageHeading
        eyebrow={personal ? "YOUR WORKSPACE" : "INVESTIGATION"}
        title={personal ? "My access history" : "Audit events"}
        description="Search recorded decisions and inspect the policy result at the time of access."
        action={
          !personal && (
            <Button
              variant="outline"
              busy={exporting}
              onClick={async () => {
                setExporting(true);
                setError("");
                try {
                  await downloadCsv(list.query);
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Export failed.");
                } finally {
                  setExporting(false);
                }
              }}
            >
              <Download size={16} />
              {exporting ? "Exporting…" : "Export CSV"}
            </Button>
          )
        }
      />
      {error && <Alert onClose={() => setError("")}>{error}</Alert>}
      <Panel>
        {personal ? (
          <Filters fields={fields} initial={list.params} onApply={list.apply} />
        ) : (
          <InvestigationFilters
            fields={fields}
            params={list.params}
            apply={list.apply}
          />
        )}
        {!personal && (
          <div className="filter-note">
            Apply a date range before exporting. CSV supports up to 93 days and
            5,000 matching events.
          </div>
        )}
        {result.loading ? (
          <Loading />
        ) : result.error || !result.data ? (
          <ErrorState message={result.error} retry={result.refresh} />
        ) : (
          <>
            <Table
              headers={[
                "Time (UTC)",
                "Actor",
                "Action",
                "Resource",
                "Decision",
                "Reason",
                "",
              ]}
              count={result.data.items.length}
              empty="No access decisions match your filters."
            >
              {result.data.items.map((e) => (
                <tr key={e.id}>
                  <td className="muted nowrap">{stamp(e.occurred_at)}</td>
                  <td>{e.actor_email}</td>
                  <td className="action-cell">{e.action}</td>
                  <td>
                    <strong>{e.resource_key}</strong>
                    <small>{e.resource_type}</small>
                  </td>
                  <td>
                    <Badge value={e.decision} />
                  </td>
                  <td className="reason-cell">{actionLabel(e.reason_code)}</td>
                  <td>
                    <Link className="text-link" to={`/events/${e.id}`}>
                      Details
                    </Link>
                  </td>
                </tr>
              ))}
            </Table>
            <Pagination data={result.data} onChange={list.page} />
          </>
        )}
      </Panel>
    </>
  );
}
export function PolicyHistory() {
  const list = useListParams();
  const result = useQuery<Page<PolicyChange>>(`/policy${list.query}`);
  const [selected, setSelected] = useState<PolicyChange | null>(null);
  return (
    <>
      <PageHeading
        eyebrow="INVESTIGATION"
        title="Policy history"
        description="Trace administrative changes and inspect their recorded details."
      />
      <Panel>
        <InvestigationFilters
          fields={[
            {
              name: "q",
              label: "Search",
              placeholder: "Administrator email or operation…",
            },
            ...dates,
          ]}
          params={list.params}
          apply={list.apply}
        />
        {result.loading ? (
          <Loading />
        ) : result.error || !result.data ? (
          <ErrorState message={result.error} retry={result.refresh} />
        ) : (
          <>
            <Table
              headers={[
                "Time (UTC)",
                "Administrator",
                "Operation",
                "Target",
                "Details",
              ]}
              count={result.data.items.length}
            >
              {result.data.items.map((p) => (
                <tr key={p.id}>
                  <td className="muted nowrap">{stamp(p.occurred_at)}</td>
                  <td>{p.actor_email}</td>
                  <td>{actionLabel(p.operation)}</td>
                  <td className="mono">
                    {p.target_type}
                    <small>{p.target_id}</small>
                  </td>
                  <td>
                    <button
                      className="text-button"
                      onClick={() => setSelected(p)}
                    >
                      Inspect change
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
        title={selected ? actionLabel(selected.operation) : "Policy change"}
        description="Historical details recorded in the same transaction as the policy update."
        open={Boolean(selected)}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      >
        {selected && (
          <div className="policy-detail">
            <dl className="detail-list">
              <div>
                <dt>Administrator</dt>
                <dd>{selected.actor_email}</dd>
              </div>
              <div>
                <dt>Time (UTC)</dt>
                <dd>{stamp(selected.occurred_at)}</dd>
              </div>
              <div>
                <dt>Target</dt>
                <dd className="mono">
                  {selected.target_type} / {selected.target_id}
                </dd>
              </div>
            </dl>
            <h3>Recorded change</h3>
            <pre>{JSON.stringify(selected.details, null, 2)}</pre>
            <p className="mono muted">Request {selected.request_id}</p>
          </div>
        )}
      </Modal>
    </>
  );
}
export function SignInActivity() {
  const list = useListParams();
  const result = useQuery<Page<SecurityEvent>>(`/security${list.query}`);
  return (
    <>
      <PageHeading
        eyebrow="INVESTIGATION"
        title="Sign-in activity"
        description="Authentication events with server timestamps and request references."
        action={
          <Button
            variant="outline"
            onClick={result.refresh}
            disabled={result.loading}
          >
            <RefreshCw size={15} />
            Refresh
          </Button>
        }
      />
      <Panel>
        <Filters
          fields={[
            { name: "q", label: "Search", placeholder: "Search email…" },
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
              headers={["Time (UTC)", "Email", "Event", "Request reference"]}
              count={result.data.items.length}
            >
              {result.data.items.map((e) => (
                <tr key={e.id}>
                  <td className="muted nowrap">{stamp(e.occurred_at)}</td>
                  <td>{e.email}</td>
                  <td>
                    <Badge value={e.operation} />
                  </td>
                  <td className="mono">{e.request_id}</td>
                </tr>
              ))}
            </Table>
            <Pagination data={result.data} onChange={list.page} />
          </>
        )}
      </Panel>
    </>
  );
}
