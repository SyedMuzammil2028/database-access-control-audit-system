import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import type { ReactNode } from "react";
import { api, ApiError } from "./api";
import type { Session, LoginInput } from "./types";
interface AuthState {
  session: Session | null;
  loading: boolean;
  error: string;
  login: (input: LoginInput) => Promise<Session>;
  logout: () => Promise<void>;
  reload: () => Promise<void>;
}
const AuthContext = createContext<AuthState | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const reload = useCallback(async () => {
    setError("");
    try {
      setSession(await api<Session>("/auth/session"));
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setSession(null);
      else setError(e instanceof Error ? e.message : "Unable to connect.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    void reload();
  }, [reload]);
  useEffect(() => {
    const expired = () => setSession(null);
    window.addEventListener("ledger:session-expired", expired);
    return () => window.removeEventListener("ledger:session-expired", expired);
  }, []);
  async function login(input: LoginInput) {
    const next = await api<Session>("/auth/login", {
      method: "POST",
      body: input,
    });
    setSession(next);
    return next;
  }
  async function logout() {
    await api("/auth/logout", { method: "POST", csrf: session?.csrf_token });
    setSession(null);
  }
  return (
    <AuthContext.Provider
      value={{ session, loading, error, login, logout, reload }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("AuthProvider is missing.");
  return auth;
}
