import uuid
from datetime import datetime, timezone
from typing import List
from sqlalchemy import String, DateTime, Text, Boolean, Integer, Table, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.permission import Permission


def generate_role_id() -> str:
    return f"role-{uuid.uuid4().hex[:8]}"


# Association table for Many-to-Many relationship between Roles and Permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String(50), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(50), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default=generate_role_id,
        index=True
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )  # e.g. "SUPER_ADMIN", "ADMIN", "STAFF", "BRANCH_MANAGER"
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )  # True for SUPER_ADMIN, ADMIN, STAFF
    permissions_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )  # Increments on permission update to invalidate stale JWT/client state

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Many-to-Many relationship to Permissions
    permissions: Mapped[List[Permission]] = relationship(
        "Permission",
        secondary=role_permissions,
        lazy="selectin"
    )

    # One-to-Many relationship to Users
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="role_rel",
        lazy="selectin"
    )
