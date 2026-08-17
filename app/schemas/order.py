from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class OrderItemBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    product_id: str
    product_name: str
    price: int = Field(ge=0)
    quantity: int = Field(ge=1)
    subtotal: int = Field(ge=0)
    image: Optional[str] = None


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: str


class OrderCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    customer_name: Optional[str] = "Khách vãng lai"
    customer_phone: Optional[str] = None
    branch_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    staff_id: Optional[str] = None
    staff_name: Optional[str] = None
    items: List[OrderItemCreate]
    subtotal: int = Field(ge=0)
    discount: int = Field(default=0, ge=0)
    total_amount: int = Field(ge=0)
    payment_method: str = "QR_TRANSFER"  # "CASH" | "QR_TRANSFER" | "CARD"
    status: str = "COMPLETED"  # "COMPLETED" | "PENDING" | "CANCELLED"
    note: Optional[str] = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    id: str
    code: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    branch_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    staff_id: str
    staff_name: str
    items: List[OrderItemResponse]
    subtotal: int
    discount: int
    total_amount: int
    payment_method: str
    status: str
    note: Optional[str] = None
    created_at: datetime
