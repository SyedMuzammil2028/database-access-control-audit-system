# Client installation and operations

## Install and verify

Install Docker Engine/Desktop with Compose v2 and Python 3. Extract/open the
project directory. On Windows use a terminal in the extracted project and
`python` instead of `python3` if needed. No host Node.js, paid APIs or cloud account are required for the Docker path.
Docker builds the React bundle and FastAPI serves both static assets and /api.
For separate Vite/TypeScript development use Node 22.22.2+ as documented in README.

```sh
python3 scripts/configure.py
docker compose up --build -d
```

Visit http://localhost:8000 and sign in using README.md. Check
`docker compose ps` for healthy database/web containers and
`docker compose logs setup` for successful migration and seed completion.
`curl http://localhost:8000/health` verifies an actual database connection.
The owner database port is bound to loopback only; the application is also
loopback-bound by default. The database is persistent across normal shutdowns.

## Upgrade

Back up the database and protect `.env` first. Keep the same credentials, update
the source, and run `docker compose up --build -d`. Setup runs Alembic upgrade
and preserves an existing dataset. A startup job failing must be investigated
through its logs before retrying. Migrations and grants use the owner account;
the running application uses dac_app and never needs schema-owner credentials.

## Backup and restore

The following commands use the owner's in-container local connection. The backup
contains password hashes and audit history; keep it private. Do not commit it.

```sh
docker compose exec -T db pg_dump -U dac_owner -d dac -Fc > dac-backup.dump
```

For a restore, prepare a separate PostgreSQL instance/database and restore the
archive as its owner. Preserve the application role, then reapply
`sql/security.sql` if role provisioning differs. Test restores before relying on
a backup. Never restore destructively over the only working database.

## Development and security configuration

`configure.py` generates `.env` only when missing and sets mode 0600 on Unix.
Changing `.env` does not rotate an already initialized PostgreSQL password.
Use PostgreSQL owner procedures and update service configuration together.
Demo passwords and identities are intentional development fixtures. Before
any external deployment, provision actual identities and remove demo access;
do not load `seed.sql` into a client database.

`COOKIE_SECURE=true` requires HTTPS. Place external deployments behind a correctly
configured trusted HTTPS reverse proxy, restrict network exposure and review
SECURITY.md. `SESSION_HOURS` can be supplied as an environment variable (1–24).
Application/DB health and backups need operational monitoring.

## Common issues

- Port already used: stop the conflicting local process or edit the loopback
  host port in Compose. If changing 5434, update the local `.env` DATABASE_URL.
- Login fails: use the exact development credentials; inactive accounts cannot
  sign in. Ten failed attempts trigger a fifteen-minute throttle.
- Setup cannot authenticate after `.env` replacement: restore the original secrets
  matching the existing volume; recreating config does not update database roles.
- Host `venv` unavailable: use the Docker path, which installs its own Python.
- CSV rejected: choose both dates, narrow to 93 days or fewer, then reduce results
  below 5,001 rows. The export never silently truncates an investigation.
- Database unavailable: the application returns 503 and cannot grant new access
  without a durable audit event. Restore the database connection and retry with
  the same request ID if the original result is uncertain.

## Stop

`docker compose down` stops services while retaining demo data. Test services use
a separate tmpfs database; `docker compose --profile test down` also stops them.
No command in normal setup deletes the main database volume.
