import * as Dialog from "@radix-ui/react-dialog";
import { createContext, useContext, useId, useState } from "react";
import type { ButtonHTMLAttributes, ReactNode, FormEvent } from "react";
import {
  X,
  LoaderCircle,
  Search,
  CircleCheck,
  CircleAlert,
  ShieldAlert,
  ChevronDown,
} from "lucide-react";
import { ApiError } from "../lib/api";
import { useQuery } from "../lib/hooks";
import type { Options, Page } from "../lib/types";

export function Button({
  variant = "primary",
  className = "",
  children,
  busy,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "outline" | "ghost" | "danger";
  busy?: boolean;
}) {
  return (
    <button
      {...props}
      className={`btn btn-${variant} ${className}`}
      disabled={props.disabled || busy}
      aria-busy={busy || undefined}
    >
      {busy && <LoaderCircle className="animate-spin" size={16} />}
      {children}
    </button>
  );
}
export function IconButton({
  label,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button {...props} aria-label={label} title={label} className="icon-button">
      {children}
    </button>
  );
}
export function Badge({ value }: { value: string | boolean }) {
  const positive =
    value === true || value === "ALLOWED" || value === "LOGIN_SUCCESS";
  const negative = value === "DENIED" || value === "LOGIN_FAILED";
  return (
    <span
      className={`badge ${positive ? "badge-success" : negative ? "badge-danger" : ""}`}
    >
      {typeof value === "boolean"
        ? value
          ? "Active"
          : "Inactive"
        : value.replaceAll("_", " ")}
    </span>
  );
}
export function Alert({
  children,
  success = false,
  onClose,
}: {
  children: ReactNode;
  success?: boolean;
  onClose?: () => void;
}) {
  return (
    <div
      className={`alert ${success ? "alert-success" : "alert-danger"}`}
      role={success ? "status" : "alert"}
    >
      {success ? <CircleCheck size={17} /> : <CircleAlert size={17} />}
      <span>{children}</span>
      {onClose && (
        <IconButton label="Dismiss notification" onClick={onClose}>
          <X size={16} />
        </IconButton>
      )}
    </div>
  );
}
export function Panel({
  title,
  description,
  action,
  children,
  className = "",
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      {title && (
        <div className="panel-header">
          <div>
            <h2>{title}</h2>
            {description && <p>{description}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}
export function PageHeading({
  title,
  description,
  eyebrow,
  action,
}: {
  title: string;
  description: string;
  eyebrow?: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Loading({ label = "Loading records…" }: { label?: string }) {
  return (
    <div className="empty-state" role="status">
      <LoaderCircle className="animate-spin" size={22} />
      <span>{label}</span>
    </div>
  );
}
export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="empty-state">
      <ShieldAlert size={26} />
      <h2>Unable to load this view</h2>
      <p>{message}</p>
      {retry && (
        <Button variant="outline" onClick={retry}>
          Try again
        </Button>
      )}
    </div>
  );
}
export function Table({
  headers,
  children,
  empty,
  count,
}: {
  headers: string[];
  children: ReactNode;
  empty?: string;
  count: number;
}) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {headers.map((h, i) => (
              <th key={i} scope="col">
                {h || <span className="sr-only">Actions</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {count ? (
            children
          ) : (
            <tr>
              <td colSpan={headers.length}>
                <div className="empty-state">
                  <Search size={23} />
                  <h3>{empty || "No records match your filters."}</h3>
                  <p>
                    Try a different search or check back after new activity.
                  </p>
                </div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
export function Pagination({
  data,
  onChange,
}: {
  data: Pick<Page<unknown>, "page" | "pages" | "total">;
  onChange: (page: number) => void;
}) {
  return (
    <div className="pagination">
      <p>
        {data.total} record{data.total === 1 ? "" : "s"}
        <span>
          Page {data.page} of {data.pages}
        </span>
      </p>
      <div className="flex gap-2">
        <Button
          variant="outline"
          disabled={data.page <= 1}
          onClick={() => onChange(data.page - 1)}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          disabled={data.page >= data.pages}
          onClick={() => onChange(data.page + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
export interface FilterField {
  name: string;
  label: string;
  type?: string;
  options?: [string, string][];
  placeholder?: string;
}
export function Filters({
  fields,
  initial,
  onApply,
}: {
  fields: FilterField[];
  initial: URLSearchParams;
  onApply: (values: Record<string, string>) => void;
}) {
  const prefix = useId();
  return (
    <form
      key={initial.toString()}
      className="filters"
      onSubmit={(event) => {
        event.preventDefault();
        onApply(
          Object.fromEntries(
            new FormData(event.currentTarget).entries(),
          ) as Record<string, string>,
        );
      }}
    >
      {fields.map((f) => (
        <div
          key={f.name}
          className={`filter-field ${f.name === "q" ? "filter-search" : ""}`}
        >
          <label htmlFor={`${prefix}-${f.name}`}>{f.label}</label>
          {f.options ? (
            <select
              id={`${prefix}-${f.name}`}
              name={f.name}
              defaultValue={initial.get(f.name) || ""}
            >
              {f.options.map(([value, label]) => (
                <option value={value} key={value}>
                  {label}
                </option>
              ))}
            </select>
          ) : (
            <input
              id={`${prefix}-${f.name}`}
              type={f.type || "text"}
              name={f.name}
              defaultValue={initial.get(f.name) || ""}
              placeholder={f.placeholder}
              maxLength={f.type === "date" ? undefined : 200}
            />
          )}
        </div>
      ))}
      <div className="filter-actions">
        <Button type="submit" variant="outline">
          Apply filters
        </Button>
        <Button type="button" variant="ghost" onClick={() => onApply({})}>
          Reset
        </Button>
      </div>
    </form>
  );
}

export interface Field {
  name: string;
  label: string;
  type?: string;
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  help?: string;
  options?: [string, string][];
  collection?: "users" | "roles" | "resources" | "permissions";
  readOnly?: boolean;
}
export function ReferenceSelect({
  field,
  value,
  onChange,
  error,
}: {
  field: Field;
  value: string;
  onChange: (v: string) => void;
  error?: string;
}) {
  const id = useId();
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const result = useQuery<Options>(
    `/options/${field.collection}?q=${encodeURIComponent(query)}${value ? `&selected_id=${value}` : ""}`,
  );
  return (
    <div className="field">
      <label htmlFor={id}>{field.label}</label>
      <div className="reference-search">
        <input
          aria-label={`Search ${field.label.toLowerCase()}`}
          placeholder={`Search ${field.label.toLowerCase()}…`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          maxLength={200}
        />
        <Button
          type="button"
          variant="outline"
          onClick={() => setQuery(search)}
          aria-label={`Find ${field.label.toLowerCase()}`}
        >
          <Search size={15} />
        </Button>
      </div>
      <select
        id={id}
        name={field.name}
        value={value}
        required={field.required !== false}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
      >
        <option value="">
          {result.loading
            ? "Loading options…"
            : `Select ${field.label.toLowerCase()}`}
        </option>
        {result.data?.items.map((o) => (
          <option key={o.id} value={o.id}>
            {o.label}
            {!o.active ? " (inactive)" : ""}
          </option>
        ))}
      </select>
      {result.error && (
        <span className="field-error">
          {result.error}{" "}
          <button
            type="button"
            className="text-button"
            onClick={result.refresh}
          >
            Retry
          </button>
        </span>
      )}
      {result.data?.has_more && (
        <small>
          Showing the first 50 matches. Search to narrow the selection.
        </small>
      )}
      {error && (
        <span id={`${id}-error`} className="field-error">
          {error}
        </span>
      )}
    </div>
  );
}
export function FieldsForm({
  fields,
  initial = {},
  submitLabel,
  onSubmit,
  footer,
}: {
  fields: Field[];
  initial?: Record<string, string>;
  submitLabel: string;
  onSubmit: (values: Record<string, string | number>) => Promise<void>;
  footer?: ReactNode;
}) {
  const [values, setValues] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const baseId = useId();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setErrors({});
    const raw = Object.fromEntries(new FormData(event.currentTarget).entries());
    const data = Object.fromEntries(
      fields.map((f) => [
        f.name,
        f.collection ? Number(raw[f.name]) : String(raw[f.name] || ""),
      ]),
    );
    try {
      await onSubmit(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save.");
      if (e instanceof ApiError) setErrors(e.fields);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="fields-form" onSubmit={submit}>
      {error && <Alert>{error}</Alert>}
      <fieldset disabled={busy}>
        <div className="form-grid">
          {fields.map((f) => {
            if (f.collection)
              return (
                <ReferenceSelect
                  key={f.name}
                  field={f}
                  value={values[f.name] || ""}
                  onChange={(v) => setValues((s) => ({ ...s, [f.name]: v }))}
                  error={errors[f.name]}
                />
              );
            const id = `${baseId}-${f.name}`;
            return (
              <div className="field" key={f.name}>
                <label htmlFor={id}>{f.label}</label>
                {f.options ? (
                  <select
                    id={id}
                    name={f.name}
                    required={f.required !== false}
                    defaultValue={initial[f.name] || ""}
                  >
                    {!initial[f.name] && (
                      <option value="">Select {f.label.toLowerCase()}</option>
                    )}
                    {f.options.map(([v, l]) => (
                      <option key={v} value={v}>
                        {l}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id={id}
                    name={f.name}
                    type={f.type || "text"}
                    required={f.required !== false}
                    minLength={f.minLength}
                    maxLength={f.maxLength}
                    pattern={f.pattern}
                    defaultValue={initial[f.name] || ""}
                    readOnly={f.readOnly}
                    autoComplete={
                      f.type === "password" ? "new-password" : "off"
                    }
                    aria-invalid={Boolean(errors[f.name])}
                    aria-describedby={
                      errors[f.name]
                        ? `${id}-error`
                        : f.help
                          ? `${id}-help`
                          : undefined
                    }
                  />
                )}
                {f.help && <small id={`${id}-help`}>{f.help}</small>}
                {errors[f.name] && (
                  <span id={`${id}-error`} className="field-error">
                    {errors[f.name]}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </fieldset>
      {footer}
      <div className="form-actions">
        <Button type="submit" busy={busy}>
          {busy ? "Saving…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
export function Modal({
  title,
  description,
  open,
  onOpenChange,
  children,
}: {
  title: string;
  description: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <div className="dialog-heading">
            <div>
              <Dialog.Title>{title}</Dialog.Title>
              <Dialog.Description>{description}</Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <IconButton label="Close dialog">
                <X size={18} />
              </IconButton>
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

type Confirm = (message: string) => Promise<boolean>;
const ConfirmContext = createContext<Confirm>(() => Promise.resolve(false));
export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [pending, setPending] = useState<{
    message: string;
    resolve: (value: boolean) => void;
  } | null>(null);
  const confirm: Confirm = (message) =>
    new Promise((resolve) => {
      setPending((previous) => {
        previous?.resolve(false);
        return { message, resolve };
      });
    });
  const close = (accepted: boolean) => {
    pending?.resolve(accepted);
    setPending(null);
  };
  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <Dialog.Root
        open={Boolean(pending)}
        onOpenChange={(open) => {
          if (!open) close(false);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content
            className="dialog-content confirm-content"
            onOpenAutoFocus={(e) => {
              e.preventDefault();
              document.getElementById("confirm-cancel")?.focus();
            }}
          >
            <div className="confirm-icon">
              <ShieldAlert size={22} />
            </div>
            <Dialog.Title>Confirm policy change</Dialog.Title>
            <Dialog.Description>{pending?.message}</Dialog.Description>
            <div className="dialog-actions">
              <Button
                id="confirm-cancel"
                variant="outline"
                onClick={() => close(false)}
              >
                Cancel
              </Button>
              <Button variant="danger" onClick={() => close(true)}>
                Confirm change
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </ConfirmContext.Provider>
  );
}
export const useConfirm = () => useContext(ConfirmContext);
export { Dialog, ChevronDown };
