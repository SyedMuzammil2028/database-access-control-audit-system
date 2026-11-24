# Security behavior and limitations

## Authentication

Argon2id through maintained pwdlib hashes passwords with random salts. There is
no public registration. The browser holds only an opaque, random session token;
PostgreSQL stores its SHA-256 digest and expiry. Login rotates the current token.
Logout deletes the server session. The default absolute session lifetime is
eight hours (configurable 1–24). Account status and active role assignments are
re-read on protected requests, so revocation takes effect without waiting for
cookie expiry. Expired session records can be removed by the owner according to
an operational retention policy.

HttpOnly/SameSite=Lax session cookies use Secure when `COOKIE_SECURE=true`.
Local HTTP defaults to false. Deployments must terminate HTTPS and enable Secure
cookies. Login CSRF uses a signed, one-hour token compared with an HttpOnly
SameSite=Strict cookie. Authenticated mutations require a random per-session CSRF
token in the form or `X-CSRF-Token` for JSON requests. GET routes never mutate
policy or access decisions. Database-backed throttling rejects further sign-in
attempts after ten failures from an email or keyed IP hash in fifteen minutes;
IP and normalized-email advisory locks are acquired in sorted order, serializing
counter checks across sources. Add edge-level abuse controls for a public deployment.

## Authorization and transactions

Active `admin` roles authorize administrative routes, active `auditor` roles
permit read-only investigation, and `user` is the default workspace category.
Admin takes precedence when both categories are present. Auditor-only identities
cannot submit resource evaluation or policy mutation endpoints. Resource grants
always require explicit permission mappings, including for administrators.

Policy writes acquire transaction-scoped exclusive PostgreSQL advisory lock
73481021, recheck administrator authority, validate inputs, mutate data, verify
that at least one active administrator remains, and insert POLICY_CHANGE before
commit. All mutation paths use this service. Concurrent removals serialize; one
is rejected if it would remove the last administrator. Permission mapping
removal, assignment/revocation and status changes use the same transaction.

Access evaluation acquires a shared policy lock and a row lock on the actor.
The check order is account status, resource existence, resource status, active
assignment/role and matching action/type permission. Multiple matches choose the
smallest role ID. Missing permission denies by default. No resource content is
read, written or deleted as part of an evaluation.

| Reason | Decision |
| --- | --- |
| ALLOWED_BY_ROLE | Explicit active mapping found; matching role ID/name recorded. |
| NO_MATCHING_PERMISSION | No matching active role permission. |
| INACTIVE_ACCOUNT | Existing authenticated session belongs to an inactive account. |
| INACTIVE_RESOURCE | Registered resource is disabled. |
| RESOURCE_NOT_FOUND | Valid positive ID has no registry record. Numeric ID is retained as the resource key snapshot. |

Malformed requests fail validation before evaluation; unauthenticated requests
fail authentication. They do not fabricate access-decision events. Failed and
successful logins and logout have separate security events. An inactive account
cannot sign in, but a still-existing session can submit an evaluation and receive
a durable INACTIVE_ACCOUNT denial. Other protected pages reject that session.

## Audit and retry semantics

One completed evaluation creates one immutable snapshot with actor, action,
resource identifiers, decision, reason, deterministic matching role, request ID
and a server timestamp. Invalid or unauthorized inputs do not become completed
evaluations. If insertion or COMMIT fails, the application returns an error and
never returns ALLOWED. Transient database errors return safe 503 messages.

Request IDs are UUIDs, unique per actor. Repeating the same ID and action/resource
payload returns the original durable event. Reusing that ID for another payload
returns 409. IDs are actor-scoped, so one user cannot retrieve another user's
result. Concurrent retries serialize on the actor row. An idempotent replay
represents the original evaluation, even if policy has changed; use a fresh ID
to evaluate current policy. New browser request forms create fresh UUIDs.
Policy POSTs use ordinary conflict validation rather than automatic replay;
refreshing after a successful POST uses redirect-after-post.

Event and policy endpoints expose no edit/delete operations. Runtime grants
allow SELECT/INSERT only for audit_event, policy_change and security_event. Their
foreign keys prevent accidental deletion of referenced live entities. Historical
email, role name, resource key and reason snapshots remain meaningful after
policy updates. The migration owner, PostgreSQL superusers, storage operators
and backups remain outside this immutability guarantee. This is not a
cryptographically sealed or independently certified audit trail.

## Reporting and operational limits

ORM queries are parameterized. Search treats LIKE wildcard characters literally;
sort orders are allowlisted. Tables use 20-row pages with a bounded page number.
CSV requires both UTC dates, at most 93 inclusive days and at most 5,000 events;
it rejects oversized results rather than silently truncating. Formula-like cells
are prefixed to prevent spreadsheet formula injection. CSV and investigation
routes are restricted to administrators and auditors; ordinary users can only
view their own events. Passwords, hashes, bearer tokens and CSRF tokens are never
included in history, exports or database error logs.

CSP restricts scripts/assets to the application, blocks framing and restricts
form destinations. Inline styles are allowed for Radix scroll-lock behavior;
inline scripts remain blocked. React escapes user-provided text. The app sends
no-store, nosniff and same-origin referrer headers. `.env` is ignored by Git and
excluded from Docker build contexts and delivery ZIPs. Docker runs the app as a
non-root user; the migration owner credential is absent from the web container.

Known prototype limitations: no MFA, self-service password reset, enterprise SSO,
tamper-evident external audit archive, automatic backup/retention jobs or
independent security certification. Admin credential recovery is an owner-run
operation; it must be separately audited operationally. Selection APIs return at most 50 matches (plus a selected item); forms provide
server-side option search. The actor filter shows a bounded list; email search
can investigate actors beyond it. Direct SQL owners can bypass
application last-admin rules. Configure trusted reverse-proxy and host controls
for an external deployment. Never expose the seeded demo credentials publicly.

## React integration

The React SPA and API are served by the same FastAPI origin. Development uses a
Vite API proxy; no cross-origin credential permission is enabled. Backend routes
return JSON 401/403 independently of frontend route guards. Session/CSRF state
is fetched into React memory, never localStorage or sessionStorage. Only theme
and sidebar UI preferences persist in localStorage. Every JSON write checks the
X-CSRF-Token header; login compares its signed token with an HttpOnly cookie.

Pydantic response models exclude hashes and database session fields. TypeScript
contracts are generated from OpenAPI, and component tests exercise API failures,
validation errors, authorization results and confirmation gates. All policy
operations recheck backend authority. Frontend success is set only after a
confirmed API response. Network retry of an unchanged resource request keeps
its UUID; editing the operation/resource creates a new request UUID.
