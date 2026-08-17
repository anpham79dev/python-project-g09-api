from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class WarehouseBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    name: str
    warehouse_type: str = "RETAIL"
    status: str = "ACTIVE"


class WarehouseCreate(WarehouseBase):
    code: str
    branch_id: str


class WarehouseResponse(WarehouseBase):
    id: str
    branch_id: str
    code: str
    created_at: datetime


class BranchBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    code: str
    name: str
    address: str
    phone: str
    manager_name: Optional[str] = None
    status: str = "ACTIVE"


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    manager_name: Optional[str] = None
    status: Optional[str] = None


class BranchResponse(BranchBase):
    id: str
    created_at: datetime
    warehouses: List[WarehouseResponse] = []


class StockItemResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    id: str
    warehouse_id: str
    warehouse_name: Optional[str] = None
    branch_id: Optional[str] = None
    branch_name: Optional[str] = None
    product_id: str
    product_name: Optional[str] = None
    product_image: Optional[str] = None
    product_category: Optional[str] = None
    quantity: int
    min_alert_stock: int
    status: str  # in_stock, low_stock, out_of_stock
    updated_at: datetime


class UpdateStockRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    warehouse_id: str
    product_id: str
    quantity: int
    min_alert_stock: Optional[int] = 5
