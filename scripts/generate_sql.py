"""Regenerate educational schema from canonical migrations, and seed from a clean
synthetic demo database. Run as owner immediately after initial setup only."""
import io
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from app.database import Base, engine
from app.models import User

buffer = io.StringIO()
config = Config('alembic.ini', output_buffer=buffer)
command.upgrade(config, 'head', sql=True)
Path('sql/schema.sql').write_text('-- GENERATED from Alembic; do not edit. Empty database only.\n' + buffer.getvalue())
# Snapshot uses only development tables, excluding server sessions and auth attempts.
tables = [t for t in Base.metadata.sorted_tables if t.name not in ('login_session','security_event')]
with engine.connect() as connection:
    if connection.scalar(select(User.email).where(User.email=='admin@example.com')) is None:
        raise SystemExit('Seed export requires the synthetic development fixture.')
    lines = ["-- GENERATED synthetic development fixture. Password hashes are Argon2id.",
             "-- Empty, migrated database only. Never production. Canonical generator: scripts/seed.py.",
             "BEGIN;", "DO $$ BEGIN IF EXISTS (SELECT 1 FROM app_user) THEN RAISE EXCEPTION 'Seed requires an empty database'; END IF; END $$;"]
    import psycopg
    from psycopg import sql
    from psycopg.types.json import Jsonb
    with psycopg.connect(str(engine.url.set(drivername='postgresql').render_as_string(hide_password=False))) as raw:
        for table in tables:
            for row in connection.execute(select(table).order_by(*table.primary_key.columns)).mappings():
                values = [Jsonb(v) if isinstance(v,dict) else v for v in row.values()]
                stmt = sql.SQL('INSERT INTO {} ({}) VALUES ({});').format(sql.Identifier(table.name),
                    sql.SQL(', ').join(sql.Identifier(k) for k in row.keys()), sql.SQL(', ').join(sql.Literal(v) for v in values))
                lines.append(stmt.as_string(raw))
        for table in tables:
            if len(table.primary_key.columns)==1:
                pk = list(table.primary_key.columns)[0]
                if str(pk.type)=='INTEGER':
                    lines.append(f"SELECT setval(pg_get_serial_sequence('{table.name}', '{pk.name}'), COALESCE((SELECT max({pk.name}) FROM {table.name}), 1));")
    lines.append('COMMIT;')
    Path('sql/seed.sql').write_text('\n'.join(lines)+'\n')
print('Generated schema.sql and synthetic seed.sql.')
