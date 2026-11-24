export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public fields: Record<string, string> = {},
  ) {
    super(message);
  }
}
export async function failure(response: Response): Promise<never> {
  const error = await response
    .json()
    .catch(() => ({ message: "The server could not complete this request." }));
  const fields: Record<string, string> = {};
  for (const field of error.errors || []) fields[field.field] = field.message;
  if (response.status === 401)
    window.dispatchEvent(new Event("ledger:session-expired"));
  throw new ApiError(
    response.status,
    error.message || "Please try again.",
    fields,
  );
}
export async function api<T>(
  path: string,
  options: {
    method?: string;
    body?: unknown;
    csrf?: string;
    signal?: AbortSignal;
  } = {},
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: options.method || "GET",
    credentials: "same-origin",
    signal: options.signal,
    headers: {
      Accept: "application/json",
      ...(options.body !== undefined
        ? { "Content-Type": "application/json" }
        : {}),
      ...(options.csrf ? { "X-CSRF-Token": options.csrf } : {}),
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) return failure(response);
  return response.json();
}
export function queryString(
  values: Record<string, string | number | undefined>,
): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values))
    if (value !== undefined && value !== "") params.set(key, String(value));
  const query = params.toString();
  return query ? `?${query}` : "";
}
export async function downloadCsv(query: string) {
  const response = await fetch(`/api/audit/export${query}`, {
    credentials: "same-origin",
  });
  if (!response.ok) return failure(response);
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = "access-audit.csv";
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
