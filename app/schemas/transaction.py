from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class TransactionBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    transaction_type: str = "INCOME"  # 'INCOME' | 'EXPENSE'
    category: str = "Thu khác / Hoàn tiền"
    amount: int = Field(gt=0)
    branch_id: Optional[str] = None
    payment_method: str = "CASH"  # 'CASH' | 'BANK_TRANSFER'
    recipient_payer: Optional[str] = "Khách hàng"
    note: Optional[str] = None

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, v: Any) -> int:
        if isinstance(v, str):
            cleaned = (
                v.replace("₫", "")
                .replace("đ", "")
                .replace("VNĐ", "")
                .replace("VND", "")
                .replace(",", "")
                .strip()
            )
            if "." in cleaned and len(cleaned.split(".")[-1]) == 3:
                cleaned = cleaned.replace(".", "")
            try:
                val = float(cleaned)
                return int(round(val))
            except (ValueError, TypeError):
                raise ValueError("Số tiền không hợp lệ")
        elif isinstance(v, (int, float)):
            return int(round(v))
        return v

    @field_validator("recipient_payer", mode="before")
    @classmethod
    def sanitize_recipient(cls, v: Any) -> str:
        if v is None:
            return "Khách hàng"
        s = str(v).strip()
        return s if s else "Khách hàng"


class TransactionCreate(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    id: str
    code: str
    branch_name: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime


class CashFlowSummary(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    period_label: str
    total_income: int
    total_expense: int
    net_cash_flow: int  # total_income - total_expense
    cash_balance: int
    bank_balance: int
    total_transactions_count: int
    income_by_category: Dict[str, int]
    expense_by_category: Dict[str, int]


class PnLReport(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    period_label: str
    gross_revenue: int          # Tổng doanh thu bán hàng & dịch vụ
    cogs: int                   # Giá vốn nguyên vật liệu & nhập hàng
    gross_profit: int           # gross_revenue - cogs
    gross_margin_percent: float # (gross_profit / gross_revenue) * 100
    operating_expenses: int     # Chi phí vận hành (Mặt bằng, điện nước, lương, tiếp thị)
    net_profit: int             # gross_profit - operating_expenses
    net_margin_percent: float   # (net_profit / gross_revenue) * 100
    expenses_breakdown: Dict[str, int]
