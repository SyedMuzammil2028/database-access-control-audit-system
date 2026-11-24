# Implementation references

The primary requirements are the supplied proposal and the two pasted master
specifications. The proposal's extracted text and images are retained in
`docs/source/` for traceability; the original DOCX is preserved at repository root.

Technical references consulted during implementation:

- [SQLAlchemy session basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [SQLAlchemy transaction management](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)

The implementation uses transaction commits before returning durable decisions
and one SQLAlchemy session per request. Service callers must commit on success
and roll back on failure. The test suite verifies those boundaries in PostgreSQL.

Frontend reference source inspection and licensing boundary are detailed in
[DESIGN_REFERENCE.md](DESIGN_REFERENCE.md). Toolchain compatibility follows the
[official Vite guide](https://vite.dev/guide/). Exact package versions were checked
against the primary npm and PyPI registries. The lockfiles record the resolved
dependency set; security advisories prompted updates before final verification.
