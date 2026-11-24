from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings().database_url, pool_pre_ping=True, pool_timeout=10,
                       connect_args={'options': '-c statement_timeout=15000 -c lock_timeout=5000'})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db
