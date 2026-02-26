from datetime import date

import pytest

from app.models.user import User
from app.services import analysis_service


@pytest.fixture
def user(session):
    u = User(
        username="routeuser",
        email="route@test.com",
        password_hash="h",
        first_name="R",
        last_name="U",
    )
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def period(session, user):
    return analysis_service.create_period(
        "Feb 2026", date(2026, 2, 1), date(2026, 2, 28), user.id
    )


class TestListPeriods:
    def test_empty_list(self, client):
        resp = client.get("/analysis/")
        assert resp.status_code == 200
        assert b"No analysis periods yet" in resp.data

    def test_with_periods(self, client, period):
        resp = client.get("/analysis/")
        assert resp.status_code == 200
        assert b"Feb 2026" in resp.data


class TestCreatePeriod:
    def test_get_form(self, client):
        resp = client.get("/analysis/create")
        assert resp.status_code == 200
        assert b"Create Period" in resp.data

    def test_post_valid(self, client, user):
        resp = client.post(
            "/analysis/create",
            data={
                "name": "March 2026",
                "start_date": "2026-03-01",
                "end_date": "2026-03-31",
            },
            follow_redirects=True,
        )
        assert b"Analysis period created" in resp.data
        assert b"March 2026" in resp.data

    @pytest.mark.parametrize(
        "data,error_fragment",
        [
            (
                {"name": "", "start_date": "2026-03-01", "end_date": "2026-03-31"},
                b"This field is required",
            ),
            (
                {"name": "Bad", "start_date": "2026-03-31", "end_date": "2026-03-01"},
                b"End date must be after",
            ),
        ],
        ids=["missing_name", "start_after_end"],
    )
    def test_post_invalid(self, client, data, error_fragment):
        resp = client.post("/analysis/create", data=data)
        assert resp.status_code == 200
        assert error_fragment in resp.data


class TestEditPeriod:
    def test_get_form(self, client, period):
        resp = client.get(f"/analysis/{period.id}/edit")
        assert resp.status_code == 200
        assert b"Edit Period" in resp.data

    def test_post_valid(self, client, period):
        resp = client.post(
            f"/analysis/{period.id}/edit",
            data={
                "name": "Updated",
                "start_date": "2026-02-01",
                "end_date": "2026-02-28",
            },
            follow_redirects=True,
        )
        assert b"Period updated" in resp.data
        assert b"Updated" in resp.data

    def test_nonexistent(self, client):
        resp = client.get("/analysis/9999/edit", follow_redirects=True)
        assert b"Period not found" in resp.data


class TestDeletePeriod:
    def test_delete(self, client, period):
        resp = client.post(
            f"/analysis/{period.id}/delete",
            follow_redirects=True,
        )
        assert b"Period deleted" in resp.data

    def test_delete_nonexistent(self, client):
        resp = client.post("/analysis/9999/delete", follow_redirects=True)
        assert b"Period not found" in resp.data
