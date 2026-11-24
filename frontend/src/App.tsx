import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Outlet,
  Link,
  useLocation,
} from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import { ConfirmProvider, Loading, ErrorState } from "./components/ui";
import { Shell } from "./components/shell";
import { Login } from "./pages/login";
import { Dashboard } from "./pages/dashboard";
import { Users, Roles, Permissions, Assignments } from "./pages/management";
import { Resources } from "./pages/resources";
import { MyAccess, Account, RequestAccess, EventDetail } from "./pages/member";
import { AuditEvents, PolicyHistory, SignInActivity } from "./pages/reports";
import type { Category } from "./lib/types";
export function Protected({ allowed }: { allowed?: Category[] }) {
  const auth = useAuth();
  const location = useLocation();
  if (auth.loading) return <Loading label="Connecting to your workspace…" />;
  if (!auth.session && auth.error)
    return <ErrorState message={auth.error} retry={() => void auth.reload()} />;
  if (!auth.session)
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (allowed && !allowed.includes(auth.session.category))
    return (
      <div className="restricted">
        <h1>Access restricted</h1>
        <p>Your current role does not have access to this workspace area.</p>
        <Link className="btn btn-outline" to="/">
          Return to overview
        </Link>
      </div>
    );
  return <Outlet />;
}
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Protected />}>
        <Route element={<Shell />}>
          <Route index element={<Dashboard />} />
          <Route path="account" element={<Account />} />
          <Route path="my-access" element={<MyAccess />} />
          <Route path="resources" element={<Resources />} />
          <Route path="history" element={<AuditEvents />} />
          <Route path="events/:id" element={<EventDetail />} />
          <Route element={<Protected allowed={["admin", "user"]} />}>
            <Route path="request" element={<RequestAccess />} />
          </Route>
          <Route element={<Protected allowed={["admin"]} />}>
            <Route path="users" element={<Users />} />
            <Route path="roles" element={<Roles />} />
            <Route path="permissions" element={<Permissions />} />
            <Route path="assignments" element={<Assignments />} />
          </Route>
          <Route element={<Protected allowed={["admin", "auditor"]} />}>
            <Route path="audit" element={<AuditEvents />} />
            <Route path="policy" element={<PolicyHistory />} />
            <Route path="security" element={<SignInActivity />} />
          </Route>
          <Route
            path="*"
            element={
              <div className="restricted">
                <h1>Page not found</h1>
                <p>This workspace page does not exist.</p>
                <Link className="btn btn-outline" to="/">
                  Return to overview
                </Link>
              </div>
            }
          />
        </Route>
      </Route>
    </Routes>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ConfirmProvider>
          <AppRoutes />
        </ConfirmProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
