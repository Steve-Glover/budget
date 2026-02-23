from datetime import date
from decimal import Decimal

from sqlalchemy import String, Date, ForeignKey, Numeric, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import TimestampMixin


class AnalysisPeriod(TimestampMixin, db.Model):
    __tablename__ = "analysis_periods"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_analysis_periods_user_id_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Relationships
    user = relationship("User", back_populates="analysis_periods")
    analyses = relationship("ExpenseAnalysis", back_populates="period", lazy="dynamic")

    def __repr__(self):
        return f"<AnalysisPeriod {self.name}>"


class ExpenseAnalysis(TimestampMixin, db.Model):
    __tablename__ = "expense_analysis"
    __table_args__ = (
        UniqueConstraint(
            "period_id",
            "user_id",
            "category_id",
            "subcategory_id",
            name="uq_expense_analysis_period_user_category_subcategory",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    budgeted_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    actual_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    variance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    period_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_periods.id"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    subcategory_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), index=True
    )

    # Relationships
    period = relationship("AnalysisPeriod", back_populates="analyses")
    user = relationship("User")
    category = relationship("Category", foreign_keys=[category_id])
    subcategory = relationship("Category", foreign_keys=[subcategory_id])

    def __repr__(self):
        return f"<ExpenseAnalysis period={self.period_id} cat={self.category_id}>"
