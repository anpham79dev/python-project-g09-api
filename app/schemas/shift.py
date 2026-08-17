from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class WorkShiftBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    shift_name: str
    initial_cash: int = 500000


class CloseShiftRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    actual_cash: int
    note: Optional[str] = None


class WorkShiftResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    id: str
    shift_name: str
    staff_id: str
    staff_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    initial_cash: int
    cash_revenue: int
    card_revenue: int
    qr_revenue: int
    total_revenue: int
    orders_count: int
    expected_cash: int
    actual_cash: int
    difference: int
    status: str
    note: Optional[str] = None
    created_at: datetime


class ShiftSummaryResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    total_shifts_count: int
    closed_shifts_count: int
    open_shifts_count: int
    total_revenue: int
    total_cash: int
    total_card: int
    total_qr: int
    total_difference: int
    shifts: List[WorkShiftResponse]
