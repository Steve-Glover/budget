"""Tests for account and budget deactivation routes."""

from datetime import date
from decimal import Decimal

import pytest

from app.models.enums import AccountType, Variability, Frequency
from app.services import account_service, budget_service


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


class TestDeactivateAccount:
    def test_deactivate_success(self, logged_in_client, user, vendor):
        acct = account_service.create_account(
            "MyAcct", vendor.id, AccountType.CHECKING, user.id
        )
        resp = logged_in_client.post(
            f"/accounts/{acct.id}/deactivate", follow_redirects=True
        )
        assert resp.status_code == 200
        assert b"Account deactivated" in resp.data
        acct = account_service.get_account(acct.id)
        assert acct.is_active is False

    def test_deactivate_nonexistent(self, logged_in_client, user):
        resp = logged_in_client.post("/accounts/9999/deactivate", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Account not found" in resp.data

    def test_deactivate_get_not_allowed(self, logged_in_client, user, vendor):
        acct = account_service.create_account(
            "MyAcct", vendor.id, AccountType.CHECKING, user.id
        )
        resp = logged_in_client.get(f"/accounts/{acct.id}/deactivate")
        assert resp.status_code == 405


class TestDeactivateBudget:
    def test_deactivate_success(self, logged_in_client, user, category):
        item = budget_service.create_budget_item(
            "MyBudget",
            Variability.FIXED,
            Frequency.MONTHLY,
            date(2026, 1, 1),
            Decimal("100.00"),
            user.id,
            category.id,
        )
        resp = logged_in_client.post(
            f"/budgets/{item.id}/deactivate", follow_redirects=True
        )
        assert resp.status_code == 200
        assert b"Budget item deactivated" in resp.data
        item = budget_service.get_budget_item(item.id)
        assert item.is_active is False

    def test_deactivate_nonexistent(self, logged_in_client, user):
        resp = logged_in_client.post("/budgets/9999/deactivate", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Budget item not found" in resp.data

    def test_deactivate_get_not_allowed(self, logged_in_client, user, category):
        item = budget_service.create_budget_item(
            "MyBudget",
            Variability.FIXED,
            Frequency.MONTHLY,
            date(2026, 1, 1),
            Decimal("100.00"),
            user.id,
            category.id,
        )
        resp = logged_in_client.get(f"/budgets/{item.id}/deactivate")
        assert resp.status_code == 405
