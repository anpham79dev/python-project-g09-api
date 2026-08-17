import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Integer, Text, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def generate_product_id() -> str:
    return f"prod-{uuid.uuid4().hex[:6]}"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default=generate_product_id,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    price: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    image: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )  # Soft delete flag

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="product",
        lazy="selectin"
    )

    @property
    def dynamic_status(self) -> str:
        """Dynamically compute product status based on stock level."""
        if self.stock == 0:
            return "out_of_stock"
        elif self.stock <= 5:
            return "low_stock"
        return "in_stock"
