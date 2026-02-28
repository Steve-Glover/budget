import pytest

from app import create_app
from app.extensions import db as _db
from app.models.user import User


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def session(db):
    yield db.session


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(session):
    """Create a test user and return it."""
    u = User(
        username="testuser",
        email="test@example.com",
        first_name="Test",
        last_name="User",
    )
    u.set_password("password123")
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def logged_in_client(client, user):
    """A test client with an authenticated session."""
    client.post(
        "/auth/login",
        data={"username": "testuser", "password": "password123"},
    )
    return client
