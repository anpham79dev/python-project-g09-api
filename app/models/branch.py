import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"branch-{uuid.uuid4().hex[:6]}")
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    address: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(20))
    manager_name: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE, INACTIVE
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    warehouses = relationship("Warehouse", back_populates="branch", cascade="all, delete-orphan")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"wh-{uuid.uuid4().hex[:6]}")
    branch_id: Mapped[str] = mapped_column(String, ForeignKey("branches.id"), index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    warehouse_type: Mapped[str] = mapped_column(String(50), default="RETAIL")  # RETAIL, COLD_STORAGE, CENTRAL
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    branch = relationship("Branch", back_populates="warehouses")
    stock_items = relationship("StockItem", back_populates="warehouse", cascade="all, delete-orphan")
