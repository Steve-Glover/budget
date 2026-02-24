from decimal import Decimal

import pytest

from app.models.enums import AccountType
from app.models.user import User
from app.models.vendor import Vendor
from app.services import account_service


@pytest.fixture
def user_and_vendor(session):
    user = User(
        username="acctuser",
        email="a@test.com",
        password_hash="h",
        first_name="A",
        last_name="U",
    )
    vendor = Vendor(name="Chase", short_name="Chase")
    session.add_all([user, vendor])
    session.flush()
    return user, vendor


class TestAccountCRUD:
    def test_create_and_get(self, session, user_and_vendor):
        user, vendor = user_and_vendor
        acct = account_service.create_account(
            "Freedom",
            vendor.id,
            AccountType.CREDIT_CARD,
            user.id,
            account_number_last4="1234",
            balance=Decimal("500.00"),
        )
        assert acct.id is not None
        assert acct.name == "Freedom"
        assert acct.balance == Decimal("500.00")
        assert account_service.get_account(acct.id).id == acct.id

    def test_get_nonexistent(self, session):
        assert account_service.get_account(9999) is None

    def test_list_active_only(self, session, user_and_vendor):
        user, vendor = user_and_vendor
        a1 = account_service.create_account(
            "A", vendor.id, AccountType.CHECKING, user.id
        )
        a2 = account_service.create_account(
            "B", vendor.id, AccountType.SAVINGS, user.id
        )
        account_service.deactivate_account(a2.id)

        active = account_service.get_accounts_for_user(user.id)
        assert [a.id for a in active] == [a1.id]
        assert (
            len(account_service.get_accounts_for_user(user.id, active_only=False)) == 2
        )

    @pytest.mark.parametrize(
        "field,value,expected",
        [
            ("name", "New Name", "New Name"),
            ("account_type", AccountType.SAVINGS, "savings"),
            ("balance", Decimal("999.99"), Decimal("999.99")),
        ],
    )
    def test_update_fields(self, session, user_and_vendor, field, value, expected):
        user, vendor = user_and_vendor
        acct = account_service.create_account(
            "X", vendor.id, AccountType.CHECKING, user.id
        )
        updated = account_service.update_account(acct.id, **{field: value})
        assert getattr(updated, field) == expected

    def test_update_nonexistent(self, session):
        assert account_service.update_account(9999, name="X") is None

    def test_deactivate(self, session, user_and_vendor):
        user, vendor = user_and_vendor
        acct = account_service.create_account(
            "D", vendor.id, AccountType.OTHER, user.id
        )
        assert account_service.deactivate_account(acct.id).is_active is False
