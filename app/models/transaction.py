from datetime import date
from decimal import Decimal

from sqlalchemy import String, Text, Date, ForeignKey, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import TimestampMixin
from app.models.enums import TransactionType


class Transaction(TimestampMixin, db.Model):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_id_transaction_date", "user_id", "transaction_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    post_date: Mapped[date | None] = mapped_column(Date)
    payee: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    transaction_type: Mapped[str] = mapped_column(String(10))
    notes: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    debit_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), index=True
    )
    credit_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), index=True
    )
    subcategory_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), index=True
    )

    # Relationships
    user = relationship("User", back_populates="transactions")
    debit_account = relationship("Account", foreign_keys=[debit_account_id])
    credit_account = relationship("Account", foreign_keys=[credit_account_id])
    category = relationship("Category", foreign_keys=[category_id])
    subcategory = relationship("Category", foreign_keys=[subcategory_id])

    @property
    def transaction_type_enum(self) -> TransactionType:
        return TransactionType(self.transaction_type)

    def __repr__(self):
        return f"<Transaction {self.payee} {self.amount}>"
