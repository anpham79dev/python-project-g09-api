import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def generate_transaction_id() -> str:
    return f"tx-{uuid.uuid4().hex[:8]}"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default=generate_transaction_id,
        index=True
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )
    transaction_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # 'INCOME' | 'EXPENSE'
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )  # 'SALES', 'RAW_MATERIALS', 'RENTAL', 'UTILITIES', 'SALARY', 'MARKETING', 'OTHER'
    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    branch_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True
    )
    payment_method: Mapped[str] = mapped_column(
        String(30),
        default="CASH",
        nullable=False
    )  # 'CASH' | 'BANK_TRANSFER'
    recipient_payer: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )  # Người nộp tiền hoặc người nhận tiền
    note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
