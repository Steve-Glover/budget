from datetime import date
from decimal import Decimal

import pytest

from app.models.enums import TransactionType
from app.models.user import User
from app.models.vendor import Vendor
from app.models.account import Account
from app.models.enums import AccountType
from app.services import transaction_service


@pytest.fixture
def user(session):
    u = User(
        username="txnuser",
        email="t@test.com",
        password_hash="h",
        first_name="T",
        last_name="U",
    )
    session.add(u)
    session.flush()
    return u


@pytest.fixture
def account(session, user):
    v = Vendor(name="Chase", short_name="Chase")
    session.add(v)
    session.flush()
    a = Account(
        name="Checking",
        vendor_id=v.id,
        owner_id=user.id,
        account_type=AccountType.CHECKING.value,
    )
    session.add(a)
    session.flush()
    return a


class TestTransactionCRUD:
    def test_create_and_get(self, session, user):
        txn = transaction_service.create_transaction(
            date(2026, 2, 15),
            "Grocery Store",
            Decimal("52.30"),
            TransactionType.DEBIT,
            user.id,
            description="Weekly groceries",
        )
        assert txn.id is not None
        assert txn.amount == Decimal("52.30")
        assert transaction_service.get_transaction(txn.id).id == txn.id

    def test_get_nonexistent(self, session):
        assert transaction_service.get_transaction(9999) is None

    def test_list_with_date_filter(self, session, user):
        for day in (1, 10, 20):
            transaction_service.create_transaction(
                date(2026, 2, day),
                f"P{day}",
                Decimal("10"),
                TransactionType.DEBIT,
                user.id,
            )
        filtered = transaction_service.get_transactions_for_user(
            user.id,
            start_date=date(2026, 2, 5),
            end_date=date(2026, 2, 15),
        )
        assert len(filtered) == 1
        assert filtered[0].payee == "P10"

    def test_list_with_account_filter(self, session, user, account):
        transaction_service.create_transaction(
            date(2026, 2, 1),
            "A",
            Decimal("10"),
            TransactionType.DEBIT,
            user.id,
            debit_account_id=account.id,
        )
        transaction_service.create_transaction(
            date(2026, 2, 2),
            "B",
            Decimal("20"),
            TransactionType.DEBIT,
            user.id,
        )
        result = transaction_service.get_transactions_for_user(
            user.id, account_id=account.id
        )
        assert len(result) == 1
        assert result[0].payee == "A"

    def test_list_with_limit(self, session, user):
        for i in range(5):
            transaction_service.create_transaction(
                date(2026, 2, i + 1),
                f"P{i}",
                Decimal("10"),
                TransactionType.DEBIT,
                user.id,
            )
        assert len(transaction_service.get_transactions_for_user(user.id, limit=3)) == 3

    @pytest.mark.parametrize(
        "field,value,expected",
        [
            ("payee", "Updated Payee", "Updated Payee"),
            ("amount", Decimal("99.99"), Decimal("99.99")),
            ("transaction_type", TransactionType.CREDIT, "credit"),
        ],
    )
    def test_update_fields(self, session, user, field, value, expected):
        txn = transaction_service.create_transaction(
            date(2026, 2, 1),
            "X",
            Decimal("10"),
            TransactionType.DEBIT,
            user.id,
        )
        updated = transaction_service.update_transaction(txn.id, **{field: value})
        assert getattr(updated, field) == expected

    def test_update_nonexistent(self, session):
        assert transaction_service.update_transaction(9999, payee="X") is None

    def test_delete(self, session, user):
        txn = transaction_service.create_transaction(
            date(2026, 2, 1),
            "Del",
            Decimal("10"),
            TransactionType.DEBIT,
            user.id,
        )
        assert transaction_service.delete_transaction(txn.id) is True
        assert transaction_service.get_transaction(txn.id) is None

    def test_delete_nonexistent(self, session):
        assert transaction_service.delete_transaction(9999) is False


class TestCSVImport:
    VALID_CSV = (
        "date,payee,amount,type,description\n"
        "2026-02-01,Grocery Store,52.30,debit,Weekly groceries\n"
        "2026-02-05,Paycheck,3000.00,credit,Salary\n"
    )

    def test_import_valid(self, session, user):
        result = transaction_service.import_csv(self.VALID_CSV, user.id)
        assert result["imported"] == 2
        assert result["errors"] == []
        txns = transaction_service.get_transactions_for_user(user.id)
        assert len(txns) == 2

    def test_import_with_account(self, session, user, account):
        csv = "date,payee,amount,type\n2026-02-01,Store,10.00,debit\n"
        transaction_service.import_csv(csv, user.id, account_id=account.id)
        txn = transaction_service.get_transactions_for_user(user.id)[0]
        assert txn.debit_account_id == account.id

    @pytest.mark.parametrize(
        "bad_csv,error_fragment",
        [
            (
                "date,payee,amount,type\n2026-02-01,Bad,notanumber,debit\n",
                "Invalid amount",
            ),
            ("date,payee,amount,type\nnot-a-date,Bad,10.00,debit\n", "Invalid date"),
            ("date,payee,amount,type\n2026-02-01,Bad,10.00,invalid\n", "Invalid type"),
        ],
        ids=["bad_amount", "bad_date", "bad_type"],
    )
    def test_import_row_errors(self, session, user, bad_csv, error_fragment):
        result = transaction_service.import_csv(bad_csv, user.id)
        assert result["imported"] == 0
        assert len(result["errors"]) == 1
        assert error_fragment in result["errors"][0]["error"]

    def test_import_mixed_valid_and_invalid(self, session, user):
        csv = (
            "date,payee,amount,type\n"
            "2026-02-01,Good,10.00,debit\n"
            "bad-date,Bad,20.00,debit\n"
            "2026-02-03,AlsoGood,30.00,credit\n"
        )
        result = transaction_service.import_csv(csv, user.id)
        assert result["imported"] == 2
        assert len(result["errors"]) == 1
