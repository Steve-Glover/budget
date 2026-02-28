"""Route-level tests verifying that transaction mutations trigger analysis recomputation."""

import io
from datetime import date
from decimal import Decimal

import pytest

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.expense_analysis import ExpenseAnalysis
from app.models.transaction import Transaction
from app.services import analysis_service


@pytest.fixture
def category(session):
    food = Category(name="Food")
    session.add(food)
    session.commit()
    return food


@pytest.fixture
def period(session, user):
    return analysis_service.create_period(
        "Feb 2026", date(2026, 2, 1), date(2026, 2, 28), user.id
    )


def _post_txn(client, data):
    defaults = {
        "payee": "Store",
        "amount": "100.00",
        "transaction_type": "debit",
        "subcategory_id": "",
        "post_date": "",
        "description": "",
        "notes": "",
        "debit_account_id": "",
        "credit_account_id": "",
    }
    defaults.update(data)
    return client.post("/transactions/create", data=defaults, follow_redirects=True)


class TestCreateTriggersRecompute:
    def test_transaction_in_period_creates_analysis(
        self, logged_in_client, session, user, period, category
    ):
        _post_txn(
            logged_in_client,
            {
                "transaction_date": "2026-02-10",
                "category_id": str(category.id),
            },
        )
        eas = ExpenseAnalysis.query.filter_by(period_id=period.id).all()
        assert len(eas) == 1
        assert eas[0].actual_amount == Decimal("100.00")

    def test_transaction_outside_period_no_analysis(
        self, logged_in_client, session, user, period, category
    ):
        _post_txn(
            logged_in_client,
            {
                "transaction_date": "2026-03-01",
                "category_id": str(category.id),
            },
        )
        eas = ExpenseAnalysis.query.filter_by(period_id=period.id).all()
        assert len(eas) == 0

    def test_no_category_no_analysis(self, logged_in_client, session, user, period):
        _post_txn(
            logged_in_client,
            {
                "transaction_date": "2026-02-10",
                "category_id": "",
            },
        )
        eas = ExpenseAnalysis.query.filter_by(period_id=period.id).all()
        assert len(eas) == 0


class TestEditTriggersRecompute:
    def test_moving_date_recomputes_both_periods(
        self, logged_in_client, session, user, category
    ):
        jan = analysis_service.create_period(
            "Jan 2026", date(2026, 1, 1), date(2026, 1, 31), user.id
        )
        feb = analysis_service.create_period(
            "Feb 2026", date(2026, 2, 1), date(2026, 2, 28), user.id
        )
        _post_txn(
            logged_in_client,
            {
                "transaction_date": "2026-01-15",
                "category_id": str(category.id),
            },
        )
        assert len(ExpenseAnalysis.query.filter_by(period_id=jan.id).all()) == 1
        assert len(ExpenseAnalysis.query.filter_by(period_id=feb.id).all()) == 0

        txn = Transaction.query.filter_by(payee="Store").first()
        logged_in_client.post(
            f"/transactions/{txn.id}/edit",
            data={
                "transaction_date": "2026-02-10",
                "payee": "Store",
                "amount": "100.00",
                "transaction_type": "debit",
                "category_id": str(category.id),
                "subcategory_id": "",
                "post_date": "",
                "description": "",
                "notes": "",
                "debit_account_id": "",
                "credit_account_id": "",
            },
            follow_redirects=True,
        )
        # Jan period recomputed — no transactions left in Jan
        assert len(ExpenseAnalysis.query.filter_by(period_id=jan.id).all()) == 0
        # Feb period recomputed — transaction moved here
        feb_eas = ExpenseAnalysis.query.filter_by(period_id=feb.id).all()
        assert len(feb_eas) == 1
        assert feb_eas[0].actual_amount == Decimal("100.00")

    def test_same_date_edit_recomputes_period(
        self, logged_in_client, session, user, period, category
    ):
        _post_txn(
            logged_in_client,
            {
                "transaction_date": "2026-02-10",
                "category_id": str(category.id),
            },
        )
        txn = Transaction.query.filter_by(payee="Store").first()
        logged_in_client.post(
            f"/transactions/{txn.id}/edit",
            data={
                "transaction_date": "2026-02-10",
                "payee": "Store",
                "amount": "200.00",
                "transaction_type": "debit",
                "category_id": str(category.id),
                "subcategory_id": "",
                "post_date": "",
                "description": "",
                "notes": "",
                "debit_account_id": "",
                "credit_account_id": "",
            },
            follow_redirects=True,
        )
        eas = ExpenseAnalysis.query.filter_by(period_id=period.id).all()
        assert len(eas) == 1
        assert eas[0].actual_amount == Decimal("200.00")


class TestDeleteTriggersRecompute:
    def test_delete_clears_analysis(
        self, logged_in_client, session, user, period, category
    ):
        _post_txn(
            logged_in_client,
            {
                "transaction_date": "2026-02-10",
                "category_id": str(category.id),
            },
        )
        assert len(ExpenseAnalysis.query.filter_by(period_id=period.id).all()) == 1

        txn = Transaction.query.filter_by(payee="Store").first()
        logged_in_client.post(f"/transactions/{txn.id}/delete", follow_redirects=True)

        assert len(ExpenseAnalysis.query.filter_by(period_id=period.id).all()) == 0

    def test_delete_nonexistent_no_crash(self, logged_in_client, session, user, period):
        resp = logged_in_client.post("/transactions/9999/delete", follow_redirects=True)
        assert resp.status_code == 200


def _import_csv(client, csv_data):
    data = {"csv_file": (io.BytesIO(csv_data.encode()), "test.csv"), "account_id": ""}
    return client.post(
        "/transactions/import",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )


class TestImportTriggersRecompute:
    def test_import_clears_stale_analysis(
        self, logged_in_client, session, user, period, category
    ):
        from app.services import transaction_service as ts

        txn = ts.create_transaction(
            date(2026, 2, 10),
            "Store",
            Decimal("100.00"),
            TransactionType.DEBIT,
            user.id,
            category_id=category.id,
        )
        analysis_service.recompute_analysis(period.id, user.id)
        assert len(ExpenseAnalysis.query.filter_by(period_id=period.id).all()) == 1

        ts.delete_transaction(txn.id)
        assert len(ExpenseAnalysis.query.filter_by(period_id=period.id).all()) == 1

        resp = _import_csv(
            logged_in_client,
            "date,payee,amount,type\n2026-02-15,Grocery,50.00,debit\n",
        )
        assert resp.status_code == 200
        assert len(ExpenseAnalysis.query.filter_by(period_id=period.id).all()) == 0

    def test_import_outside_period_leaves_analysis_untouched(
        self, logged_in_client, session, user, period, category
    ):
        from app.services import transaction_service as ts

        ts.create_transaction(
            date(2026, 2, 10),
            "Store",
            Decimal("100.00"),
            TransactionType.DEBIT,
            user.id,
            category_id=category.id,
        )
        analysis_service.recompute_analysis(period.id, user.id)
        ea_before = ExpenseAnalysis.query.filter_by(period_id=period.id).first()
        assert ea_before is not None

        _import_csv(
            logged_in_client,
            "date,payee,amount,type\n2026-06-01,Other,50.00,debit\n",
        )

        ea_after = ExpenseAnalysis.query.filter_by(period_id=period.id).first()
        assert ea_after is not None
        assert ea_after.actual_amount == Decimal("100.00")
