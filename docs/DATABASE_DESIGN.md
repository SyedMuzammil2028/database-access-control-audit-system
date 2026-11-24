# Database design and data dictionary

Alembic revision `0001` is the canonical application schema. `sql/schema.sql` is
its generated PostgreSQL DDL, including the Alembic revision marker. ORM metadata
is compared with the migrated schema in integration tests.

## Normalization

First normal form: scalar, typed columns hold one value; role lists and permission
lists use junction tables. Second normal form: each junction table's facts depend
on its complete composite key; a permission description is not repeated in a
mapping. Third normal form: users, roles, operations and resources each own their
attributes; role descriptions and resource ownership are not copied into current
assignment records. Email, role name, action/type and resource type/key are
candidate keys enforced by UNIQUE constraints.

Event snapshots intentionally repeat email, resource identifiers and matching
role name. These are facts about the historical event, not a second source of
current policy. Their functional dependency is on event ID, so subsequent changes
to current entities must not rewrite them. JSONB policy details are variable
historical payloads, never used as the live RBAC source. Role kind distinguishes
application administration/reporting authority from resource permissions.

## Data dictionary

`PK` is primary key, `FK` is foreign key, `UQ` is unique. All columns are NOT NULL
unless marked nullable. All timestamps use `timestamp with time zone`.

| Table | Columns and constraints |
| --- | --- |
| `app_user` | `id` integer serial PK; `name` varchar(100), nonblank CHECK; `email` varchar(254), UQ, lowercase CHECK; `password_hash` text Argon2id; `active` boolean default true; `created_at`, `updated_at` server default now (ORM updates updated_at). |
| `role` | `id` integer serial PK; `name` varchar(60) UQ/nonblank; `description` varchar(300) default empty; `kind` varchar(10) CHECK admin/auditor/user default user; `active` default true. |
| `permission` | `id` integer serial PK; `action` varchar(6) CHECK READ/CREATE/UPDATE/DELETE; `resource_type` varchar(40) CHECK lowercase type vocabulary; UQ(action, resource_type). |
| `user_role` | Composite PK(`user_id`, `role_id`), FKs to user/role; `assigned_by` FK user; `assigned_at` default now; `active` default true. Revocations retain the pair with active=false; reactivation records a fresh assignment timestamp. |
| `role_permission` | Composite PK(`role_id`, `permission_id`), both FKs. Removal physically deletes the current mapping; policy snapshots preserve its history. |
| `resource` | `id` integer serial PK; `resource_type` varchar(40) validated type; `resource_key` varchar(80) nonblank; `name` varchar(120); `owner_user_id` FK user; `active` default true; UQ(type, key). Ownership is descriptive, not an implicit access grant. |
| `audit_event` | `id` UUID PK; nullable `actor_user_id` FK; `actor_email` varchar(254) snapshot; action CHECK; nullable `resource_id` FK; `resource_type`, `resource_key` snapshots; `decision` CHECK ALLOWED/DENIED; `reason_code` CHECK documented vocabulary; nullable `matching_role_id` FK and `matching_role_name`; `request_id` UUID; `occurred_at` default now; UQ(actor_user_id, request_id). CHECK requires a matching role for ALLOWED and no matching role for DENIED. |
| `policy_change` | `id` UUID PK; `actor_user_id` FK user; `actor_email` snapshot; `target_type` varchar(30); `target_id` varchar(80) historical entity or composite identifier; `operation` varchar(40); `details` JSONB; `request_id` UUID; `occurred_at` default now. |
| `login_session` | `token_hash` varchar(64) PK SHA-256 of a cryptographic bearer token; `user_id` FK; `csrf_token` varchar(64) random; `created_at` default now; `expires_at` timestamp. Technical table required for revocable server-side sessions. |
| `security_event` | `id` integer serial PK; nullable `actor_user_id` FK; `email` varchar(254) supplied/known identity; `ip_hash` varchar(64) keyed hash; `operation` varchar(30) LOGIN_SUCCESS/LOGIN_FAILED/LOGOUT; `request_id` UUID; `occurred_at` default now. Supports investigation and database-backed login throttling. |

UUID defaults are generated in server application code; timestamps default in
PostgreSQL. The development seed owner can specify historical timestamps. Live
request inputs cannot supply event timestamps or actor identity.

## Indexes and integrity

PostgreSQL supplies PK and UNIQUE indexes. Additional indexes cover assignment
role lookup, permission reverse lookup, resource owner, audit time/actor-time/
decision-time/resource-time, policy time/actor-time, session user/expiry and
security IP-time/email-time. No redundant index duplicates the leading composite
PK on user_role. `EXPLAIN` examples show actual planner choices; a small fixture
can correctly favor sequential scans.

No cascading deletions erase history. Orphan references and duplicate assignments
are rejected by the database. A shared transaction advisory lock protects the
last-admin invariant at the application service boundary; the database owner can
still bypass that invariant through direct SQL. The runtime login has no DDL or
audit UPDATE/DELETE rights.

## Views

`effective_user_permission` joins five tables, combines permissions across active
roles, and excludes inactive users. `daily_access_summary` groups snapshots by
UTC date, type and decision. Neither view stores independent policy state.
