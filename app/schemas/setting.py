from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ShiftTemplateBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    name: str
    start_time: str
    end_time: str
    default_initial_cash: int = 500000
    is_active: bool = True
    note: Optional[str] = None


class ShiftTemplateCreate(ShiftTemplateBase):
    pass


class ShiftTemplateUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    default_initial_cash: Optional[int] = None
    is_active: Optional[bool] = None
    note: Optional[str] = None


class ShiftTemplateResponse(ShiftTemplateBase):
    id: str
    created_at: datetime


class SystemSettingsResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    store_name: str
    store_slogan: str
    hotline: str
    address: str
    default_vat_rate: int
    low_stock_threshold: int
    allow_negative_stock: bool
    require_shift_reconciliation_note: bool
    bank_account_number: str
    bank_name: str
    bank_account_holder: str
    receipt_footer_note: str


class UpdateSystemSettingsRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    store_name: Optional[str] = None
    store_slogan: Optional[str] = None
    hotline: Optional[str] = None
    address: Optional[str] = None
    default_vat_rate: Optional[int] = None
    low_stock_threshold: Optional[int] = None
    allow_negative_stock: Optional[bool] = None
    require_shift_reconciliation_note: Optional[bool] = None
    bank_account_number: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_holder: Optional[str] = None
    receipt_footer_note: Optional[str] = None
