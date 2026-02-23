from datetime import date
from decimal import Decimal
from unittest import TestCase

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    User, Vendor, Account, Category, BudgetedExpense,
    Transaction, AnalysisPeriod, ExpenseAnalysis,
)
from app.models.enums import AccountType, TransactionType, Variability, Frequency


def _make_user(session, username="testuser", email="test@example.com"):
    user = User(
        username=username, email=email, password_hash="hash",
        first_name="Test", last_name="User",
    )
    session.add(user)
    session.flush()
    return user


def _make_vendor(session, name="Chase", short_name="Chase"):
    vendor = Vendor(name=name, short_name=short_name)
    session.add(vendor)
    session.flush()
    return vendor


def _make_category(session, name="Housing", parent=None):
    cat = Category(name=name, parent_id=parent.id if parent else None)
    session.add(cat)
    session.flush()
    return cat


class TestUserModel:
    def test_create_user_defaults(self, session):
        user = _make_user(session)
        assert user.id is not None
        assert user.is_active is True
        assert user.created_at is not None

    def test_username_unique(self, session):
        _make_user(session)
        with pytest.raises(IntegrityError):
            _make_user(session, username="testuser", email="other@example.com")

    def test_email_unique(self, session):
        _make_user(session)
        with pytest.raises(IntegrityError):
            _make_user(session, username="other", email="test@example.com")


class TestVendorModel:
    def test_create_vendor(self, session):
        vendor = _make_vendor(session)
        assert vendor.id is not None
        assert repr(vendor) == "<Vendor Chase>"

    def test_name_unique(self, session):
        _make_vendor(session)
        with pytest.raises(IntegrityError):
            _make_vendor(session, name="Chase", short_name="CH2")


class TestAccountModel:
    def test_create_account_defaults(self, session):
        user = _make_user(session)
        vendor = _make_vendor(session)
        acct = Account(
            name="Freedom", vendor_id=vendor.id, owner_id=user.id,
            account_type=AccountType.CREDIT_CARD.value,
        )
        session.add(acct)
        session.flush()
        assert acct.balance == Decimal("0.00")
        assert acct.is_active is True
        assert acct.account_type_enum == AccountType.CREDIT_CARD

    def test_account_relationships(self, session):
        user = _make_user(session)
        vendor = _make_vendor(session)
        acct = Account(
            name="Checking", vendor_id=vendor.id, owner_id=user.id,
            account_type=AccountType.CHECKING.value,
        )
        session.add(acct)
        session.flush()
        assert acct.owner.username == "testuser"
        assert acct.vendor.name == "Chase"


class TestCategoryModel:
    def test_top_level_category(self, session):
        cat = _make_category(session, "Housing")
        assert cat.is_top_level is True
        assert cat.parent_id is None

    def test_subcategory(self, session):
        parent = _make_category(session, "Housing")
        child = _make_category(session, "Mortgage", parent=parent)
        assert child.is_top_level is False
        assert child.parent.name == "Housing"

    def test_duplicate_name_under_same_parent(self, session):
        parent = _make_category(session, "Housing")
        _make_category(session, "Mortgage", parent=parent)
        with pytest.raises(IntegrityError):
            _make_category(session, "Mortgage", parent=parent)

    def test_same_name_different_parent(self, session):
        p1 = _make_category(session, "Housing")
        p2 = _make_category(session, "Transportation")
        _make_category(session, "Insurance", parent=p1)
        _make_category(session, "Insurance", parent=p2)
        session.flush()  # should not raise


class TestBudgetedExpenseModel:
    def test_create_expense(self, session):
        user = _make_user(session)
        cat = _make_category(session, "Housing")
        sub = _make_category(session, "Mortgage", parent=cat)
        exp = BudgetedExpense(
            payee="Wells Fargo", variability=Variability.FIXED.value,
            frequency=Frequency.MONTHLY.value, date_scheduled=date(2026, 3, 1),
            budgeted_amount=Decimal("1500.00"), user_id=user.id,
            category_id=cat.id, subcategory_id=sub.id,
        )
        session.add(exp)
        session.flush()
        assert exp.variability_enum == Variability.FIXED
        assert exp.frequency_enum == Frequency.MONTHLY
        assert exp.is_active is True


class TestTransactionModel:
    def test_create_transaction(self, session):
        user = _make_user(session)
        txn = Transaction(
            transaction_date=date(2026, 2, 15), payee="Grocery Store",
            amount=Decimal("52.30"), transaction_type=TransactionType.DEBIT.value,
            user_id=user.id,
        )
        session.add(txn)
        session.flush()
        assert txn.transaction_type_enum == TransactionType.DEBIT
        assert txn.debit_account_id is None
        assert txn.category_id is None


class TestAnalysisPeriodModel:
    def test_create_period(self, session):
        user = _make_user(session)
        period = AnalysisPeriod(
            name="January 2026", start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31), user_id=user.id,
        )
        session.add(period)
        session.flush()
        assert period.id is not None

    def test_unique_user_period_name(self, session):
        user = _make_user(session)
        session.add(AnalysisPeriod(
            name="Q1", start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31), user_id=user.id,
        ))
        session.flush()
        with pytest.raises(IntegrityError):
            session.add(AnalysisPeriod(
                name="Q1", start_date=date(2026, 1, 1),
                end_date=date(2026, 3, 31), user_id=user.id,
            ))
            session.flush()


class TestExpenseAnalysisModel:
    def test_create_analysis(self, session):
        user = _make_user(session)
        cat = _make_category(session, "Food")
        period = AnalysisPeriod(
            name="Feb 2026", start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28), user_id=user.id,
        )
        session.add(period)
        session.flush()
        ea = ExpenseAnalysis(
            period_id=period.id, user_id=user.id, category_id=cat.id,
            budgeted_amount=Decimal("500.00"), actual_amount=Decimal("450.00"),
            variance=Decimal("50.00"), transaction_count=12,
        )
        session.add(ea)
        session.flush()
        assert ea.variance == Decimal("50.00")
        assert ea.subcategory_id is None


class TestEnums:
    """Verify enum values match the schema spec."""
    def test_account_types(self):
        expected = {"checking", "savings", "credit_card", "investment", "loan", "other"}
        assert {e.value for e in AccountType} == expected

    def test_transaction_types(self):
        assert {e.value for e in TransactionType} == {"debit", "credit"}

    def test_variability(self):
        assert {e.value for e in Variability} == {"fixed", "variable"}

    def test_frequency(self):
        expected = {"weekly", "biweekly", "monthly", "quarterly", "annual", "one_time"}
        assert {e.value for e in Frequency} == expected
