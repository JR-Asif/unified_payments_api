import os
import pytest
import fakeredis
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
import app.utils.idempotency as idempotency_module


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:password@localhost:5433/payments_db_test",
)
ADMIN_DATABASE_URL = os.getenv(
    "ADMIN_DATABASE_URL",
    "postgresql+psycopg://postgres:password@localhost:5433/postgres",
)


@pytest.fixture(scope="session")
def test_engine():
    """Set up the test database schema once per session."""
    admin_engine = create_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        existing = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'payments_db_test'")
        ).scalar()
        if not existing:
            conn.execute(text("CREATE DATABASE payments_db_test"))
    admin_engine.dispose()

    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Per-test DB session; truncates between tests for isolation."""
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.execute(text("TRUNCATE refunds, payments CASCADE"))
        session.commit()
        session.close()


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """Swap Redis for an in-memory fake during tests."""
    fake = fakeredis.FakeStrictRedis(decode_responses=True)
    monkeypatch.setattr(idempotency_module, "redis_client", fake)


@pytest.fixture
def client(db_session):
    """TestClient with the DB dependency overridden to the test session."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
