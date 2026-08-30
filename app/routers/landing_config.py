from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_permission
from app.models.landing_config import LandingPageConfig
from app.models.user import User
from app.schemas.landing_config import LandingPageConfigSchema

router = APIRouter(tags=["Landing Page CMS"])

DEFAULT_LANDING_CONFIG = {
    "brand": {
        "name": "Artisan Bakery",
        "tagline": "Nền Tảng Quản Trị & Bán Hàng Chuyên Biệt Cho Chuỗi Tiệm Bánh",
        "logoUrl": "/emerald_bakery_logo.png",
        "subdomainSuffix": ".artisan.vn"
    },
    "nav": [
        {"label": "Tính Năng", "href": "#features"},
        {"label": "Giải Pháp Chuỗi", "href": "#solutions"},
        {"label": "Bảng Giá Thuê Bao", "href": "#pricing"},
        {"label": "Khách Hàng", "href": "#testimonials"},
        {"label": "Hỏi Đáp (FAQ)", "href": "#faq"}
    ],
    "hero": {
        "badge": "GIẢI PHÁP ERP CHUYÊN SÂU F&B",
        "title": "Nền Tảng Quản Trị & Bán Hàng Chuyên Biệt Cho Chuỗi Tiệm Bánh",
        "subtitle": "Đột phá doanh thu với hệ thống POS đa kênh, đồng bộ thời gian thực từ khâu nhào bột đến bàn giao két tiền từng ca làm việc.",
        "ctaPrimaryText": "Khởi Tạo Dùng Thử 14 Ngày",
        "ctaSecondaryText": "Trải Nghiệm Trực Tiếp POS",
        "checklist": [
            "14 ngày dùng thử miễn phí",
            "Không cần thẻ tín dụng",
            "Thiết lập sau 60 giây"
        ],
        "sampleSubdomain": "la-petite-paris"
    },
    "features": [
        {
            "id": "pos",
            "title": "Quầy POS Bán Hàng & Chốt Ca Két Tiền",
            "subtitle": "Tối ưu hóa thao tác thu ngân, in bill tức thì, thanh toán VietQR động và chốt ca tiền mặt không sai một đồng.",
            "description": "Giao diện cảm ứng trực quan, phân nhóm mẻ bánh thông minh, hỗ trợ thanh toán đa phương thức và đối soát két tiền từng ca minh bạch.",
            "icon": "ShoppingCartOutlined",
            "bullets": [
                "Thanh toán QR động VietQR tự động khớp hóa đơn",
                "Quản lý mở ca, chốt ca, kiểm đếm tiền mặt thực tế",
                "In hóa đơn nhiệt và biên bản bàn giao két tiền chuẩn hóa",
                "Hoạt động mượt mà cả khi kết nối mạng chập chờn"
            ]
        },
        {
            "id": "inventory",
            "title": "Quản Lý Đa Kho & Cảnh Báo Hết Hạn",
            "subtitle": "Kiểm soát mẻ bánh theo thời hạn sử dụng trong ngày (Shelf-life) và tự động đồng bộ tồn kho đa điểm.",
            "description": "Theo dõi nguyên vật liệu nhập/xuất/tồn, cảnh báo bánh sắp hết hạn để chủ động giảm giá giờ vàng (Happy Hour).",
            "icon": "AppstoreOutlined",
            "bullets": [
                "Cảnh báo tồn kho an toàn và bánh cận date tự động",
                "Điều chuyển hàng hóa giữa các chi nhánh chỉ trong 1 chạm",
                "Hạch toán hao hụt mẻ nướng và định lượng nguyên liệu chuẩn",
                "Báo cáo tỷ lệ huỷ hàng và tối ưu kế hoạch làm bánh"
            ]
        },
        {
            "id": "reports",
            "title": "Báo Cáo Doanh Thu & Sổ Quỹ Lãi Lỗ P&L",
            "subtitle": "Nắm bắt sức khỏe tài chính toàn chuỗi tức thời với biểu đồ phân tích chuyên sâu.",
            "description": "Hệ thống tự động tổng hợp doanh thu, chi phí nguyên liệu, chi phí mặt bằng và lợi nhuận ròng từng chi nhánh.",
            "icon": "DashboardOutlined",
            "bullets": [
                "Báo cáo Doanh thu theo giờ, sản phẩm bán chạy (Top Selling)",
                "Hiệu suất bán hàng của từng nhân viên thu ngân trong ca",
                "Sổ quỹ thu - chi và đối chiếu dòng tiền mặt vs ngân hàng",
                "Xuất file Excel báo cáo kế toán chỉ với 1 cú nhấp chuột"
            ]
        }
    ],
    "solutions": [
        {
            "title": "Bán Hàng Siêu Tốc Giờ Cao Điểm",
            "desc": "Thao tác chọn món và thanh toán QR chỉ mất 3 giây. Không còn cảnh khách xếp hàng dài chờ đợi giờ sáng.",
            "icon": "ThunderboltOutlined"
        },
        {
            "title": "Kiểm Soát Thất Thoát Tiền Mặt",
            "desc": "Chốt ca làm việc minh bạch. Hệ thống tự động so khớp tiền mặt đầu ca, doanh thu trong ca và số tiền thực kiểm đếm khi bàn giao két.",
            "icon": "SafetyCertificateOutlined"
        },
        {
            "title": "Báo Cáo Tài Chính Real-time",
            "desc": "Tự động hạch toán phiếu thu - chi tiền mặt & ngân hàng. Báo cáo Doanh thu thuần, Giá vốn (COGS) và Lợi nhuận ròng thời gian thực.",
            "icon": "LineChartOutlined"
        },
        {
            "title": "Mở Rộng Chuỗi Không Giới Hạn",
            "desc": "Quản lý 10, 50 hay 100 chi nhánh trên cùng 1 hệ thống tập trung. Phân quyền chặt chẽ từng nhân viên và quản lý kho tổng.",
            "icon": "BranchesOutlined"
        }
    ],
    "pricingPlans": [
        {
            "id": "starter",
            "name": "Khởi Nghiệp (Starter)",
            "monthlyPrice": 199000,
            "yearlyPrice": 159000,
            "period": "tháng",
            "desc": "Dành cho tiệm bánh đơn lẻ, quầy bánh nhỏ mới khai trương.",
            "isPopular": False,
            "features": [
                "1 Chi nhánh quầy bán lẻ",
                "Không giới hạn số lượng sản phẩm",
                "Quầy POS bán hàng & In hóa đơn",
                "Quản lý Ca & Két tiền mặt",
                "Thanh toán VietQR động",
                "Báo cáo doanh thu cơ bản"
            ],
            "buttonText": "Bắt Đầu Dùng Thử"
        },
        {
            "id": "growth",
            "name": "Tăng Trưởng (Growth)",
            "monthlyPrice": 499000,
            "yearlyPrice": 399000,
            "period": "tháng",
            "desc": "Dành cho tiệm bánh đang mở rộng từ 2 - 5 chi nhánh.",
            "isPopular": True,
            "features": [
                "Tối đa 5 Chi nhánh liên kết",
                "Quản lý kho đa điểm & Điều chuyển kho",
                "Phân quyền Nhân viên & Thu ngân",
                "Sổ Quỹ Thu Chi & Báo cáo Lãi Lỗ P&L",
                "Cảnh báo hàng cận hạn tự động",
                "Hỗ trợ kỹ thuật ưu tiên 24/7"
            ],
            "buttonText": "Trải Nghiệm Gói Hot"
        },
        {
            "id": "enterprise",
            "name": "Chuỗi Lớn (Enterprise)",
            "monthlyPrice": 999000,
            "yearlyPrice": 799000,
            "period": "tháng",
            "desc": "Dành cho chuỗi thương hiệu bánh quy mô lớn trên 5 chi nhánh.",
            "isPopular": False,
            "features": [
                "Không giới hạn số lượng Chi nhánh",
                "Kho tổng sản xuất & Phân phối",
                "Tùy biến Subdomain & Domain riêng",
                "Tích hợp API phần mềm kế toán",
                "Báo cáo tài chính chuyên sâu",
                "Chuyên viên triển khai Onboarding riêng"
            ],
            "buttonText": "Liên Hệ Doanh Nghiệp"
        }
    ],
    "testimonials": [
        {
            "quote": "Từ khi dùng hệ thống, tình trạng lệch tiền mặt cuối ca hoàn toàn chấm dứt. Nhân viên bàn giao két trong 2 phút là xong.",
            "author": "Chị Mai Hương",
            "role": "Chủ chuỗi Bánh Mì Hương Mai (4 cơ sở)",
            "avatar": "H",
            "rating": 5
        },
        {
            "quote": "Tính năng cảnh báo bánh cận date giúp tiệm giảm hơn 40% lượng bánh huỷ mỗi ngày nhờ chạy chương trình xả bánh đúng lúc.",
            "author": "Anh Hoàng Nam",
            "role": "Founder Nam Pastry & Cafe",
            "avatar": "N",
            "rating": 5
        },
        {
            "quote": "Báo cáo P&L tự động giúp tôi nắm rõ lợi nhuận từng cửa hàng mỗi tối mà không cần đợi kế toán làm sổ sách cuối tháng.",
            "author": "Chị Ngọc Lan",
            "role": "Giám đốc Vận hành Tiệm Bánh Madame Lan",
            "avatar": "L",
            "rating": 5
        }
    ],
    "faqs": [
        {
            "q": "Tôi có cần cài đặt phần mềm phức tạp trên máy tính không?",
            "a": "Hoàn toàn không. Hệ thống hoạt động 100% trên nền tảng Web đám mây. Bạn có thể sử dụng trên bất kỳ thiết bị nào như iPad, máy POS cầm tay, laptop hoặc điện thoại thông minh."
        },
        {
            "q": "Phần mềm có hỗ trợ máy in bill nhiệt và ngăn kéo đựng tiền không?",
            "a": "Có, hệ thống tương thích với 100% các dòng máy in nhiệt chuẩn khổ 80mm/58mm (kết nối USB, LAN hoặc Wifi) và hỗ trợ tự động bật két tiền khi thanh toán."
        },
        {
            "q": "Sau 14 ngày dùng thử, dữ liệu của tôi có bị mất không?",
            "a": "Toàn bộ dữ liệu menu, danh mục bánh và chi nhánh được lưu trữ an toàn trên cloud. Khi nâng cấp gói chính thức, bạn có thể tiếp tục kinh doanh ngay lập tức."
        },
        {
            "q": "Tôi có thể thanh toán phí thuê bao bằng hình thức nào?",
            "a": "Hỗ trợ thanh toán linh hoạt qua chuyển khoản ngân hàng (VietQR tự động kích hoạt ngay sau 5 giây), thẻ tín dụng quốc tế hoặc thẻ ATM nội địa."
        }
    ],
    "footer": {
        "about": "Hệ thống quản trị và vận hành chuyên sâu dành riêng cho chuỗi tiệm bánh mì, bánh ngọt và bakery cafe hiện đại.",
        "hotline": "1900 6868 (8:00 - 22:00)",
        "email": "hotro@artisanbakery.vn",
        "address": "Tòa nhà Innovation Hub, Quận 1, TP. Hồ Chí Minh",
        "copyright": "© 2026 Artisan Bakery SaaS Platform. Bản quyền thuộc về Đội ngũ Kỹ sư Công nghệ F&B."
    }
}


