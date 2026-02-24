from datetime import date
from decimal import Decimal

import pytest

from app.models.category import Category
from app.models.enums import Variability, Frequency
from app.models.user import User
from app.services import budget_service


@pytest.fixture
def user_and_category(session):
    user = User(
        username="budgetuser",
        email="b@test.com",
        password_hash="h",
        first_name="B",
        last_name="U",
    )
    cat = Category(name="Housing")
    session.add_all([user, cat])
    session.flush()
    sub = Category(name="Mortgage", parent_id=cat.id)
    session.add(sub)
    session.flush()
    return user, cat, sub


class TestBudgetCRUD:
    def test_create_and_get(self, session, user_and_category):
        user, cat, sub = user_and_category
        item = budget_service.create_budget_item(
            "Wells Fargo",
            Variability.FIXED,
            Frequency.MONTHLY,
            date(2026, 3, 1),
            Decimal("1500.00"),
            user.id,
            cat.id,
            subcategory_id=sub.id,
            notes="Mortgage payment",
        )
        assert item.id is not None
        assert item.budgeted_amount == Decimal("1500.00")
        assert budget_service.get_budget_item(item.id).id == item.id

    def test_get_nonexistent(self, session):
        assert budget_service.get_budget_item(9999) is None

    def test_list_active_only(self, session, user_and_category):
        user, cat, _ = user_and_category
        b1 = budget_service.create_budget_item(
            "A",
            Variability.FIXED,
            Frequency.MONTHLY,
            date(2026, 1, 1),
            Decimal("100"),
            user.id,
            cat.id,
        )
        b2 = budget_service.create_budget_item(
            "B",
            Variability.VARIABLE,
            Frequency.WEEKLY,
            date(2026, 2, 1),
            Decimal("50"),
            user.id,
            cat.id,
        )
        budget_service.deactivate_budget_item(b2.id)

        active = budget_service.get_budget_items_for_user(user.id)
        assert [b.id for b in active] == [b1.id]
        assert (
            len(budget_service.get_budget_items_for_user(user.id, active_only=False))
            == 2
        )

    @pytest.mark.parametrize(
        "field,value,expected",
        [
            ("payee", "New Payee", "New Payee"),
            ("variability", Variability.VARIABLE, "variable"),
            ("frequency", Frequency.ANNUAL, "annual"),
            ("budgeted_amount", Decimal("2000.00"), Decimal("2000.00")),
        ],
    )
    def test_update_fields(self, session, user_and_category, field, value, expected):
        user, cat, _ = user_and_category
        item = budget_service.create_budget_item(
            "X",
            Variability.FIXED,
            Frequency.MONTHLY,
            date(2026, 3, 1),
            Decimal("100"),
            user.id,
            cat.id,
        )
        updated = budget_service.update_budget_item(item.id, **{field: value})
        assert getattr(updated, field) == expected

    def test_update_nonexistent(self, session):
        assert budget_service.update_budget_item(9999, payee="X") is None

    def test_deactivate(self, session, user_and_category):
        user, cat, _ = user_and_category
        item = budget_service.create_budget_item(
            "D",
            Variability.FIXED,
            Frequency.MONTHLY,
            date(2026, 3, 1),
            Decimal("100"),
            user.id,
            cat.id,
        )
        assert budget_service.deactivate_budget_item(item.id).is_active is False
