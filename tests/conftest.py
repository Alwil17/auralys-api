import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force use of test settings
os.environ["APP_ENV"] = "test"

# Import necessary modules
from app.db.base import Base, get_db
from app.main import app
from app.core.config_test import test_settings
from tests.fixtures.mood_fixtures import *
from tests.utils.test_data_seeder import TestDataSeeder
from app.core.security import create_access_token

# Create in-memory SQLite database for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Override the get_db dependency for tests
@pytest.fixture(scope="function")
def override_get_db(db):
    # Patch app's settings to use test_settings
    from app.core import config

    original_settings = config.settings
    config.settings = test_settings

    def _get_db_override():
        try:
            yield db
        finally:
            db.rollback()

    app.dependency_overrides[get_db] = _get_db_override
    yield

    # Restore original settings
    config.settings = original_settings
    app.dependency_overrides.clear()


# Client fixture that uses test database
@pytest.fixture(scope="function")
def client(override_get_db):
    with TestClient(app) as test_client:
        yield test_client


# Store tokens that need to be shared between test modules
pytest.user_refresh_token = None


@pytest.fixture(scope="function")
def user_auth(client):
    """
    Returns user auth headers when needed.
    """
    user_payload = {
        "name": "Test User",
        "email": "testuser@example.com",
        "password": "testpassword",
    }
    # Try to create user, ignore if already exists
    client.post("/auth/register", json=user_payload)

    form_data = {
        "username": user_payload["email"],
        "password": user_payload["password"],
    }
    response = client.post("/auth/token", data=form_data)
    assert response.status_code == 200, response.text
    token_data = response.json()
    pytest.user_refresh_token = token_data["refresh_token"]
    return {
        "headers": {"Authorization": f"Bearer {token_data['access_token']}"},
        "refresh_token": token_data["refresh_token"],
    }


@pytest.fixture
def test_data_seeder(db: Session) -> TestDataSeeder:
    """Fixture pour le seeder de données de test"""
    return TestDataSeeder(db)


@pytest.fixture
def test_user_with_consent(db: Session, test_data_seeder: TestDataSeeder) -> User:
    """Utilisateur de test avec consentement"""
    return test_data_seeder.create_test_user(email="consent@test.com", consent=True)


@pytest.fixture
def test_user_no_consent(db: Session, test_data_seeder: TestDataSeeder) -> User:
    """Utilisateur de test sans consentement"""
    return test_data_seeder.create_test_user(email="noconsent@test.com", consent=False)


@pytest.fixture
def auth_headers_no_consent(test_user_no_consent: User) -> Dict[str, str]:
    """Headers d'authentification pour utilisateur sans consentement"""
    # Simulate JWT token creation for user without consent
    token = create_access_token(data={"sub": test_user_no_consent.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_with_consent(test_user_with_consent: User) -> Dict[str, str]:
    """Headers d'authentification pour utilisateur avec consentement"""
    token = create_access_token(data={"sub": test_user_with_consent.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_other_user(
    db: Session, test_data_seeder: TestDataSeeder
) -> Dict[str, str]:
    """Headers d'authentification pour un autre utilisateur"""
    other_user = test_data_seeder.create_test_user(
        email="other@test.com", name="Other User", consent=True
    )
    token = create_access_token(data={"sub": other_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def db():
    """Database session fixture"""
    # Create in-memory SQLite database for tests
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create a db session
    db_session = TestingSessionLocal()

    # Override get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides.clear()
