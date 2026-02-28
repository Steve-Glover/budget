from datetime import date
from decimal import Decimal

import pytest

from app.models.category import Category
from app.models.enums import TransactionType, Variability, Frequency
from app.services import analysis_service, budget_service, transaction_service


@pytest.fixture
def period(session, user):
    return analysis_service.create_period(
        "Feb 2026", date(2026, 2, 1), date(2026, 2, 28), user.id
    )


class TestListPeriods:
    def test_empty_list(self, logged_in_client):
        resp = logged_in_client.get("/analysis/")
        assert resp.status_code == 200
        assert b"No analysis periods yet" in resp.data

    def test_with_periods(self, logged_in_client, period):
        resp = logged_in_client.get("/analysis/")
        assert resp.status_code == 200
        assert b"Feb 2026" in resp.data


class TestCreatePeriod:
    def test_get_form(self, logged_in_client):
        resp = logged_in_client.get("/analysis/create")
        assert resp.status_code == 200
        assert b"Create Period" in resp.data

    def test_post_valid(self, logged_in_client, user):
        resp = logged_in_client.post(
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
    def test_post_invalid(self, logged_in_client, data, error_fragment):
        resp = logged_in_client.post("/analysis/create", data=data)
        assert resp.status_code == 200
        assert error_fragment in resp.data


class TestEditPeriod:
    def test_get_form(self, logged_in_client, period):
        resp = logged_in_client.get(f"/analysis/{period.id}/edit")
        assert resp.status_code == 200
        assert b"Edit Period" in resp.data

    def test_post_valid(self, logged_in_client, period):
        resp = logged_in_client.post(
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

    def test_nonexistent(self, logged_in_client):
        resp = logged_in_client.get("/analysis/9999/edit", follow_redirects=True)
        assert b"Period not found" in resp.data


class TestDeletePeriod:
    def test_delete(self, logged_in_client, period):
        resp = logged_in_client.post(
            f"/analysis/{period.id}/delete",
            follow_redirects=True,
        )
        assert b"Period deleted" in resp.data

    def test_delete_nonexistent(self, logged_in_client):
        resp = logged_in_client.post("/analysis/9999/delete", follow_redirects=True)
        assert b"Period not found" in resp.data


@pytest.fixture
def categories(session):
    food = Category(name="Food")
    session.add(food)
    session.flush()
    groceries = Category(name="Groceries", parent_id=food.id)
    dining = Category(name="Dining Out", parent_id=food.id)
    session.add_all([groceries, dining])
    session.flush()
    return {"food": food, "groceries": groceries, "dining": dining}


@pytest.fixture
def period_with_data(session, user, period, categories):
    """Period that has been recomputed with grocery budget + transaction."""
    budget_service.create_budget_item(
        "Grocery Budget",
        Variability.VARIABLE,
        Frequency.MONTHLY,
        date(2026, 2, 1),
        Decimal("500.00"),
        user.id,
        categories["food"].id,
        subcategory_id=categories["groceries"].id,
    )
    transaction_service.create_transaction(
        date(2026, 2, 10),
        "Superstore",
        Decimal("350.00"),
        TransactionType.DEBIT,
        user.id,
        category_id=categories["food"].id,
        subcategory_id=categories["groceries"].id,
    )
    analysis_service.recompute_analysis(period.id, user.id)
    return period


class TestPeriodReport:
    def test_report_no_data(self, logged_in_client, period):
        resp = logged_in_client.get(f"/analysis/{period.id}/report")
        assert resp.status_code == 200
        assert b"No analysis data" in resp.data

    def test_report_nonexistent(self, logged_in_client):
        resp = logged_in_client.get("/analysis/9999/report", follow_redirects=True)
        assert b"Period not found" in resp.data

    def test_report_shows_category(self, logged_in_client, period_with_data):
        resp = logged_in_client.get(f"/analysis/{period_with_data.id}/report")
        assert resp.status_code == 200
        assert b"Food" in resp.data
        assert b"350.00" in resp.data
        assert b"500.00" in resp.data

    def test_report_shows_summary_cards(self, logged_in_client, period_with_data):
        resp = logged_in_client.get(f"/analysis/{period_with_data.id}/report")
        assert b"Budgeted" in resp.data
        assert b"Spent" in resp.data
        assert b"Variance" in resp.data

    def test_drill_down(self, logged_in_client, period_with_data, categories):
        resp = logged_in_client.get(
            f"/analysis/{period_with_data.id}/report?category_id={categories['food'].id}"
        )
        assert resp.status_code == 200
        assert b"Groceries" in resp.data

    def test_drill_down_shows_back_arrow(
        self, logged_in_client, period_with_data, categories
    ):
        resp = logged_in_client.get(
            f"/analysis/{period_with_data.id}/report?category_id={categories['food'].id}"
        )
        assert b"All Periods" in resp.data
        assert b"Food" in resp.data


class TestRecomputePeriod:
    def test_recompute_success(self, logged_in_client, period):
        resp = logged_in_client.post(
            f"/analysis/{period.id}/recompute",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"recomputed" in resp.data

    def test_recompute_nonexistent(self, logged_in_client):
        resp = logged_in_client.post("/analysis/9999/recompute", follow_redirects=True)
        assert b"Period not found" in resp.data
