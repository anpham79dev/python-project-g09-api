import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def generate_permission_id() -> str:
    return f"perm-{uuid.uuid4().hex[:8]}"


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default=generate_permission_id,
        index=True
    )
    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False
    )  # e.g. "products:write"
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )
    module: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )  # e.g. "Sản Phẩm"
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
