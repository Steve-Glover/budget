from datetime import date
from decimal import Decimal

from sqlalchemy import String, Boolean, Text, Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import TimestampMixin
from app.models.enums import Variability, Frequency


class BudgetedExpense(TimestampMixin, db.Model):
    __tablename__ = "budgeted_expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    payee: Mapped[str] = mapped_column(String(200), index=True)
    variability: Mapped[str] = mapped_column(String(20))
    frequency: Mapped[str] = mapped_column(String(20))
    date_scheduled: Mapped[date] = mapped_column(Date, index=True)
    budgeted_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    subcategory_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), index=True
    )

    # Relationships
    user = relationship("User", back_populates="budgeted_expenses")
    category = relationship("Category", foreign_keys=[category_id])
    subcategory = relationship("Category", foreign_keys=[subcategory_id])

    @property
    def variability_enum(self) -> Variability:
        return Variability(self.variability)

    @property
    def frequency_enum(self) -> Frequency:
        return Frequency(self.frequency)

    def __repr__(self):
        return f"<BudgetedExpense {self.payee} {self.budgeted_amount}>"
