# SQL demonstration guide

Use a synthetic development database and connect as the owner. Do not execute
course mutation examples against a production database. Every supplied script
is PostgreSQL-specific; SQLite cannot validate this project.

| Script | Purpose |
| --- | --- |
| `schema.sql` | Generated offline Alembic DDL. Apply once to an empty database, as an alternative to `alembic upgrade head`. It sets the revision marker; do not run both paths on the same initialized database. |
| `seed.sql` | Generated development-only dataset with Argon2id hashes; transactionally rejects nonempty user tables. Use after schema creation. Canonical generator is `scripts/seed.py`; regular setup runs that generator only if empty. |
| `queries.sql` | CRUD on a temporary relation; INNER/LEFT/multi-table joins; GROUP BY/HAVING; conditional aggregates; subqueries/EXISTS; all seven required investigations; actual EXPLAIN/ANALYZE examples. |
| `views.sql` | Two repeatably created reporting views. |
| `indexes.sql` | Idempotent illustrations of the indexes already maintained by Alembic. |
| `constraints.sql` | Tests duplicate pair, orphan FK and unsupported action rejection, catches expected exceptions and leaves no changes. |
| `transactions.sql` | Demonstrates committed temp-table insertion, rolled-back update and an atomic role-revocation/policy-event CTE that is entirely rolled back. |
| `security.sql` | Least-privilege runtime grants; optional SQL auditor example. Requires `dac_app` provisioned independently. |

## Run the demonstrations

From the project root:

```sh
docker compose exec -T db psql -U dac_owner -d dac -v ON_ERROR_STOP=1 < sql/queries.sql
docker compose exec -T db psql -U dac_owner -d dac -v ON_ERROR_STOP=1 < sql/constraints.sql
docker compose exec -T db psql -U dac_owner -d dac -v ON_ERROR_STOP=1 < sql/transactions.sql
```

The numbered queries cover effective permissions (4), daily decisions (5),
repeated denied users (6), changes followed by requests (7), historical versus
current roles (8), administrator assignment history (9) and resource R42 (10).
Change the selected email/key literals to investigate another subject. The
policy-to-request query may return no rows when no request followed the change
within one day; after a live change and request, it will show that relationship.

To regenerate schema and seed snapshots, use an empty synthetic development
database, apply the migrations and Python seed, then run
`PYTHONPATH=backend python -m scripts.generate_sql` with an owner connection. This exporter includes
only the eight core tables; it deliberately excludes live sessions and sign-in
attempts. Do not export a database that contains client data.

Constraint scripts use PL/pgSQL exception subtransactions, so an expected
integrity violation does not abort the entire demonstration. Application
rollback tests go further: PostgreSQL triggers deliberately reject audit
INSERTs, proving that policy changes roll back and that no allowed result is
returned without a durable decision record.
