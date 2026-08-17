import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class StockItem(Base):
    __tablename__ = "stock_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"stk-{uuid.uuid4().hex[:8]}")
    warehouse_id: Mapped[str] = mapped_column(String, ForeignKey("warehouses.id"), index=True)
    product_id: Mapped[str] = mapped_column(String, ForeignKey("products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    min_alert_stock: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('warehouse_id', 'product_id', name='uq_warehouse_product_stock'),
    )

    # Relationships
    warehouse = relationship("Warehouse", back_populates="stock_items")
    product = relationship("Product")
