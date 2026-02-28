from app.models.user import User


class TestLogin:
    def test_login_page_renders(self, client):
        resp = client.get("/auth/login")
        assert resp.status_code == 200
        assert b"Login" in resp.data

    def test_login_success_redirects_to_dashboard(self, client, user):
        resp = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "password123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/" in resp.headers["Location"]

    def test_login_invalid_password(self, client, user):
        resp = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "wrong"},
            follow_redirects=True,
        )
        assert b"Invalid username or password" in resp.data

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/auth/login",
            data={"username": "nobody", "password": "password123"},
            follow_redirects=True,
        )
        assert b"Invalid username or password" in resp.data

    def test_login_preserves_next(self, client, user):
        resp = client.post(
            "/auth/login?next=/accounts/",
            data={"username": "testuser", "password": "password123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/accounts/" in resp.headers["Location"]

    def test_login_rejects_external_next(self, client, user):
        resp = client.post(
            "/auth/login?next=https://evil.com/steal",
            data={"username": "testuser", "password": "password123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "evil.com" not in resp.headers["Location"]

    def test_login_redirects_if_authenticated(self, logged_in_client):
        resp = logged_in_client.get("/auth/login", follow_redirects=False)
        assert resp.status_code == 302


class TestLogout:
    def test_logout_post_succeeds(self, logged_in_client):
        resp = logged_in_client.post("/auth/logout", follow_redirects=True)
        assert b"You have been logged out" in resp.data

    def test_logout_get_returns_405(self, logged_in_client):
        resp = logged_in_client.get("/auth/logout")
        assert resp.status_code == 405


class TestRegistration:
    def test_register_page_renders(self, client):
        resp = client.get("/auth/register")
        assert resp.status_code == 200
        assert b"Register" in resp.data

    def test_register_success(self, client, session):
        resp = client.post(
            "/auth/register",
            data={
                "username": "newuser",
                "email": "new@example.com",
                "first_name": "New",
                "last_name": "User",
                "password": "securepass1",
                "password_confirm": "securepass1",
            },
            follow_redirects=True,
        )
        assert b"Registration successful" in resp.data
        assert User.query.filter_by(username="newuser").first() is not None

    def test_register_duplicate_username(self, client, user):
        resp = client.post(
            "/auth/register",
            data={
                "username": "testuser",
                "email": "other@example.com",
                "first_name": "Other",
                "last_name": "User",
                "password": "securepass1",
                "password_confirm": "securepass1",
            },
            follow_redirects=True,
        )
        assert b"Username already taken" in resp.data

    def test_register_duplicate_email(self, client, user):
        resp = client.post(
            "/auth/register",
            data={
                "username": "otheruser",
                "email": "test@example.com",
                "first_name": "Other",
                "last_name": "User",
                "password": "securepass1",
                "password_confirm": "securepass1",
            },
            follow_redirects=True,
        )
        assert b"Email already registered" in resp.data

    def test_register_disabled_returns_404(self, app, client):
        app.config["REGISTRATION_ENABLED"] = False
        resp = client.get("/auth/register")
        assert resp.status_code == 404

    def test_register_redirects_if_authenticated(self, logged_in_client):
        resp = logged_in_client.get("/auth/register", follow_redirects=False)
        assert resp.status_code == 302
