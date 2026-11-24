# Practical demonstration walkthrough

Start the application using README.md. All accounts use the development password
`AccessDemo!2026#`. All event times and report date filters use UTC. Open separate
browser profiles or sign out between categories.

## Ordinary user

1. Sign in as `analyst@example.com`. Review the overview and My access.
2. Open Resources, find report R42 and select Request access.
3. Evaluate READ. Expect **ALLOWED**. Open My access history and inspect the event.
4. Make a new request for DELETE on R42. Expect **DENIED**, because no role grants it.
5. Request READ on archived report R46. Expect **DENIED** for an inactive resource.
6. Open a resource document and READ it. The analyst's second role grants that
   permission, demonstrating the union of multiple roles.

## Administrator

1. Sign in as `admin@example.com`. Open Users and create a fictional account
   with a password of at least 12 characters.
2. Open Roles and create a role; open Permissions and map READ on report to it.
3. Open Role assignments, select the new account and new role, confirm and save.
4. Sign in as that account and evaluate READ R42. Expect ALLOWED.
5. As administrator, revoke the assignment and inspect the resulting policy record.
6. As that account, create a new READ request. Expect DENIED. The earlier ALLOWED
   event is unchanged. Do not reuse the previous request reference for a new check.
7. Register a fictional resource, deactivate/reactivate it, and inspect policy history.
8. To show administrator lockout protection without disabling working accounts,
   run the focused automated last-admin and concurrency tests (below).

## Auditor

1. Sign in as `auditor@example.com`. The overview summarizes real stored decisions.
2. Open Audit events. Select the analyst, READ, report R42, ALLOWED and a recent
   UTC date window; apply filters and open Details.
3. Filter DENIED to inspect stopped requests. Use search for an email/key and
   sort oldest/newest; navigate pages.
4. Inspect Policy history and expand the change details for assignment/revocation.
5. Export CSV with both dates selected (up to 93 days and 5,000 matches). Export
   uses the same filters as the table.
6. Inspect Sign-in activity. Visit `/users` directly to demonstrate backend 403.
   Audit records expose no editing or deletion controls.

## SQL and integrity

Run the commands in SQL_DEMONSTRATION.md. Show the five-table effective-permission
join, the UTC daily GROUP BY, repeated-denial HAVING query, R42 history and policy
changes performed by an administrator. `constraints.sql` prints PASS notices when
PostgreSQL rejects duplicates, orphans and unsupported actions.

`transactions.sql` shows a committed insert and rolled-back update in a temporary
relation, then a completely rolled-back role/policy change. Real failure tests
create PostgreSQL triggers that reject event inserts and assert that no related
policy mutation persists.

```sh
docker compose --profile test run --build --rm test pytest -q -p no:cacheprovider -k 'last_admin or policy_audit_failure or audit_insert_failure or concurrent'
```

Run the full suite for submission. The report and existing screenshots are in docs/submission and docs/screenshots.
Do not claim production certification or arbitrary database interception.