def get_or_create_config(db: Session) -> LandingPageConfig:
    config = db.query(LandingPageConfig).filter(LandingPageConfig.id == "landing-config-current").first()
    if not config:
        config = LandingPageConfig(
            id="landing-config-current",
            version=1,
            is_published=True,
            brand=DEFAULT_LANDING_CONFIG["brand"],
            nav=DEFAULT_LANDING_CONFIG["nav"],
            hero=DEFAULT_LANDING_CONFIG["hero"],
            features=DEFAULT_LANDING_CONFIG["features"],
            solutions=DEFAULT_LANDING_CONFIG["solutions"],
            pricing_plans=DEFAULT_LANDING_CONFIG["pricingPlans"],
            testimonials=DEFAULT_LANDING_CONFIG["testimonials"],
            faqs=DEFAULT_LANDING_CONFIG["faqs"],
            footer=DEFAULT_LANDING_CONFIG["footer"],
            updated_at=datetime.now(timezone.utc),
            updated_by="system"
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.get("/landing-page-config", response_model=LandingPageConfigSchema)
def get_public_landing_config(db: Session = Depends(get_db)):
    """Public API: Get current published landing page configuration for marketing route '/'."""
    config = get_or_create_config(db)
    return config


@router.get("/admin/landing-page-config", response_model=LandingPageConfigSchema)
def get_admin_landing_config(
    current_user: User = Depends(require_permission("landing_page:edit")),
    db: Session = Depends(get_db)
):
    """SuperAdmin API: Get current draft/editable landing page configuration."""
    config = get_or_create_config(db)
    return config


@router.put("/admin/landing-page-config", response_model=LandingPageConfigSchema)
def update_admin_landing_config(
    payload: LandingPageConfigSchema,
    current_user: User = Depends(require_permission("landing_page:edit")),
    db: Session = Depends(get_db)
):
    """SuperAdmin API: Save and publish updated landing page configuration."""
    config = get_or_create_config(db)
    
    config.brand = payload.brand.model_dump(by_alias=True)
    config.nav = [item.model_dump(by_alias=True) for item in payload.nav]
    config.hero = payload.hero.model_dump(by_alias=True)
    config.features = [item.model_dump(by_alias=True) for item in payload.features]
    config.solutions = [item.model_dump(by_alias=True) for item in payload.solutions]
    config.pricing_plans = [item.model_dump(by_alias=True) for item in payload.pricing_plans]
    config.testimonials = [item.model_dump(by_alias=True) for item in payload.testimonials]
    config.faqs = [item.model_dump(by_alias=True) for item in payload.faqs]
    config.footer = payload.footer.model_dump(by_alias=True)
    config.version = (config.version or 1) + 1
    config.is_published = True
    config.updated_at = datetime.now(timezone.utc)
    config.updated_by = current_user.id

    db.commit()
    db.refresh(config)
    return config


@router.post("/admin/landing-page-config/reset", response_model=LandingPageConfigSchema)
def reset_admin_landing_config(
    current_user: User = Depends(require_permission("landing_page:edit")),
    db: Session = Depends(get_db)
):
    """SuperAdmin API: Reset landing page configuration to initial factory default."""
    config = get_or_create_config(db)
    
    config.brand = DEFAULT_LANDING_CONFIG["brand"]
    config.nav = DEFAULT_LANDING_CONFIG["nav"]
    config.hero = DEFAULT_LANDING_CONFIG["hero"]
    config.features = DEFAULT_LANDING_CONFIG["features"]
    config.solutions = DEFAULT_LANDING_CONFIG["solutions"]
    config.pricing_plans = DEFAULT_LANDING_CONFIG["pricingPlans"]
    config.testimonials = DEFAULT_LANDING_CONFIG["testimonials"]
    config.faqs = DEFAULT_LANDING_CONFIG["faqs"]
    config.footer = DEFAULT_LANDING_CONFIG["footer"]
    config.version = (config.version or 1) + 1
    config.is_published = True
    config.updated_at = datetime.now(timezone.utc)
    config.updated_by = current_user.id

    db.commit()
    db.refresh(config)
    return config
