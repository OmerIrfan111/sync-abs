import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SQLAlchemySession
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User
from app.core.security import get_password_hash, create_access_token
from app.api.deps import get_current_user

# Use SQLite for fast in-memory unit/integration test isolation
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = SQLAlchemySession(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def test_admin_user(db_session):
    user = User(
        email="testadmin@syncplatform.io",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test Admin",
        is_active=True,
        is_superuser=True,
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def client(db_session, test_admin_user):
    """
    Every route except /auth now requires a logged-in user (Phase 5: staff
    roles/permissions). Tests represent the common case — an already-logged-in
    staff member — by overriding get_current_user to return a real admin
    test user by default, rather than requiring every single test call site
    to manually attach a bearer token. Tests that specifically need to
    exercise unauthenticated/unauthorized behavior should clear this
    override (app.dependency_overrides.pop(get_current_user, None)) or use a
    non-admin user via a role-specific override instead.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_user():
        return test_admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def admin_auth_headers(test_admin_user):
    token = create_access_token(test_admin_user.id)
    return {"Authorization": f"Bearer {token}"}
