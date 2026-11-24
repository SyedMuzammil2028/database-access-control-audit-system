# Requirements to implementation checklist

The supplied proposal plus both pasted specifications define the scope. This
matrix describes implementation evidence and explicitly records verification
limits; it is not a claim of external security certification.

| Requirement | Implementation/evidence |
| --- | --- |
| Eight core relational entities, 3NF | backend/app/models/entities.py, revision 0001, DATABASE_DESIGN.md |
| PK/FK/composite/UQ/NOT NULL/CHECK | PostgreSQL migration; database constraint tests and sql/constraints.sql |
| Registered document/report targets, R42 | scripts/seed.py and sql/seed.sql |
| Real PostgreSQL, migrations, Docker | backend/app/database.py, alembic, Dockerfile, docker-compose.yml |
| Secure login/logout/server sessions | backend/app/security/passwords.py, security/sessions.py, routes/api.py; authentication, expiry and CSRF tests |
| Backend role restrictions | API context/category dependencies and guard_admin; direct-route and unauthorized-write tests |
| Default deny, active users/resources/roles | services/authorization.py and rule tests |
| Combined permissions and deterministic match | services/policy.py, authorization.py; multiple-role/history tests |
| Durable audit, historical identifiers | audit_event snapshots, commit before response, failure-trigger tests |
| Request UUID/idempotency | actor/request UQ, payload conflict validation, row lock; replay/concurrent tests |
| Transactional assignments/revocations/mappings | mutate + write_policy; PostgreSQL rejection-trigger rollback tests |
| Final active administrator protection | exclusive transaction lock and invariant count; three lockout paths and concurrent removal test |
| User creation and activation | Users page and create_user/user_status routes; end-to-end HTTP admin test |
| Roles and mappings | Roles, Permissions and Role assignments pages; audited create/edit/status/map/revoke workflows |
| Resource registry and status | Resources page, create_resource/resource_status; active/inactive tests |
| Three database-backed dashboards | JSON dashboard endpoint, shared React dashboard and category-specific metrics; API and browser tests |
| Ordinary roles/permissions/request/history | My access, Resources, Request access, event detail and personal-history scope |
| Auditor filters/details/policy | services/reports.py, audit/policy/security pages; filter and event-scope tests |
| Bounded, filtered, safe CSV | export query, 93 days, 5,000 rows, formula escaping; role/window/count/filter tests |
| CRUD, joins, GROUP BY/HAVING, aggregate, EXISTS | sql/queries.sql, automated script execution |
| Views, transactions, indexes, EXPLAIN, GRANT | sql/views.sql, transactions.sql, indexes.sql, queries.sql, security.sql |
| Seven analytical queries | queries.sql sections 4–10, SQL_DEMONSTRATION.md |
| Synthetic data / three per category / dates | 10 users, 6 roles, 8 permissions, 16 resources, 180 decisions, 13 policy changes |
| Append-only application and DB grants | no audit edit/delete routes, SELECT/INSERT grants; runtime-role denial tests |
| Parameterized input, bounded pages, safe sort | ORM/Pydantic/report allowlists; injection and invalid-filter tests |
| Reusable enterprise UI and responsive styles | React shared components, Tailwind/HSL tokens, self-hosted Geist, Radix dialogs, Lucide, mobile drawer, dark/light themes and persisted sidebar collapse |
| Visual desktop/mobile browser QA | Containerized Playwright and real screenshot inspection; current actual results in TEST_RESULTS.md. Direct CUA host unavailable. |
| Academic report/ERD/dictionary/demo/setup | docs and README.md |
| Actual test evidence and archive | TEST_RESULTS.md and generated project ZIP; secrets/runtime files excluded |

| Updated React specification | Evidence |
| --- | --- |
| Inspect actual SecureAuth source | DESIGN_REFERENCE.md, pinned inspected commit and source-file inventory |
| Original implementation, licensing | No reference source/assets/auth copied; dependency notices in third-party/ |
| React/TypeScript/Vite/Tailwind | frontend package manifests, lockfile, typed client and production build |
| Radix, Lucide, Geist, reference tokens | components/ui.tsx, shell.tsx, index.css |
| Same-origin API, typed requests/responses | backend/app/schemas, /api routes, exported OpenAPI and generated schema.d.ts |
| Dark/light, desktop/mobile, collapse | ThemeToggle, persisted preferences, responsive drawer and Playwright tests |
| Actual component/API tests | Vitest tests cover authentication, navigation, errors, confirmations and filters |
| Clean installation | Separate dac-acceptance Compose project with a new PostgreSQL volume |
