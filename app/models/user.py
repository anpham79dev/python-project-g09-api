import uuid
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.core.rbac_config import ALL_PERMISSION_CODES, SYSTEM_ROLES_CONFIG


def generate_user_id() -> str:
    return f"user-{uuid.uuid4().hex[:8]}"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default=generate_user_id,
        index=True
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )
    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    # Role ID referencing roles table (PBAC)
    role_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    # Legacy role string kept as fallback for backward compatibility
    role: Mapped[str] = mapped_column(
        String(50),
        default="STAFF",
        nullable=False,
        index=True
    )  # 'SUPER_ADMIN' | 'ADMIN' | 'STAFF' | or custom role code
    status: Mapped[str] = mapped_column(
        String(20),
        default="ACTIVE",
        nullable=False,
        index=True
    )  # 'ACTIVE' | 'INACTIVE'
    default_branch_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True
    )
    last_active_branch_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    
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

    # Relationships
    role_rel: Mapped[Optional["Role"]] = relationship(
        "Role",
        back_populates="users",
        lazy="selectin"
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="staff",
        lazy="selectin"
    )

    @property
    def role_code(self) -> str:
        if self.role_rel and self.role_rel.code:
            return self.role_rel.code
        return self.role or "STAFF"

    @property
    def role_name(self) -> str:
        if self.role_rel and self.role_rel.name:
            return self.role_rel.name
        cfg = SYSTEM_ROLES_CONFIG.get(self.role_code)
        if cfg:
            return cfg["name"]
        return self.role_code

    @property
    def permissions_version(self) -> int:
        if self.role_rel:
            return self.role_rel.permissions_version
        return 1

    def get_permissions(self) -> List[str]:
        """Return list of atomic permission codes for this user."""
        if self.role_code == "SUPER_ADMIN":
            return ALL_PERMISSION_CODES
        
        if self.role_rel and self.role_rel.permissions:
            return [p.code for p in self.role_rel.permissions]
        
        # Fallback to system config
        cfg = SYSTEM_ROLES_CONFIG.get(self.role_code)
        if cfg:
            return cfg["permissions"]
        
        return []
