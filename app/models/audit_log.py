import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def generate_audit_id() -> str:
    return f"audit-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:6]}"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default=generate_audit_id,
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    user_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )  # "ROLE_CREATE" | "ROLE_UPDATE_PERMISSIONS" | "ROLE_DELETE" | "USER_ROLE_CHANGE"
    target_type: Mapped[str] = mapped_column(
        String(50),
        default="ROLE",
        nullable=False
    )  # "ROLE" | "USER"
    target_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    target_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    changes_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    details_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )  # JSON string with {before, after, diff_added, diff_removed}
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
