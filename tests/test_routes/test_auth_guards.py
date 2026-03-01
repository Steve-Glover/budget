"""Tests for @login_required redirects and cross-user ownership enforcement."""

from datetime import date
from decimal import Decimal

import pytest

from app.models.enums import AccountType, TransactionType, Variability, Frequency
from app.models.user import User
from app.services import (
    account_service,
    budget_service,
    transaction_service,
    analysis_service,
)


class TestAnonymousRedirects:
    """Anonymous users must be redirected to login for all protected routes."""

    @pytest.mark.parametrize(
        "url",
        [
            "/",
            "/accounts/",
            "/accounts/create",
            "/budgets/",
            "/budgets/create",
            "/transactions/",
            "/transactions/create",
            "/transactions/import",
            "/analysis/",
            "/analysis/create",
        ],
    )
    def test_anonymous_get_redirects(self, client, url):
        resp = client.get(url, follow_redirects=False)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]

    @pytest.mark.parametrize(
        "url",
        [
            "/accounts/1/deactivate",
            "/budgets/1/deactivate",
            "/transactions/1/delete",
            "/analysis/1/delete",
            "/analysis/1/recompute",
        ],
    )
    def test_anonymous_post_redirects(self, client, url):
        resp = client.post(url, follow_redirects=False)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]

    def test_anonymous_redirect_preserves_next(self, client):
        resp = client.get("/accounts/", follow_redirects=False)
        assert "next" in resp.headers["Location"]


@pytest.fixture
def other_user(session):
    u = User(
        username="otheruser",
        email="other@example.com",
        first_name="Other",
        last_name="User",
    )
    u.set_password("password123")
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def vendor(session):
    from app.models.vendor import Vendor

    v = Vendor(name="TestBank", short_name="TB")
    session.add(v)
    session.commit()
    return v


@pytest.fixture
def category(session):
    from app.models.category import Category

    c = Category(name="TestCat")
    session.add(c)
    session.commit()
    return c


class TestCrossUserOwnership:
    """Logged-in user A must not access user B's resources."""

    def test_cannot_edit_other_users_account(
        self, logged_in_client, other_user, vendor
    ):
        acct = account_service.create_account(
            "OtherAcct", vendor.id, AccountType.CHECKING, other_user.id
        )
        resp = logged_in_client.get(f"/accounts/{acct.id}/edit", follow_redirects=True)
        assert b"Account not found" in resp.data

    def test_cannot_edit_other_users_budget(
        self, logged_in_client, other_user, category
    ):
        item = budget_service.create_budget_item(
            "OtherBudget",
            Variability.FIXED,
            Frequency.MONTHLY,
            date(2026, 1, 1),
            Decimal("100.00"),
            other_user.id,
            category.id,
        )
        resp = logged_in_client.get(f"/budgets/{item.id}/edit", follow_redirects=True)
        assert b"Budget item not found" in resp.data

    def test_cannot_edit_other_users_transaction(
        self, logged_in_client, other_user, category
    ):
        txn = transaction_service.create_transaction(
            date(2026, 2, 10),
            "OtherPayee",
            Decimal("50.00"),
            TransactionType.DEBIT,
            other_user.id,
        )
        resp = logged_in_client.get(
            f"/transactions/{txn.id}/edit", follow_redirects=True
        )
        assert b"Transaction not found" in resp.data

    def test_cannot_delete_other_users_transaction(
        self, logged_in_client, other_user, category
    ):
        txn = transaction_service.create_transaction(
            date(2026, 2, 10),
            "OtherPayee",
            Decimal("50.00"),
            TransactionType.DEBIT,
            other_user.id,
        )
        resp = logged_in_client.post(
            f"/transactions/{txn.id}/delete", follow_redirects=True
        )
        assert b"Transaction not found" in resp.data

    def test_cannot_view_other_users_period_report(self, logged_in_client, other_user):
        period = analysis_service.create_period(
            "OtherPeriod", date(2026, 1, 1), date(2026, 1, 31), other_user.id
        )
        resp = logged_in_client.get(
            f"/analysis/{period.id}/report", follow_redirects=True
        )
        assert b"Period not found" in resp.data

    def test_cannot_deactivate_other_users_account(
        self, logged_in_client, other_user, vendor
    ):
        acct = account_service.create_account(
            "OtherAcct", vendor.id, AccountType.CHECKING, other_user.id
        )
        resp = logged_in_client.post(
            f"/accounts/{acct.id}/deactivate", follow_redirects=True
        )
        assert b"Account not found" in resp.data

    def test_cannot_deactivate_other_users_budget(
        self, logged_in_client, other_user, category
    ):
        item = budget_service.create_budget_item(
            "OtherBudget",
            Variability.FIXED,
            Frequency.MONTHLY,
            date(2026, 1, 1),
            Decimal("100.00"),
            other_user.id,
            category.id,
        )
        resp = logged_in_client.post(
            f"/budgets/{item.id}/deactivate", follow_redirects=True
        )
        assert b"Budget item not found" in resp.data

    def test_cannot_delete_other_users_period(self, logged_in_client, other_user):
        period = analysis_service.create_period(
            "OtherPeriod", date(2026, 1, 1), date(2026, 1, 31), other_user.id
        )
        resp = logged_in_client.post(
            f"/analysis/{period.id}/delete", follow_redirects=True
        )
        assert b"Period not found" in resp.data
