from app import create_app
from app.extensions import db as _db
from app.models.user import User


class TestErrorPages:
    def test_404_returns_custom_template(self, logged_in_client):
        resp = logged_in_client.get("/nonexistent-page")
        assert resp.status_code == 404
        assert b"404" in resp.data
        assert b"doesn" in resp.data
        assert b"t exist" in resp.data

    def test_404_extends_base(self, logged_in_client):
        resp = logged_in_client.get("/nonexistent-page")
        assert b"Budget" in resp.data
        assert b"navbar" in resp.data

    def test_500_returns_custom_template(self):
        """Use a separate app with exception propagation disabled."""
        app = create_app("testing")
        app.config["PROPAGATE_EXCEPTIONS"] = False

        @app.route("/test-500")
        def trigger_500():
            raise RuntimeError("test error")

        with app.app_context():
            _db.create_all()
            u = User(
                username="err500user",
                email="err500@test.com",
                first_name="E",
                last_name="U",
            )
            u.set_password("password123")
            _db.session.add(u)
            _db.session.commit()

            client = app.test_client()
            client.post(
                "/auth/login",
                data={"username": "err500user", "password": "password123"},
            )
            resp = client.get("/test-500")
            assert resp.status_code == 500
            assert b"500" in resp.data
            assert b"Something went wrong" in resp.data

            _db.drop_all()
