# Actual verification results

Updated React specification verification on **22 November 2026** (Asia/Karachi).
All results below come from executed checks.

## PostgreSQL and JSON API

```sh
docker compose --profile test run --build --rm test
```

**113 passed, 1 dependency deprecation warning, 56.84 seconds.**
Python 3.12; PostgreSQL 17; FastAPI 0.165.0; Starlette 1.10.0;
SQLAlchemy 2.0.44; pytest 9.2.0. Tests use a separate tmpfs PostgreSQL server,
refuse non-`_test` database names and reset only their synthetic test database.
No client or main application database is cleared.

Coverage includes:

- Valid/invalid/inactive authentication, signed login CSRF, throttling, hashed
  server sessions, cookie properties, expiry, logout and security events.
- Three categories' typed API views; backend 401/403 restrictions; auditor
  read-only behavior; excluded password hashes and session storage fields.
- Default deny, allowed requests, inactive accounts/resources/roles, missing
  resources, combined roles, deterministic matching and role revocation.
- Immutable historical snapshots after role renaming and policy changes.
- PostgreSQL duplicate pairs, unique keys, orphan FKs and CHECK rejection.
- Last administrator protection for account/assignment/role removal and
  concurrent administrator changes.
- Request UUID replay, payload conflicts, forbidden actor claims and concurrent
  retries creating one record.
- Real PostgreSQL triggers rejecting audit INSERTs. Assign/revoke/map/unmap
  roll back on policy audit failure; decision failure never returns ALLOWED.
- Actor/action/decision/resource/date filtering, personal event isolation,
  literal wildcard search and SQL injection-resistant inputs.
- CSV filter correctness, roles, 93-day limit, 5,000-row bound, secret omission
  and formula escaping.
- Full JSON administration workflow, field validation and safe conflicts.
- Bounded searchable selection lists, strict status booleans and no permissive CORS.
- Least-privilege runtime grants rejecting history modification, DDL and
  migration-table access.
- ORM/migration comparison; executable SQL queries, views, indexes, constraints,
  transactions; standalone schema/seed on an independent empty schema.

The warning states that Starlette's compatibility client using `httpx` is
 deprecated in favor of `httpx2`. The existing maintained HTTP client remains
functional; no failures were suppressed. Versions are pinned in requirements files.

## React

`npm test`: **12 component/API integration tests passed** (12.35 seconds in the
completed run after the filter-label correction). These exercise login payload/CSRF and real-response
metrics, failed login, protected navigation, logout, themes/collapse, mobile
drawer, safe server errors, field validation, confirmation cancellation,
resource request UUIDs and report-filter requests.

`npm run build`: TypeScript and Vite production build succeeded. It bundles local
Geist assets with no Google Fonts request. Types in `frontend/src/lib/schema.d.ts`
are generated from the actual FastAPI OpenAPI contracts. The build also type-checks
test sources; test-only typing errors found during integration were corrected.

## Clean installation and browser checks

A separate `dac-acceptance` Compose project created a new PostgreSQL volume,
provisioned the restricted runtime account, applied migrations, loaded the Python
seed, and started a healthy React/FastAPI app. Alternate loopback ports (8002/5436)
kept the user's persistent main database separate. Subsequent setup retained data.

Browser verification used the explicitly requested Playwright/Chromium container.
**All 5 tests passed in 58.3 seconds.** The direct CUA host was unavailable; actual
Chromium rendering, interactions and screenshots were verified through Playwright.

Verified browser workflows:

1. Administrator login/logout, every workspace page, both themes, persisted
   collapse/expansion, HttpOnly cookie invisibility and no authentication tokens
   in web storage. No unhandled browser script errors.
2. Ordinary-user allowed, denied and inactive-resource decisions, personal history
   isolation, restricted navigation and unchanged historical event details.
3. Account/role creation, permission mapping, assignment, separate-user login,
   resulting allowed access, cancellation/confirmation of revocation, subsequent
   denial and retained original allowed decision; policy detail investigation.
4. Auditor search/action/decision/resource/date filters, exact filtered CSV download,
   decision detail and read-only restrictions.
5. Mobile navigation, management dialog, both themes, and viewport-bounded
   dashboard/users/audit/request/roles/resources/permissions screens. Wide tables
   scroll inside their containers.

Browser testing found and corrected select-label associations and a visually hidden
table heading escaping its scrolling container. Earlier test-selector ambiguities
were scoped to the intended row/notification. Final tests have no failures.
Checks were serialized and browser memory bounded to avoid host memory pressure.

Actual screenshots in `docs/screenshots/` were inspected for typography, spacing,
table readability, theme consistency, dialogs and mobile overflow. They contain
only fictional development data. Counts reflect database changes made by the tests.

## Dependency review

The final npm install audited its resolved dependency set with **zero findings**.
A primary PyPI advisory-metadata check covered **38 Python pins with zero listed
advisories** after upgrading FastAPI/Starlette, pydantic-settings and pytest, and
removing unused Jinja/multipart dependencies. This is a known-advisory review, not independent security
certification. Lockfiles pin the tested dependency set.

## Final fresh-volume check and live smoke

The disposable acceptance volume was removed and recreated after browser tests.
The updated setup loaded exactly **10 users, 6 roles, 8 permissions, 16 resources,
180 decision events and 13 policy changes**, verified by a real PostgreSQL query.
The live `scripts.smoke` check against that installation verified health, all
three dashboards, administration endpoints, allowed/denied requests, a viewer
grant and revocation, auditor restrictions, filtered CSV and logout.

The source archive excludes .env, virtual environments, node_modules, build
outputs and browser trace/results directories. Inspected screenshots contain
only synthetic data and are intentionally included in documentation.

The upgraded main application at http://localhost:8000 also passed the live
smoke script. React production HTML and its CSS/JavaScript entry assets returned
200 through FastAPI, and the main database/web Compose health checks passed.
