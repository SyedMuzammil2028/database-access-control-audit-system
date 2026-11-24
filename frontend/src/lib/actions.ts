import { useState } from "react";
import { useAuth } from "./auth";
import { api } from "./api";
export function useActions(refresh: () => void) {
  const auth = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  async function save<T = unknown>(
    path: string,
    body: unknown,
    message: string,
    method = "POST",
  ): Promise<T> {
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const result = await api<T>(path, {
        method,
        body,
        csrf: auth.session!.csrf_token,
      });
      setSuccess(message);
      refresh();
      await auth.reload();
      return result;
    } finally {
      setBusy(false);
    }
  }
  async function run(
    path: string,
    body: unknown,
    message: string,
    method = "POST",
  ) {
    try {
      await save(path, body, message, method);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save.");
    }
  }
  return {
    busy,
    error,
    success,
    save,
    run,
    clearError: () => setError(""),
    clearSuccess: () => setSuccess(""),
  };
}
