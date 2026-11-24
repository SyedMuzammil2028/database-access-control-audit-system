import { useEffect, useState } from "react";
import { Navigate, useNavigate, useLocation } from "react-router-dom";
import { ShieldCheck, KeyRound, Database, Eye, EyeOff } from "lucide-react";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import { Brand, ThemeToggle } from "../components/shell";
import { Alert, Button, IconButton } from "../components/ui";
export function Login() {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [csrf, setCsrf] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  async function loadCsrf() {
    try {
      setCsrf((await api<{ csrf_token: string }>("/auth/csrf")).csrf_token);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to connect.");
    }
  }
  useEffect(() => {
    void loadCsrf();
  }, []);
  if (auth.session) return <Navigate to="/" replace />;
  return (
    <div className="login-page">
      <header className="login-header">
        <Brand />
        <ThemeToggle />
      </header>
      <main className="login-layout">
        <section className="login-context">
          <div className="eyebrow">DATABASE ACCESS &amp; AUDIT</div>
          <h1>
            Control access.
            <br />
            Keep a clear record.
          </h1>
          <p>
            A dedicated workspace for managing permissions, evaluating access,
            and investigating decisions.
          </p>
          <div className="login-principles">
            {[
              [
                KeyRound,
                "Role-based access",
                "Clear permissions for every responsibility.",
              ],
              [
                ShieldCheck,
                "Default-deny policy",
                "Access is allowed only with an active permission.",
              ],
              [
                Database,
                "Durable audit history",
                "Decisions and policy changes recorded in PostgreSQL.",
              ],
            ].map(([Icon, title, description]) => {
              const Glyph = Icon as typeof KeyRound;
              return (
                <div key={String(title)}>
                  <Glyph size={19} />
                  <div>
                    <strong>{String(title)}</strong>
                    <span>{String(description)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
        <section className="login-panel">
          <div className="eyebrow">WORKSPACE SIGN IN</div>
          <h2>Welcome back</h2>
          <p>Enter your credentials to continue.</p>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              setBusy(true);
              setError("");
              const form = new FormData(event.currentTarget);
              try {
                await auth.login({
                  email: String(form.get("email")),
                  password: String(form.get("password")),
                  csrf_token: csrf,
                });
                navigate(location.state?.from || "/", { replace: true });
              } catch (e) {
                setError(e instanceof Error ? e.message : "Unable to sign in.");
                await loadCsrf();
              } finally {
                setBusy(false);
              }
            }}
          >
            {error && <Alert>{error}</Alert>}
            <div className="field">
              <label htmlFor="login-email">Email address</label>
              <input
                id="login-email"
                name="email"
                type="email"
                placeholder="you@example.com"
                required
                maxLength={254}
                autoComplete="username"
              />
            </div>
            <div className="field">
              <label htmlFor="login-password">Password</label>
              <div className="password-field">
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  required
                  maxLength={128}
                  autoComplete="current-password"
                />
                <IconButton
                  label={showPassword ? "Hide password" : "Show password"}
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </IconButton>
              </div>
            </div>
            <Button
              className="w-full"
              type="submit"
              busy={busy}
              disabled={!csrf}
            >
              {busy ? "Signing in…" : "Sign in"}
            </Button>
            {!csrf && (
              <Button
                type="button"
                variant="ghost"
                onClick={() => void loadCsrf()}
              >
                Retry connection
              </Button>
            )}
          </form>
          <div className="login-help">
            <LockNote />
            Access is provided by your administrator.
            <br />
            Contact them if you need help signing in.
          </div>
        </section>
      </main>
      <footer className="login-footer">
        Development workspace · Synthetic demonstration data
      </footer>
    </div>
  );
}
function LockNote() {
  return <ShieldCheck size={16} aria-hidden="true" />;
}
