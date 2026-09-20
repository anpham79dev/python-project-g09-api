from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class HourlySaleItem(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    time: str
    revenue: int
    orders: int


class TopSellingProductItem(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    id: str
    name: str
    category: str
    sold_count: int
    revenue: int
    image: str


class SlowSellingProductItem(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    id: str
    name: str
    category: str
    sold_count: int
    revenue: int
    stock: int
    image: str


class PaymentMethodStat(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    method: str
    method_label: str
    count: int
    revenue: int
    percentage: float


class CategoryStat(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    category: str
    revenue: int
    sold_count: int
    percentage: float


class StaffPerformanceStat(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    staff_id: str
    staff_name: str
    orders_count: int
    revenue: int
    average_order_value: int


class LowStockDetailItem(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    id: str
    name: str
    category: str
    stock: int
    threshold: int
    status: str
    image: str


class DashboardStatsResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    period_label: str
    previous_period_label: str
    today_revenue: int
    yesterday_revenue: int
    revenue_growth: float
    today_orders_count: int
    yesterday_orders_count: int
    orders_growth: float
    average_order_value: int
    total_products_count: int
    low_stock_count: int
    recent_sales_chart: List[HourlySaleItem]
    top_selling_products: List[TopSellingProductItem]
    slow_selling_products: List[SlowSellingProductItem]
    payment_methods: List[PaymentMethodStat]
    category_sales: List[CategoryStat]
    staff_performances: List[StaffPerformanceStat]
    low_stock_details: List[LowStockDetailItem]
    low_stock_threshold: int = 5
