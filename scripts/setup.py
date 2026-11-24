from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from app.database import engine, SessionLocal
from scripts.seed import seed

command.upgrade(Config('alembic.ini'), 'head')
with engine.begin() as connection:
    connection.execute(text(Path('sql/views.sql').read_text()))
    connection.execute(text(Path('sql/security.sql').read_text()))
with SessionLocal() as db:
    changed = seed(db); db.commit()
print('Migrations, views, least-privilege grants and development seed complete.' if changed else 'Schema ready; existing data retained.')
