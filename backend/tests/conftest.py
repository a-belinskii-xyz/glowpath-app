import re
from collections.abc import Generator

import pytest
from app.api.deps import get_email_service, get_storage_service
from app.config import settings
from app.db.session import get_db
from app.main import app
from app.services.email_service import EmailService, SentEmail
from app.services.storage import FakeStorage, ObjectStorage
from fastapi.testclient import TestClient
from pgvector.psycopg import register_vector
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from tests.db_safety import assert_safe_test_database, get_test_database_url

TEST_DATABASE_URL = get_test_database_url()


@pytest.fixture(autouse=True)
def _disable_embeddings_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid downloading fastembed models during the default test suite."""
    monkeypatch.setattr(settings, "embedding_enabled", False)


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_database_only() -> None:
    assert_safe_test_database(TEST_DATABASE_URL)


def _database_available() -> bool:
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
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

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> None:
        del html_body
        self._outbox.append(SentEmail(to=to, subject=subject, body=body))


def extract_token_from_email(body: str) -> str:
    match = re.search(r"(?:verify-email|reset-password)\?token=([^\s&]+)", body)
    if match is not None:
        return match.group(1)
    raise AssertionError(f"Token not found in email body: {body}")


def register_verify_and_login(
    auth_client: TestClient,
    mailer: FakeEmailService,
    email: str,
    *,
    password: str = "password123",
) -> str:
    register_response = auth_client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "password_confirm": password},
    )
    assert register_response.status_code == 201
    token = extract_token_from_email(mailer.outbox[-1].body)
    verify_response = auth_client.get(f"/v1/auth/verify-email?token={token}")
    assert verify_response.status_code == 200
    login_response = auth_client.post(
        "/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def db_engine():
    if not _database_available():
        pytest.skip("PostgreSQL is not available for auth integration tests")
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

    @event.listens_for(engine, "connect")
    def _register_vector(dbapi_connection: object, _connection_record: object) -> None:
        register_vector(dbapi_connection)

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
def storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def auth_client(
    db: Session,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    def override_get_email_service() -> EmailService:
        return mailer

    def override_get_storage_service() -> ObjectStorage:
        return storage

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_service] = override_get_email_service
    app.dependency_overrides[get_storage_service] = override_get_storage_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
