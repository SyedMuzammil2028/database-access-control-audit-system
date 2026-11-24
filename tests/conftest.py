import os
import re
from pathlib import Path
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config

url = os.environ.get('TEST_DATABASE_URL')
if not url or not (make_url(url).database or '').endswith('_test'):
    raise RuntimeError('Tests require an explicit disposable TEST_DATABASE_URL ending in _test.')
os.environ['DATABASE_URL'] = url
os.environ['SECRET_KEY'] = 'isolated-tests-only-key-minimum-32-characters'
from app.database import get_db
from app.main import app
from app.models import LoginSession
from app.security.sessions import digest
from fastapi.testclient import TestClient


@pytest.fixture(scope='session')
def pg_engine():
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text('DROP SCHEMA public CASCADE; CREATE SCHEMA public'))
    command.upgrade(Config('alembic.ini'), 'head')
    with engine.begin() as conn:
        conn.exec_driver_sql(Path('sql/views.sql').read_text())
        conn.exec_driver_sql("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='dac_app') THEN CREATE ROLE dac_app; END IF; END $$")
        conn.exec_driver_sql(Path('sql/security.sql').read_text())
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def dataset(pg_engine):
    with pg_engine.connect() as conn:
        conn.exec_driver_sql('TRUNCATE app_user, role, permission, user_role, role_permission, resource, audit_event, policy_change, login_session, security_event RESTART IDENTITY CASCADE')
        conn.commit()
        conn.exec_driver_sql(Path('sql/seed.sql').read_text())
        conn.commit()
        # Keep the frozen development fixture's date distribution relative to today.
        conn.exec_driver_sql("UPDATE audit_event SET occurred_at=occurred_at + (now() - (SELECT max(occurred_at) FROM audit_event))")
        conn.commit()
    yield


@pytest.fixture
def db(pg_engine):
    with Session(pg_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def client(pg_engine):
    def override():
        with Session(pg_engine, expire_on_commit=False) as session:
            yield session
    app.dependency_overrides[get_db] = override
    with TestClient(app, follow_redirects=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sign_in(client, pg_engine):
    def login(email='admin@example.com', password='AccessDemo!2026#'):
        token = client.get('/api/auth/csrf').json()['csrf_token']
        response = client.post('/api/auth/login', json={'email':email,'password':password,'csrf_token':token})
        return response, response.json().get('csrf_token') if response.status_code==200 else None
    return login
