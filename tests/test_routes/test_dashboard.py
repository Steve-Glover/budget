from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.category import Category
from app.models.enums import TransactionType, Variability, Frequency
from app.models.user import User
from app.services import analysis_service, budget_service, transaction_service

TODAY = date.today()


@pytest.fixture
def user(session):
    u = User(
        username="dashuser",
        email="dash@test.com",
        password_hash="h",
        first_name="D",
        last_name="U",
    )
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def categories(session):
    food = Category(name="Food")
    session.add(food)
    session.flush()
    groceries = Category(name="Groceries", parent_id=food.id)
    session.add(groceries)
    session.flush()
    return {"food": food, "groceries": groceries}


@pytest.fixture
def current_period(session, user):
    """Period that contains today."""
    start = TODAY.replace(day=1)
    end = start.replace(month=start.month % 12 + 1, day=1) - timedelta(days=1)
    return analysis_service.create_period("Current Month", start, end, user.id)


@pytest.fixture
def past_period(session, user):
    """Period entirely in the past."""
    start = date(2026, 1, 1)
    end = date(2026, 1, 31)
    return analysis_service.create_period("Jan 2026", start, end, user.id)


class TestDashboardEmpty:
    def test_no_periods_shows_prompt(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"No analysis periods" in resp.data
        assert b"Create a period" in resp.data


class TestDashboardPeriodDetection:
    def test_auto_detects_current_period(self, client, current_period):
        resp = client.get("/")
        assert resp.status_code == 200
        assert current_period.name.encode() in resp.data

    def test_falls_back_to_most_recent(self, client, past_period):
        """When no period contains today, use most recent."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert past_period.name.encode() in resp.data

    def test_period_id_override(self, client, current_period, past_period):
        resp = client.get(f"/?period_id={past_period.id}")
        assert resp.status_code == 200
        assert past_period.name.encode() in resp.data

    def test_period_selector_rendered(self, client, current_period, past_period):
        resp = client.get("/")
        assert b"period_id" in resp.data
        assert current_period.name.encode() in resp.data
        assert past_period.name.encode() in resp.data


class TestDashboardContent:
    @pytest.fixture
    def period_with_data(self, session, user, current_period, categories):
        budget_service.create_budget_item(
            "Grocery Budget",
            Variability.VARIABLE,
            Frequency.MONTHLY,
            current_period.start_date,
            Decimal("500.00"),
            user.id,
            categories["food"].id,
            subcategory_id=categories["groceries"].id,
        )
        transaction_service.create_transaction(
            current_period.start_date + timedelta(days=1),
            "Superstore",
            Decimal("200.00"),
            TransactionType.DEBIT,
            user.id,
            category_id=categories["food"].id,
            subcategory_id=categories["groceries"].id,
        )
        analysis_service.recompute_analysis(current_period.id, user.id)
        return current_period

    def test_shows_summary_cards(self, client, period_with_data):
        resp = client.get("/")
        assert b"Budgeted" in resp.data
        assert b"Spent" in resp.data
        assert b"Variance" in resp.data

    def test_shows_category_bars(self, client, period_with_data):
        resp = client.get("/")
        assert b"Food" in resp.data
        assert b"500.00" in resp.data
        assert b"200.00" in resp.data

    def test_shows_recent_transactions(self, client, period_with_data):
        resp = client.get("/")
        assert b"Superstore" in resp.data

    def test_full_report_link_present(self, client, period_with_data):
        resp = client.get("/")
        assert b"Full Report" in resp.data

    def test_no_analysis_data_shows_recompute_prompt(self, client, current_period):
        resp = client.get("/")
        assert b"No analysis data" in resp.data
