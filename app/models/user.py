from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import TimestampMixin


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    accounts = relationship("Account", back_populates="owner", lazy="dynamic")
    budgeted_expenses = relationship(
        "BudgetedExpense", back_populates="user", lazy="dynamic"
    )
    transactions = relationship("Transaction", back_populates="user", lazy="dynamic")
    analysis_periods = relationship(
        "AnalysisPeriod", back_populates="user", lazy="dynamic"
    )

    def __repr__(self):
        return f"<User {self.username}>"
