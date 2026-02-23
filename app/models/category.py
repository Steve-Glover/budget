from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import TimestampMixin


class Category(TimestampMixin, db.Model):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_categories_parent_id_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255))
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), index=True
    )

    # Self-referencing relationship
    parent = relationship("Category", remote_side="Category.id", back_populates="children")
    children = relationship("Category", back_populates="parent", lazy="dynamic")

    @property
    def is_top_level(self) -> bool:
        return self.parent_id is None

    def __repr__(self):
        return f"<Category {self.name}>"
