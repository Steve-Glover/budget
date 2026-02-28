from decimal import Decimal

from app.extensions import db
from app.models.account import Account
from app.models.enums import AccountType


def create_account(
    name: str,
    vendor_id: int,
    account_type: AccountType,
    owner_id: int,
    *,
    account_number_last4: str | None = None,
    balance: Decimal = Decimal("0.00"),
) -> Account:
    account = Account(
        name=name,
        vendor_id=vendor_id,
        account_type=account_type.value,
        owner_id=owner_id,
        account_number_last4=account_number_last4,
        balance=balance,
    )
    db.session.add(account)
    db.session.commit()
    return account


def get_account(account_id: int) -> Account | None:
    return db.session.get(Account, account_id)


def get_account_for_user(account_id: int, user_id: int) -> Account | None:
    return Account.query.filter_by(id=account_id, owner_id=user_id).first()


def get_accounts_for_user(user_id: int, *, active_only: bool = True) -> list[Account]:
    query = Account.query.filter_by(owner_id=user_id)
    if active_only:
        query = query.filter_by(is_active=True)
    return query.order_by(Account.name).all()


def update_account(account_id: int, **kwargs) -> Account | None:
    account = db.session.get(Account, account_id)
    if not account:
        return None

    # Convert enum to value string if provided
    if "account_type" in kwargs and isinstance(kwargs["account_type"], AccountType):
        kwargs["account_type"] = kwargs["account_type"].value

    for key, value in kwargs.items():
        if hasattr(account, key):
            setattr(account, key, value)

    db.session.commit()
    return account


def deactivate_account(account_id: int) -> Account | None:
    return update_account(account_id, is_active=False)
