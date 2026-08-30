from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BrandConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    name: str = "Artisan Bakery"
    tagline: str = "Nền Tảng Quản Trị & Bán Hàng Chuyên Biệt Cho Chuỗi Tiệm Bánh"
    logo_url: str = "/emerald_bakery_logo.png"
    subdomain_suffix: str = ".artisan.vn"


class NavItemConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    label: str
    href: str


class HeroConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    badge: str = "GIẢI PHÁP ERP CHUYÊN SÂU F&B"
    title: str = "Nền Tảng Quản Trị & Bán Hàng Chuyên Biệt Cho Chuỗi Tiệm Bánh"
    subtitle: str = "Đột phá doanh thu với hệ thống POS đa kênh, đồng bộ thời gian thực từ khâu nhào bột đến bàn giao két tiền từng ca làm việc."
    cta_primary_text: str = "Khởi Tạo Dùng Thử 14 Ngày"
    cta_secondary_text: str = "Trải Nghiệm Trực Tiếp POS"
    checklist: List[str] = [
        "14 ngày dùng thử miễn phí",
        "Không cần thẻ tín dụng",
        "Thiết lập sau 60 giây"
    ]
    sample_subdomain: str = "la-petite-paris"


class FeatureItemConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: str
    title: str
    subtitle: str
    description: str
    icon: str
    bullets: List[str] = []


class SolutionItemConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    title: str
    desc: str
    icon: str


class PricingPlanConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: str
    name: str
    monthly_price: int
    yearly_price: int
    period: str = "tháng"
    desc: str
    is_popular: bool = False
    features: List[str]
    button_text: str = "Đăng Ký Gói"


class TestimonialConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    quote: str
    author: str
    role: str
    avatar: str
    rating: int = 5


class FAQConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    q: str
    a: str


class FooterConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    about: str
    hotline: str
    email: str
    address: str
    copyright: str


class LandingPageConfigSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    brand: BrandConfig
    nav: List[NavItemConfig]
    hero: HeroConfig
    features: List[FeatureItemConfig]
    solutions: List[SolutionItemConfig]
    pricing_plans: List[PricingPlanConfig]
    testimonials: List[TestimonialConfig]
    faqs: List[FAQConfig]
    footer: FooterConfig
    is_published: bool = True
    version: Optional[int] = 1
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
