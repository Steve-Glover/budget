from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import TimestampMixin


class Vendor(TimestampMixin, db.Model):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    short_name: Mapped[str] = mapped_column(String(20), unique=True)

    # Relationships
    accounts = relationship("Account", back_populates="vendor", lazy="dynamic")

    def __repr__(self):
        return f"<Vendor {self.short_name}>"
