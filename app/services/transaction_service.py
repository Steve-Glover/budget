import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models.transaction import Transaction
from app.models.enums import TransactionType


def create_transaction(
    transaction_date: date,
    payee: str,
    amount: Decimal,
    transaction_type: TransactionType,
    user_id: int,
    *,
    post_date: date | None = None,
    description: str | None = None,
    notes: str | None = None,
    debit_account_id: int | None = None,
    credit_account_id: int | None = None,
    category_id: int | None = None,
    subcategory_id: int | None = None,
) -> Transaction:
    txn = Transaction(
        transaction_date=transaction_date,
        payee=payee,
        amount=amount,
        transaction_type=transaction_type.value,
        user_id=user_id,
        post_date=post_date,
        description=description,
        notes=notes,
        debit_account_id=debit_account_id,
        credit_account_id=credit_account_id,
        category_id=category_id,
        subcategory_id=subcategory_id,
    )
    db.session.add(txn)
    db.session.commit()
    return txn


def get_transaction(transaction_id: int) -> Transaction | None:
    return db.session.get(Transaction, transaction_id)


def get_transactions_for_user(
    user_id: int,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    category_id: int | None = None,
    account_id: int | None = None,
    limit: int | None = None,
) -> list[Transaction]:
    query = Transaction.query.filter_by(user_id=user_id)

    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if account_id:
        query = query.filter(
            (Transaction.debit_account_id == account_id)
            | (Transaction.credit_account_id == account_id)
        )

    query = query.order_by(Transaction.transaction_date.desc())
    if limit:
        query = query.limit(limit)

    return query.all()


def update_transaction(transaction_id: int, **kwargs) -> Transaction | None:
    txn = db.session.get(Transaction, transaction_id)
    if not txn:
        return None

    if "transaction_type" in kwargs and isinstance(
        kwargs["transaction_type"], TransactionType
    ):
        kwargs["transaction_type"] = kwargs["transaction_type"].value

    for key, value in kwargs.items():
        if hasattr(txn, key):
            setattr(txn, key, value)

    db.session.commit()
    return txn


def delete_transaction(transaction_id: int) -> bool:
    txn = db.session.get(Transaction, transaction_id)
    if not txn:
        return False
    db.session.delete(txn)
    db.session.commit()
    return True


def import_csv(
    csv_data: str | io.StringIO,
    user_id: int,
    *,
    account_id: int | None = None,
) -> dict:
    """Import transactions from CSV data.

    Expected columns: date, payee, amount, type (debit/credit)
    Optional columns: post_date, description, notes

    Returns dict with 'imported' count and 'errors' list.
    """
    if isinstance(csv_data, str):
        csv_data = io.StringIO(csv_data)

    reader = csv.DictReader(csv_data)
    imported = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):  # row 1 is header
        try:
            amount = Decimal(row["amount"].strip().replace(",", ""))
        except (InvalidOperation, KeyError) as e:
            errors.append({"row": row_num, "error": f"Invalid amount: {e}"})
            continue

        try:
            txn_date = date.fromisoformat(row["date"].strip())
        except (ValueError, KeyError) as e:
            errors.append({"row": row_num, "error": f"Invalid date: {e}"})
            continue

        txn_type_str = row.get("type", "debit").strip().lower()
        try:
            txn_type = TransactionType(txn_type_str)
        except ValueError:
            errors.append({"row": row_num, "error": f"Invalid type: {txn_type_str}"})
            continue

        post_date = None
        if row.get("post_date"):
            try:
                post_date = date.fromisoformat(row["post_date"].strip())
            except ValueError:
                pass  # non-critical — skip post_date

        txn = Transaction(
            transaction_date=txn_date,
            post_date=post_date,
            payee=row.get("payee", "").strip(),
            description=row.get("description", "").strip() or None,
            amount=amount,
            transaction_type=txn_type.value,
            notes=row.get("notes", "").strip() or None,
            user_id=user_id,
            debit_account_id=account_id if txn_type == TransactionType.DEBIT else None,
            credit_account_id=account_id
            if txn_type == TransactionType.CREDIT
            else None,
        )
        db.session.add(txn)
        imported += 1

    if imported:
        db.session.commit()

    return {"imported": imported, "errors": errors}
