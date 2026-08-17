import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def generate_order_id() -> str:
    return f"ord-{uuid.uuid4().hex[:6]}"


def generate_order_item_id() -> str:
    return f"item-{uuid.uuid4().hex[:8]}"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default=generate_order_id,
        index=True
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )
    customer_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        default="Khách vãng lai"
    )
    customer_phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )
    branch_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True
    )
    warehouse_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True
    )
    staff_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    staff_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    subtotal: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    discount: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    total_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    payment_method: Mapped[str] = mapped_column(
        String(30),
        default="QR_TRANSFER",
        nullable=False
    )  # 'CASH' | 'QR_TRANSFER' | 'CARD'
    status: Mapped[str] = mapped_column(
        String(30),
        default="COMPLETED",
        nullable=False
    )  # 'COMPLETED' | 'PENDING' | 'CANCELLED'
    note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

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
    staff: Mapped["User"] = relationship(
        "User",
        back_populates="orders"
    )
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default=generate_order_item_id
    )
    order_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )
    product_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )
    price: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    subtotal: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    image: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items"
    )
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="order_items"
    )
