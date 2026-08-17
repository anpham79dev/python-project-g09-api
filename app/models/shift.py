import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class WorkShift(Base):
    __tablename__ = "work_shifts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"shift-{uuid.uuid4().hex[:8]}")
    branch_id: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    template_id: Mapped[str] = mapped_column(String(50), nullable=True)
    shift_name: Mapped[str] = mapped_column(String(100), default="Ca làm việc tiêu chuẩn")
    staff_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    staff_name: Mapped[str] = mapped_column(String(100))
    start_time: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    initial_cash: Mapped[int] = mapped_column(Integer, default=500000)
    cash_revenue: Mapped[int] = mapped_column(Integer, default=0)
    card_revenue: Mapped[int] = mapped_column(Integer, default=0)
    qr_revenue: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue: Mapped[int] = mapped_column(Integer, default=0)
    orders_count: Mapped[int] = mapped_column(Integer, default=0)
    
    expected_cash: Mapped[int] = mapped_column(Integer, default=500000)
    actual_cash: Mapped[int] = mapped_column(Integer, default=0)
    difference: Mapped[int] = mapped_column(Integer, default=0)
    
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)  # OPEN, CLOSED
    note: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    staff = relationship("User", backref="work_shifts")
