import re
from collections.abc import Generator

import pytest
from app.api.deps import get_email_service
from app.config import settings
from app.db.session import get_db
from app.main import app
from app.services.email_service import EmailService, SentEmail
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


def _database_available() -> bool:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        return False
    finally:
        engine.dispose()
    return True


class FakeEmailService(EmailService):
    def __init__(self) -> None:
        super().__init__()
        self._outbox: list[SentEmail] = []

    @property
    def outbox(self) -> list[SentEmail]:
        return list(self._outbox)

    def clear_outbox(self) -> None:
        self._outbox.clear()

    def _send(self, *, to: str, subject: str, body: str) -> None:
        self._outbox.append(SentEmail(to=to, subject=subject, body=body))


def extract_token_from_email(body: str) -> str:
    match = re.search(r"(?:verify-email|reset-password)\?token=([^\s&]+)", body)
    if match is not None:
        return match.group(1)
    raise AssertionError(f"Token not found in email body: {body}")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def db_engine():
    if not _database_available():
        pytest.skip("PostgreSQL is not available for auth integration tests")
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db(db_engine) -> Generator[Session, None, None]:
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def mailer() -> FakeEmailService:
    return FakeEmailService()


@pytest.fixture
def auth_client(db: Session, mailer: FakeEmailService) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    def override_get_email_service() -> EmailService:
        return mailer

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_service] = override_get_email_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
