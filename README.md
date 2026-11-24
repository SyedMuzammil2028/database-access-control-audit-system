# Database Access Control and Audit System

Repository: https://github.com/SyedMuzammil2028/database-access-control-audit-system

The repository is private. Instructors need collaborator access to view it.
For a file upload, use `artifacts/Database-Access-Control-Audit-System.zip`, which
contains source code and submission documents. The smaller submission ZIP holds
only the report and ER diagram. Archives are generated locally and are not committed.

**Access Ledger** implements the supplied Database Systems proposal using
PostgreSQL/FastAPI and React/TypeScript. It manages users, roles, resource
permissions and immutable decision snapshots. The frontend follows the supplied
SecureAuth reference's neutral, indigo, dark-first design language, with a
working light theme and collapsible navigation.

[Desktop preview](docs/screenshots/admin-dark.png) · [Light theme](docs/screenshots/admin-light.png) · [Mobile preview](docs/screenshots/mobile-dark.png)

All records and counts come from PostgreSQL. Resource requests evaluate READ,
CREATE, UPDATE and DELETE authorization; they do not modify external files or
intercept arbitrary database traffic.

## Start locally

Install Docker Engine/Desktop with Compose v2 and Python 3. From this directory:

```sh
python3 scripts/configure.py
docker compose up --build -d
```

On Windows use `python` if `python3` is unavailable. Open **http://localhost:8000**.
Ports 8000 and 5434 must be free. Docker builds React, starts PostgreSQL, applies
migrations and least-privilege grants, and seeds an empty database. No host Node
or Python packages are required. The SPA/API share one origin; bearer tokens are
never put in browser storage. First build requires internet access.

```sh
docker compose ps
docker compose logs setup web
docker compose down
```

Shutdown preserves data. Keep `.env` with the volume: generating new passwords
does not rotate existing database roles. Setup preserves an existing dataset,
including revoked assignments. Do not delete the volume unless discarding data.

## Development-only demo credentials

Shared password: **`AccessDemo!2026#`**

| Category | Email addresses |
| --- | --- |
| Administrator | `admin@example.com`, `maya.admin@example.com`, `omar.admin@example.com` |
| Auditor | `auditor@example.com`, `leila.auditor@example.com`, `noah.auditor@example.com` |
| Ordinary user | `analyst@example.com`, `editor@example.com`, `viewer@example.com` |
| Inactive | `inactive@example.com` (cannot sign in) |

The analyst reads R42 reports and documents through multiple roles. The editor
reads/creates/updates documents; the viewer reads documents. Auditors investigate
without writing policy or evaluating resource operations. Administrators have
explicit seeded resource grants; ownership does not imply permission.

## Tests

```sh
# Backend with a separate disposable PostgreSQL database:
docker compose --profile test run --build --rm test

# React component tests and production build (Node 22.22.2+):
cd frontend
npm ci
npm test
npm run build
```

The backend fixture refuses database names that do not end in `_test`, uses a
separate tmpfs server, and resets only that database. Do not run pytest workers
in parallel against it. Tests include real audit-insert failure triggers and
concurrent administrator changes. See [actual results](docs/TEST_RESULTS.md).

For Playwright, target only a synthetic development instance:

```sh
# In frontend/, with the application running at localhost:8000:
npx playwright install --with-deps --only-shell chromium
npm run test:e2e
```

Linux Docker alternative, from the root:

```sh
docker build -f frontend/Dockerfile.e2e -t dac-playwright frontend
docker run --rm --network host --memory=640m --memory-swap=640m -e NODE_OPTIONS=--max-old-space-size=128 -v "$PWD/frontend/test-results:/work/test-results" dac-playwright
```

For Docker Desktop omit host networking and set
`-e PLAYWRIGHT_BASE_URL=http://host.docker.internal:8000`. Browser tests create
fictional accounts, roles, evaluations and policy history. Never target client data.

## Host development

Use Python 3.12+ with venv and Node 22.22.2+. In two terminals:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt -c requirements.lock
docker compose up -d db
docker compose run --build --rm setup
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

```sh
cd frontend
npm ci
npm run dev
```

Open Vite's URL, normally http://localhost:5173. It proxies `/api` to FastAPI,
keeping same-origin cookie/CSRF behavior. On PowerShell activate
`.venv\Scripts\Activate.ps1`; use Docker if host tooling is inconvenient.

## API contracts

Pydantic defines typed request/response contracts; frontend types are generated
from OpenAPI. After a contract change, on Unix:

```sh
PYTHONPATH=backend .venv/bin/python -m scripts.export_openapi
cd frontend
npm run api:types
npm run build
```

On PowerShell set `$env:PYTHONPATH="backend"` and invoke
`.venv\Scripts\python.exe -m scripts.export_openapi`. OpenAPI and generated types
contain no credentials or session tokens.

## SQL demonstrations

```sh
docker compose exec -T db psql -U dac_owner -d dac -v ON_ERROR_STOP=1 < sql/queries.sql
docker compose exec -T db psql -U dac_owner -d dac -v ON_ERROR_STOP=1 < sql/constraints.sql
docker compose exec -T db psql -U dac_owner -d dac -v ON_ERROR_STOP=1 < sql/transactions.sql
```

Redirection works in Bash/zsh/CMD. PowerShell can pipe
`Get-Content -Raw sql/queries.sql` into the same `docker compose exec -T ...`
command. Use development data. Alembic is canonical; standalone DDL is generated.

## Submission documents

- [Project report PDF](docs/submission/Project_Report.pdf) and [editable Word copy](docs/submission/Project_Report.docx).
- [Complete ER diagram PDF](docs/submission/ER_Diagram.pdf).
- [Submission contents and checks](docs/submission/README.md).

## Repository and documentation

- `backend/app/`: routes, schemas, sessions, RBAC, transactions and models.
- `frontend/`: React/TypeScript/Vite, Tailwind, Radix, Lucide, local Geist,
  component tests and Playwright workflows.
- `alembic/`, `sql/`, `scripts/`: schema, academic queries and setup/seed tools.
- [ERD](docs/ERD.md), [data dictionary](docs/DATABASE_DESIGN.md),
  [project report](docs/PROJECT_REPORT.md), [SQL guide](docs/SQL_DEMONSTRATION.md),
  [demo guide](docs/DEMO_GUIDE.md), [installation](docs/INSTALLATION.md),
  [security scope](docs/SECURITY.md), [requirements](docs/REQUIREMENTS.md),
  [reference review](docs/DESIGN_REFERENCE.md).

Requirements files pin Python dependencies; exact frontend versions and
package-lock.json support reproducible npm ci. This prototype is not certified
or independently security-audited. HTTPS, backups, credential recovery, retention
and deployment review remain operational responsibilities. Never expose demo access.
