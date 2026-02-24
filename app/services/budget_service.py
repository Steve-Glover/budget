from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models.budget import BudgetedExpense
from app.models.enums import Variability, Frequency


def create_budget_item(
    payee: str,
    variability: Variability,
    frequency: Frequency,
    date_scheduled: date,
    budgeted_amount: Decimal,
    user_id: int,
    category_id: int,
    *,
    subcategory_id: int | None = None,
    notes: str | None = None,
) -> BudgetedExpense:
    item = BudgetedExpense(
        payee=payee,
        variability=variability.value,
        frequency=frequency.value,
        date_scheduled=date_scheduled,
        budgeted_amount=budgeted_amount,
        user_id=user_id,
        category_id=category_id,
        subcategory_id=subcategory_id,
        notes=notes,
    )
    db.session.add(item)
    db.session.commit()
    return item


def get_budget_item(budget_id: int) -> BudgetedExpense | None:
    return db.session.get(BudgetedExpense, budget_id)


def get_budget_items_for_user(
    user_id: int, *, active_only: bool = True
) -> list[BudgetedExpense]:
    query = BudgetedExpense.query.filter_by(user_id=user_id)
    if active_only:
        query = query.filter_by(is_active=True)
    return query.order_by(BudgetedExpense.date_scheduled).all()


def update_budget_item(budget_id: int, **kwargs) -> BudgetedExpense | None:
    item = db.session.get(BudgetedExpense, budget_id)
    if not item:
        return None

    # Convert enums to value strings if provided
    if "variability" in kwargs and isinstance(kwargs["variability"], Variability):
        kwargs["variability"] = kwargs["variability"].value
    if "frequency" in kwargs and isinstance(kwargs["frequency"], Frequency):
        kwargs["frequency"] = kwargs["frequency"].value

    for key, value in kwargs.items():
        if hasattr(item, key):
            setattr(item, key, value)

    db.session.commit()
    return item


def deactivate_budget_item(budget_id: int) -> BudgetedExpense | None:
    return update_budget_item(budget_id, is_active=False)
