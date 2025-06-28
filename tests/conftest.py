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

# Create in-memory SQLite database for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Override the get_db dependency for testing
@pytest.fixture(scope="session")
def test_db():
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create a db session
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

    # Clean up database after tests
    Base.metadata.drop_all(bind=engine)


# Override the get_db dependency for tests
@pytest.fixture(scope="function")
def override_get_db(test_db):
    # Patch app's settings to use test_settings
    from app.core import config

    original_settings = config.settings
    config.settings = test_settings

    def _get_db_override():
        try:
            yield test_db
        finally:
            test_db.rollback()

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
