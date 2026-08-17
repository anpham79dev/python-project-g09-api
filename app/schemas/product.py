from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic.alias_generators import to_camel


class ProductBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    name: str
    category: str
    price: int = Field(ge=0)
    stock: int = Field(ge=0)
    description: Optional[str] = None
    image: str


class ProductCreate(ProductBase):
    warehouse_id: Optional[str] = None


class ProductUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[int] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)
    description: Optional[str] = None
    image: Optional[str] = None


class ProductResponse(ProductBase):
    id: str
    created_at: datetime

    @computed_field
    def status(self) -> str:
        """Dynamic calculation of stock status without storing duplicate column."""
        if self.stock == 0:
            return "out_of_stock"
        elif self.stock <= 5:
            return "low_stock"
        return "in_stock"
