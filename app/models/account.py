from decimal import Decimal

from sqlalchemy import String, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import TimestampMixin
from app.models.enums import AccountType


class Account(TimestampMixin, db.Model):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), index=True)
    account_type: Mapped[str] = mapped_column(String(50))
    account_number_last4: Mapped[str | None] = mapped_column(String(4))
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Relationships
    vendor = relationship("Vendor", back_populates="accounts")
    owner = relationship("User", back_populates="accounts")

    @property
    def account_type_enum(self) -> AccountType:
        return AccountType(self.account_type)

    def __repr__(self):
        return f"<Account {self.name}>"
