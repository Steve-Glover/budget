from datetime import date
from decimal import Decimal

import pytest

from app.models.category import Category
from app.models.enums import TransactionType, Variability, Frequency
from app.models.user import User
from app.services import analysis_service, transaction_service, budget_service


@pytest.fixture
def user(session):
    u = User(
        username="analysisuser",
        email="an@test.com",
        password_hash="h",
        first_name="A",
        last_name="U",
    )
    session.add(u)
    session.flush()
    return u


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


class TestPeriodCRUD:
    def test_create_and_get(self, session, user):
        period = analysis_service.create_period(
            "Feb 2026",
            date(2026, 2, 1),
            date(2026, 2, 28),
            user.id,
        )
        assert period.id is not None
        assert analysis_service.get_period(period.id).name == "Feb 2026"

    def test_get_nonexistent(self, session):
        assert analysis_service.get_period(9999) is None

    def test_list_for_user(self, session, user):
        analysis_service.create_period(
            "Jan", date(2026, 1, 1), date(2026, 1, 31), user.id
        )
        analysis_service.create_period(
            "Feb", date(2026, 2, 1), date(2026, 2, 28), user.id
        )
        periods = analysis_service.get_periods_for_user(user.id)
        assert len(periods) == 2
        assert periods[0].name == "Feb"  # desc order

    @pytest.mark.parametrize(
        "field,value",
        [
            ("name", "Updated"),
            ("start_date", date(2026, 3, 1)),
        ],
    )
    def test_update_fields(self, session, user, field, value):
        period = analysis_service.create_period(
            "Q1",
            date(2026, 1, 1),
            date(2026, 3, 31),
            user.id,
        )
        updated = analysis_service.update_period(period.id, **{field: value})
        assert getattr(updated, field) == value

    def test_update_nonexistent(self, session):
        assert analysis_service.update_period(9999, name="X") is None

    def test_delete(self, session, user):
        period = analysis_service.create_period(
            "Del",
            date(2026, 1, 1),
            date(2026, 1, 31),
            user.id,
        )
        assert analysis_service.delete_period(period.id) is True
        assert analysis_service.get_period(period.id) is None

    def test_delete_nonexistent(self, session):
        assert analysis_service.delete_period(9999) is False


class TestRecomputeAnalysis:
    def test_basic_recompute(self, session, user, categories):
        """Transactions + budgets in period produce correct analysis rows."""
        period = analysis_service.create_period(
            "Feb 2026",
            date(2026, 2, 1),
            date(2026, 2, 28),
            user.id,
        )
        # Budget: $500 for Food/Groceries
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
        # Actual: $350 in Food/Groceries (2 transactions)
        for amt in (Decimal("200.00"), Decimal("150.00")):
            transaction_service.create_transaction(
                date(2026, 2, 10),
                "Store",
                amt,
                TransactionType.DEBIT,
                user.id,
                category_id=categories["food"].id,
                subcategory_id=categories["groceries"].id,
            )

        results = analysis_service.recompute_analysis(period.id, user.id)
        assert len(results) == 1
        ea = results[0]
        assert ea.budgeted_amount == Decimal("500.00")
        assert ea.actual_amount == Decimal("350.00")
        assert ea.variance == Decimal("150.00")
        assert ea.transaction_count == 2

    def test_transactions_only_no_budget(self, session, user, categories):
        """Spending without a budget shows actual with zero budgeted."""
        period = analysis_service.create_period(
            "Feb 2026",
            date(2026, 2, 1),
            date(2026, 2, 28),
            user.id,
        )
        transaction_service.create_transaction(
            date(2026, 2, 5),
            "Restaurant",
            Decimal("75.00"),
            TransactionType.DEBIT,
            user.id,
            category_id=categories["food"].id,
            subcategory_id=categories["dining"].id,
        )
        results = analysis_service.recompute_analysis(period.id, user.id)
        assert len(results) == 1
        assert results[0].budgeted_amount == Decimal("0.00")
        assert results[0].actual_amount == Decimal("75.00")
        assert results[0].variance == Decimal("-75.00")

    def test_budget_only_no_transactions(self, session, user, categories):
        """Budget with no spending shows budgeted with zero actual."""
        period = analysis_service.create_period(
            "Feb 2026",
            date(2026, 2, 1),
            date(2026, 2, 28),
            user.id,
        )
        budget_service.create_budget_item(
            "Groceries",
            Variability.VARIABLE,
            Frequency.MONTHLY,
            date(2026, 2, 1),
            Decimal("400.00"),
            user.id,
            categories["food"].id,
            subcategory_id=categories["groceries"].id,
        )
        results = analysis_service.recompute_analysis(period.id, user.id)
        assert len(results) == 1
        assert results[0].actual_amount == Decimal("0.00")
        assert results[0].variance == Decimal("400.00")

    def test_credits_excluded(self, session, user, categories):
        """Credit transactions are not counted as spending."""
        period = analysis_service.create_period(
            "Feb 2026",
            date(2026, 2, 1),
            date(2026, 2, 28),
            user.id,
        )
        transaction_service.create_transaction(
            date(2026, 2, 10),
            "Refund",
            Decimal("50.00"),
            TransactionType.CREDIT,
            user.id,
            category_id=categories["food"].id,
            subcategory_id=categories["groceries"].id,
        )
        results = analysis_service.recompute_analysis(period.id, user.id)
        assert len(results) == 0  # no debit transactions

    def test_out_of_range_excluded(self, session, user, categories):
        """Transactions outside the period date range are excluded."""
        period = analysis_service.create_period(
            "Feb 2026",
            date(2026, 2, 1),
            date(2026, 2, 28),
            user.id,
        )
        transaction_service.create_transaction(
            date(2026, 1, 15),
            "Old",
            Decimal("100.00"),
            TransactionType.DEBIT,
            user.id,
            category_id=categories["food"].id,
            subcategory_id=categories["groceries"].id,
        )
        results = analysis_service.recompute_analysis(period.id, user.id)
        assert len(results) == 0

    def test_recompute_replaces_old_rows(self, session, user, categories):
        """Running recompute twice replaces previous analysis rows."""
        period = analysis_service.create_period(
            "Feb 2026",
            date(2026, 2, 1),
            date(2026, 2, 28),
            user.id,
        )
        transaction_service.create_transaction(
            date(2026, 2, 5),
            "Store",
            Decimal("100.00"),
            TransactionType.DEBIT,
            user.id,
            category_id=categories["food"].id,
            subcategory_id=categories["groceries"].id,
        )
        analysis_service.recompute_analysis(period.id, user.id)
        # Add another transaction and recompute
        transaction_service.create_transaction(
            date(2026, 2, 15),
            "Store",
            Decimal("50.00"),
            TransactionType.DEBIT,
            user.id,
            category_id=categories["food"].id,
            subcategory_id=categories["groceries"].id,
        )
        results = analysis_service.recompute_analysis(period.id, user.id)
        assert len(results) == 1
        assert results[0].actual_amount == Decimal("150.00")
        assert results[0].transaction_count == 2

    def test_nonexistent_period(self, session, user):
        assert analysis_service.recompute_analysis(9999, user.id) == []
