import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ShiftTemplate(Base):
    __tablename__ = "shift_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"tmpl-{uuid.uuid4().hex[:6]}")
    name: Mapped[str] = mapped_column(String(100), index=True)
    start_time: Mapped[str] = mapped_column(String(10))  # e.g. "06:30"
    end_time: Mapped[str] = mapped_column(String(10))    # e.g. "14:30"
    default_initial_cash: Mapped[int] = mapped_column(Integer, default=500000)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
