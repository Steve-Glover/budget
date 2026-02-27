from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import func

from app.extensions import db
from app.models.category import Category
from app.models.expense_analysis import AnalysisPeriod, ExpenseAnalysis
from app.models.transaction import Transaction
from app.models.budget import BudgetedExpense
from app.models.enums import TransactionType


def create_period(
    name: str, start_date: date, end_date: date, user_id: int
) -> AnalysisPeriod:
    period = AnalysisPeriod(
        name=name, start_date=start_date, end_date=end_date, user_id=user_id
    )
    db.session.add(period)
    db.session.commit()
    return period


def get_period(period_id: int) -> AnalysisPeriod | None:
    return db.session.get(AnalysisPeriod, period_id)


def get_periods_for_user(user_id: int) -> list[AnalysisPeriod]:
    return (
        AnalysisPeriod.query.filter_by(user_id=user_id)
        .order_by(AnalysisPeriod.start_date.desc())
        .all()
    )


def update_period(period_id: int, **kwargs) -> AnalysisPeriod | None:
    period = db.session.get(AnalysisPeriod, period_id)
    if not period:
        return None
    for key, value in kwargs.items():
        if hasattr(period, key):
            setattr(period, key, value)
    db.session.commit()
    return period


def delete_period(period_id: int) -> bool:
    period = db.session.get(AnalysisPeriod, period_id)
    if not period:
        return False
    # Delete associated analyses first
    ExpenseAnalysis.query.filter_by(period_id=period_id).delete()
    db.session.delete(period)
    db.session.commit()
    return True


def recompute_analysis(period_id: int, user_id: int) -> list[ExpenseAnalysis]:
    """Recompute budget-vs-actual for a period.

    1. Delete existing analysis rows for this period/user.
    2. Query transactions in the period's date range grouped by category/subcategory.
    3. Query budgeted amounts that fall in the period.
    4. Merge into ExpenseAnalysis rows with variance = budgeted - actual.
    """
    period = db.session.get(AnalysisPeriod, period_id)
    if not period:
        return []

    # Clear existing analysis rows
    ExpenseAnalysis.query.filter_by(period_id=period_id, user_id=user_id).delete()

    # Aggregate actual spending from transactions (debits only)
    actuals = (
        db.session.query(
            Transaction.category_id,
            Transaction.subcategory_id,
            func.sum(Transaction.amount).label("total_amount"),
            func.count(Transaction.id).label("txn_count"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= period.start_date,
            Transaction.transaction_date <= period.end_date,
            Transaction.transaction_type == TransactionType.DEBIT.value,
            Transaction.category_id.is_not(None),
        )
        .group_by(Transaction.category_id, Transaction.subcategory_id)
        .all()
    )

    # Aggregate budgeted amounts for expenses scheduled in the period
    budgeted = (
        db.session.query(
            BudgetedExpense.category_id,
            BudgetedExpense.subcategory_id,
            func.sum(BudgetedExpense.budgeted_amount).label("total_budgeted"),
        )
        .filter(
            BudgetedExpense.user_id == user_id,
            BudgetedExpense.is_active.is_(True),
            BudgetedExpense.date_scheduled >= period.start_date,
            BudgetedExpense.date_scheduled <= period.end_date,
        )
        .group_by(BudgetedExpense.category_id, BudgetedExpense.subcategory_id)
        .all()
    )

    # Build lookup: (category_id, subcategory_id) -> data
    analysis_map: dict[tuple, dict] = {}

    for row in actuals:
        key = (row.category_id, row.subcategory_id)
        analysis_map[key] = {
            "actual_amount": row.total_amount or Decimal("0.00"),
            "transaction_count": row.txn_count or 0,
            "budgeted_amount": Decimal("0.00"),
        }

    for row in budgeted:
        key = (row.category_id, row.subcategory_id)
        if key in analysis_map:
            analysis_map[key]["budgeted_amount"] = row.total_budgeted or Decimal("0.00")
        else:
            analysis_map[key] = {
                "actual_amount": Decimal("0.00"),
                "transaction_count": 0,
                "budgeted_amount": row.total_budgeted or Decimal("0.00"),
            }

    # Create ExpenseAnalysis rows
    results = []
    for (cat_id, subcat_id), data in analysis_map.items():
        variance = data["budgeted_amount"] - data["actual_amount"]
        ea = ExpenseAnalysis(
            period_id=period_id,
            user_id=user_id,
            category_id=cat_id,
            subcategory_id=subcat_id,
            budgeted_amount=data["budgeted_amount"],
            actual_amount=data["actual_amount"],
            variance=variance,
            transaction_count=data["transaction_count"],
        )
        db.session.add(ea)
        results.append(ea)

    db.session.commit()
    return results


def aggregate_by_category(
    period_id: int, user_id: int, category_id: int | None = None
) -> list[SimpleNamespace]:
    """Aggregate ExpenseAnalysis rows for a period into display objects.

    - category_id=None: sum across subcategories, group by top-level category.
    - category_id=X: return per-subcategory breakdown for that category.

    Each returned SimpleNamespace has: category_id, category_name,
    budgeted_amount, actual_amount, variance, transaction_count, pct.
    pct = int(actual/budgeted*100) when budgeted > 0, else None.
    """
    rows = ExpenseAnalysis.query.filter_by(period_id=period_id, user_id=user_id).all()

    if category_id is None:
        # Aggregate by top-level category
        agg: dict[int, dict] = {}
        for row in rows:
            cid = row.category_id
            if cid not in agg:
                agg[cid] = {
                    "budgeted": Decimal("0.00"),
                    "actual": Decimal("0.00"),
                    "count": 0,
                }
            agg[cid]["budgeted"] += row.budgeted_amount
            agg[cid]["actual"] += row.actual_amount
            agg[cid]["count"] += row.transaction_count

        result = []
        for cid, data in agg.items():
            cat = db.session.get(Category, cid)
            budgeted = data["budgeted"]
            actual = data["actual"]
            pct = int(actual / budgeted * 100) if budgeted > 0 else None
            result.append(
                SimpleNamespace(
                    category_id=cid,
                    category_name=cat.name if cat else "Unknown",
                    budgeted_amount=budgeted,
                    actual_amount=actual,
                    variance=budgeted - actual,
                    transaction_count=data["count"],
                    pct=pct,
                )
            )
    else:
        # Subcategory drill-down for a specific top-level category
        cat_rows = [r for r in rows if r.category_id == category_id]
        result = []
        for row in cat_rows:
            if row.subcategory_id:
                subcat = db.session.get(Category, row.subcategory_id)
                name = subcat.name if subcat else "Unknown"
            else:
                name = "Uncategorized"
            budgeted = row.budgeted_amount
            actual = row.actual_amount
            pct = int(actual / budgeted * 100) if budgeted > 0 else None
            result.append(
                SimpleNamespace(
                    category_id=row.category_id,
                    category_name=name,
                    budgeted_amount=budgeted,
                    actual_amount=actual,
                    variance=row.variance,
                    transaction_count=row.transaction_count,
                    pct=pct,
                )
            )

    result.sort(key=lambda x: x.actual_amount, reverse=True)
    return result
