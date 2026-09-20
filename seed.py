from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo
import sqlalchemy as sa
from app.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.stock import StockItem
from app.models.branch import Branch, Warehouse
from app.models.transaction import Transaction
from app.models.shift import WorkShift
from app.models.setting import SystemSetting, ShiftTemplate
from app.models.landing_config import LandingPageConfig
from app.models.permission import Permission
from app.models.role import Role, role_permissions
from app.models.audit_log import AuditLog
from app.core.rbac_config import ALL_PERMISSIONS, SYSTEM_ROLES_CONFIG
from app.routers.landing_config import DEFAULT_LANDING_CONFIG
from app.routers.settings import DEFAULT_SETTINGS


def seed_database():
    print("🌱 Bắt đầu nạp dữ liệu mẫu (Seed Data) vào PostgreSQL...")
    db = SessionLocal()

    try:
        # Tạo tables nếu chưa có
        Base.metadata.create_all(bind=engine)
        with engine.connect() as conn:
            conn.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id VARCHAR(50) REFERENCES roles(id) ON DELETE SET NULL;"))
            conn.commit()

        # Xóa dữ liệu cũ theo đúng thứ tự khóa ngoại (bảng con trước, bảng cha sau)
        db.query(OrderItem).delete()
        db.query(Order).delete()
        db.query(StockItem).delete()
        db.query(WorkShift).delete()
        db.query(Transaction).delete()
        db.query(AuditLog).delete()
        db.query(Product).delete()
        db.query(Warehouse).delete()
        db.query(User).delete()
        db.query(Branch).delete()
        db.execute(role_permissions.delete())
        db.query(Role).delete()
        db.query(Permission).delete()
        db.query(ShiftTemplate).delete()
        db.query(SystemSetting).delete()
        db.query(LandingPageConfig).delete()
        db.commit()

        # 0. TẠO 21 PERMISSIONS
        perm_map = {}
        for p in ALL_PERMISSIONS:
            perm = Permission(
                id=f"perm-{p['code'].replace(':', '-')}",
                code=p["code"],
                name=p["name"],
                module=p["module"],
                description=p["description"],
                created_at=datetime.now(timezone.utc) - timedelta(days=120)
            )
            db.add(perm)
            perm_map[p["code"]] = perm
        db.flush()
        print(f"✅ Đã tạo {len(ALL_PERMISSIONS)} quyền nguyên tử (Permissions).")

        # 0.1. TẠO 3 ROLES GỐC
        role_objs = {}
        for r_code, r_cfg in SYSTEM_ROLES_CONFIG.items():
            r = Role(
                id=r_cfg["id"],
                code=r_cfg["code"],
                name=r_cfg["name"],
                description=r_cfg["description"],
                is_system=r_cfg["is_system"],
                permissions_version=1,
                created_at=datetime.now(timezone.utc) - timedelta(days=120)
            )
            # Attach permissions
            r.permissions = [perm_map[code] for code in r_cfg["permissions"] if code in perm_map]
            db.add(r)
            role_objs[r_code] = r
        db.flush()
        print("✅ Đã tạo 3 vai trò hệ thống gốc (SUPER_ADMIN, ADMIN, STAFF).")

        # 0.2. TẠO 2 CHI NHÁNH & 3 KHO HÀNG
        b1 = Branch(
            id="branch-001",
            code="CN-Q1",
            name="Artisan Bakery - Chi Nhánh Quận 1 (Trụ Sở)",
            address="123 Đường Đồng Khởi, Bến Nghé, Quận 1, TP.HCM",
            phone="0901 234 567",
            manager_name="Nguyễn Quản Trị",
            status="ACTIVE"
        )
        b2 = Branch(
            id="branch-002",
            code="CN-TD",
            name="Artisan Bakery - Chi Nhánh Thảo Điền",
            address="45 Đường Xuân Thủy, Thảo Điền, TP. Thủ Đức, TP.HCM",
            phone="0909 888 777",
            manager_name="Lê Thu Hà",
            status="ACTIVE"
        )
        db.add_all([b1, b2])
        db.flush()

        w1 = Warehouse(id="wh-001", branch_id=b1.id, code="KHO-Q1-POS", name="Kho Quầy Bán Lẻ Q1", warehouse_type="RETAIL", status="ACTIVE")
        w2 = Warehouse(id="wh-002", branch_id=b1.id, code="KHO-Q1-COLD", name="Kho Lạnh Bảo Quản Q1", warehouse_type="COLD_STORAGE", status="ACTIVE")
        w3 = Warehouse(id="wh-003", branch_id=b2.id, code="KHO-TD-POS", name="Kho Quầy Bán Lẻ Thảo Điền", warehouse_type="RETAIL", status="ACTIVE")
        db.add_all([w1, w2, w3])
        db.flush()
        print("✅ Đã tạo 2 chi nhánh và 3 kho lưu trữ (wh-001, wh-002, wh-003).")

        # 1. TẠO USERS
        superadmin_user = User(
            id="user-000",
            username="superadmin",
            hashed_password=get_password_hash("password123"),
            full_name="Tổng Quản Trị Hệ Thống",
            email="superadmin@artisanbakery.vn",
            phone="0999888777",
            role_id=role_objs["SUPER_ADMIN"].id,
            role="SUPER_ADMIN",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc) - timedelta(days=90)
        )

        admin_user = User(
            id="user-001",
            username="admin",
            hashed_password=get_password_hash("password123"),
            full_name="Nguyễn Quản Trị",
            email="admin@artisanbakery.vn",
            phone="0901234567",
            role_id=role_objs["ADMIN"].id,
            role="ADMIN",
            default_branch_id="branch-001",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc) - timedelta(days=60)
        )

        staff_user1 = User(
            id="user-002",
            username="staff",
            hashed_password=get_password_hash("password123"),
            full_name="Trần Thị Thu Ngân",
            email="thungan@artisanbakery.vn",
            phone="0912345678",
            role_id=role_objs["STAFF"].id,
            role="STAFF",
            default_branch_id="branch-001",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc) - timedelta(days=30)
        )

        staff_user2 = User(
            id="user-003",
            username="lethuha",
            hashed_password=get_password_hash("password123"),
            full_name="Lê Thu Hà",
            email="thuha@artisanbakery.vn",
            phone="0988776655",
            role_id=role_objs["STAFF"].id,
            role="STAFF",
            default_branch_id="branch-002",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc) - timedelta(days=20)
        )

        staff_user3 = User(
            id="user-004",
            username="phamminh",
            hashed_password=get_password_hash("password123"),
            full_name="Phạm Minh Bếp Bánh",
            email="minh.chef@artisanbakery.vn",
            phone="0977665544",
            role_id=role_objs["STAFF"].id,
            role="STAFF",
            default_branch_id="branch-001",
            status="INACTIVE",
            created_at=datetime.now(timezone.utc) - timedelta(days=10)
        )

        db.add_all([superadmin_user, admin_user, staff_user1, staff_user2, staff_user3])
        db.commit()
        print("✅ Đã tạo 5 tài khoản người dùng mẫu (superadmin/admin/staff/lethuha/phamminh).")

        # 2. TẠO PRODUCTS
        products = [
            Product(
                id="prod-001",
                name="Croissant Bơ Pháp Truyền Thống",
                category="Bánh Mì Ngọt & Pastry",
                price=35000,
                stock=45,
                description="Vỏ bánh ngàn lớp giòn xốp, thơm nồng mùi bơ Pháp nhập khẩu cao cấp Elle & Vire.",
                image="https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=400&q=80",
                created_at=datetime.now(timezone.utc) - timedelta(days=15)
            ),
            Product(
                id="prod-002",
                name="Sourdough Men Tự Nhiên (500g)",
                category="Bánh Mì Nghệ Nhân (Artisan)",
                price=65000,
                stock=14,
                description="Lên men chậm tự nhiên 24h, vị chua dịu thanh lịch, tốt cho hệ tiêu hóa.",
                image="https://images.unsplash.com/photo-1589367920969-ab8e050bbb04?w=400&q=80",
                created_at=datetime.now(timezone.utc) - timedelta(days=15)
            ),
            Product(
                id="prod-003",
                name="Pain au Chocolat (Bánh Sô-cô-la)",
                category="Bánh Mì Ngọt & Pastry",
                price=40000,
                stock=28,
                description="Bánh cuộn với nhân thanh sô-cô-la đen nguyên chất Valrhona 70%.",
                image="https://images.unsplash.com/photo-1608198093002-ad4e005484ec?w=400&q=80",
                created_at=datetime.now(timezone.utc) - timedelta(days=14)
            ),
            Product(
                id="prod-004",
                name="Baguette Pháp Truyền Thống",
                category="Bánh Mì Nghệ Nhân (Artisan)",
                price=25000,
                stock=35,
                description="Ổ bánh dài kinh điển nước Pháp, vỏ giòn rụm, ruột dẻo thơm hạt lúa mạch.",
                image="https://images.unsplash.com/photo-1597079910443-60c43fc4f749?w=400&q=80",
                created_at=datetime.now(timezone.utc) - timedelta(days=14)
            ),
            Product(
                id="prod-005",
                name="Bánh Kem Dâu Tây Matcha Nhật Bản",
                category="Bánh Kem & Sinh Nhật",
                price=280000,
                stock=6,
                description="Cốt bánh bông lan trà xanh Uji kết hợp kem whipping béo ngậy và dâu tây Đà Lạt tươi.",
                image="https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=400&q=80",
                created_at=datetime.now(timezone.utc) - timedelta(days=12)
            ),
            Product(
                id="prod-006",
                name="Tiramisu Cacao Mascarpone Ý",
                category="Bánh Kem & Sinh Nhật",
                price=55000,
                stock=18,
                description="Lớp bánh sâm-panh đẫm cà phê espresso hòa quyện phô mai mascarpone béo ngậy.",
                image="https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=400&q=80",
                created_at=datetime.now(timezone.utc) - timedelta(days=10)
            ),
            Product(
                id="prod-007",
                name="Cinnamon Roll Phủ Kem Phô Mai",
                category="Bánh Mì Ngọt & Pastry",
                price=42000,
                stock=22,
                description="Bánh quế cuộn ngọt ngào thơm nức mũi với lớp phủ kem phô mai chua ngọt mịn màng.",
                image="https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&q=80",
                created_at=datetime.now(timezone.utc) - timedelta(days=8)
            ),
            Product(
                id="prod-008",
                name="Cà Phê Muối Kem Béo Artisan",
                category="Cà Phê & Đồ Uống",
                price=35000,
                stock=99,
                description="Cà phê pha phin truyền thống phối kem muối mặn mà độc đáo theo công thức riêng.",
                image="https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400&q=80",
                created_at=datetime.now(timezone.utc) - timedelta(days=7)
            ),
            Product(
                id="prod-009",
                name="Trà Sữa Oolong Nướng Trân Châu",
                category="Cà Phê & Đồ Uống",
                price=38000,
                stock=80,
                description="Trà Oolong đậm đà rang mộc kết hợp sữa tươi thanh trùng và trân châu hoàng kim.",
                image="https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=400&q=80",
                created_at=datetime.now(timezone.utc) - timedelta(days=6)
            ),
            Product(
                id="prod-010",
                name="Bánh Mì Phô Mai Bơ Tỏi Hàn Quốc",
                category="Bánh Mì Ngọt & Pastry",
                price=48000,
                stock=3,  # Cảnh báo sắp hết (low_stock)
                description="Sốt bơ tỏi thơm lừng thấm đẫm 6 múi bánh ngập phô mai cream cheese.",
                image="https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=400&q=80",
                created_at=datetime.now(timezone.utc) - timedelta(days=5)
            ),
            Product(
                id="prod-011",
                name="Cheesecake Cháy San Sebastian",
                category="Bánh Kem & Sinh Nhật",
                price=60000,
                stock=0,  # Cảnh báo hết hàng (out_of_stock)
                description="Bánh phô mai nướng xém mặt ngoài, bên trong mềm tan chảy béo ngậy.",
                image="https://images.unsplash.com/photo-1533134242443-d4fd215305ad?w=400&q=80",
                created_at=datetime.now(timezone.utc) - timedelta(days=4)
            ),
        ]
        db.add_all(products)
        db.commit()
        print("✅ Đã nạp 11 sản phẩm bánh mẫu với đầy đủ danh mục và các trạng thái tồn kho.")

        # 2.1. TẠO TỒN KHO CHI TIẾT (stock_items) - SUM KHỚP ĐÚNG 100% TỒN KHO SẢN PHẨM
        # wh-001: Kho Quầy Bán Lẻ Q1 | wh-002: Kho Lạnh Q1 | wh-003: Kho Quầy Thảo Điền
        stock_distribution = {
            "prod-001": [("wh-001", 25), ("wh-002", 10), ("wh-003", 10)],  # 45
            "prod-002": [("wh-001", 8),  ("wh-002", 0),  ("wh-003", 6)],   # 14
            "prod-003": [("wh-001", 15), ("wh-002", 5),  ("wh-003", 8)],   # 28
            "prod-004": [("wh-001", 20), ("wh-002", 5),  ("wh-003", 10)],  # 35
            "prod-005": [("wh-001", 3),  ("wh-002", 1),  ("wh-003", 2)],   # 6
            "prod-006": [("wh-001", 10), ("wh-002", 3),  ("wh-003", 5)],   # 18
            "prod-007": [("wh-001", 12), ("wh-002", 2),  ("wh-003", 8)],   # 22
            "prod-008": [("wh-001", 50), ("wh-002", 20), ("wh-003", 29)],  # 99
            "prod-009": [("wh-001", 40), ("wh-002", 20), ("wh-003", 20)],  # 80
            "prod-010": [("wh-001", 2),  ("wh-002", 0),  ("wh-003", 1)],   # 3
            "prod-011": [("wh-001", 0),  ("wh-002", 0),  ("wh-003", 0)],   # 0
        }

        stock_items = []
        for p_id, wh_allocations in stock_distribution.items():
            for wh_id, qty in wh_allocations:
                stock_items.append(StockItem(
                    id=f"stk-{wh_id}-{p_id}",
                    warehouse_id=wh_id,
                    product_id=p_id,
                    quantity=qty,
                    min_alert_stock=5
                ))
        db.add_all(stock_items)
        db.commit()
        print(f"✅ Đã nạp {len(stock_items)} bản ghi tồn kho chi nhánh (stock_items) cho 11 sản phẩm.")

        # 3. TẠO WORK SHIFTS (CA ĐÃ CHỐT, KHÔNG CÓ CA MỞ)
        vn_tz = ZoneInfo("Asia/Ho_Chi_Minh")
        now_vn = datetime.now(vn_tz)
        yesterday_vn = now_vn - timedelta(days=1)
        two_days_ago_vn = now_vn - timedelta(days=2)

        yesterday_d = yesterday_vn.date()
        two_days_ago_d = two_days_ago_vn.date()

        y_prefix = yesterday_vn.strftime("%y%m%d")
        two_d_prefix = two_days_ago_vn.strftime("%y%m%d")

        # 2 Ca chốt hôm qua
        shift_y1 = WorkShift(
            id="shift-001",
            branch_id="branch-001",
            template_id="tmpl-001",
            shift_name=f"Ca Sáng (06:00 - 14:00) - {yesterday_vn.strftime('%d/%m/%Y')}",
            staff_id="user-002",
            staff_name="Trần Thị Thu Ngân",
            start_time=datetime.combine(yesterday_d, time(6, 0)).replace(tzinfo=vn_tz).astimezone(timezone.utc),
            end_time=datetime.combine(yesterday_d, time(14, 0)).replace(tzinfo=vn_tz).astimezone(timezone.utc),
            initial_cash=500000,
            cash_revenue=100000,
            card_revenue=380000,
            qr_revenue=140000,
            total_revenue=620000,
            orders_count=3,
            expected_cash=600000,
            actual_cash=600000,
            difference=0,
            status="CLOSED",
            note="Bàn giao ca sáng đủ tiền mặt, không thất thoát"
        )

        shift_y2 = WorkShift(
            id="shift-002",
            branch_id="branch-002",
            template_id="tmpl-002",
            shift_name=f"Ca Chiều (14:00 - 22:00) - {yesterday_vn.strftime('%d/%m/%Y')}",
            staff_id="user-003",
            staff_name="Lê Thu Hà",
            start_time=datetime.combine(yesterday_d, time(14, 0)).replace(tzinfo=vn_tz).astimezone(timezone.utc),
            end_time=datetime.combine(yesterday_d, time(22, 0)).replace(tzinfo=vn_tz).astimezone(timezone.utc),
            initial_cash=500000,
            cash_revenue=115000,
            card_revenue=0,
            qr_revenue=761000,
            total_revenue=876000,
            orders_count=3,
            expected_cash=615000,
            actual_cash=615000,
            difference=0,
            status="CLOSED",
            note="Kết ca chiều khớp doanh thu POS"
        )

        shift_2d = WorkShift(
            id="shift-003",
            branch_id="branch-001",
            template_id="tmpl-001",
            shift_name=f"Ca Sáng (06:00 - 14:00) - {two_days_ago_vn.strftime('%d/%m/%Y')}",
            staff_id="user-002",
            staff_name="Trần Thị Thu Ngân",
            start_time=datetime.combine(two_days_ago_d, time(6, 0)).replace(tzinfo=vn_tz).astimezone(timezone.utc),
            end_time=datetime.combine(two_days_ago_d, time(14, 0)).replace(tzinfo=vn_tz).astimezone(timezone.utc),
            initial_cash=500000,
            cash_revenue=0,
            card_revenue=0,
            qr_revenue=320000,
            total_revenue=320000,
            orders_count=1,
            expected_cash=500000,
            actual_cash=500000,
            difference=0,
            status="CLOSED",
            note="Ca sáng ngày hôm kia hoàn tất"
        )

        db.add_all([shift_y1, shift_y2, shift_2d])
        db.flush()
        print("✅ Đã nạp 3 ca làm việc mẫu (WorkShift) ĐÃ CHỐT (không có ca mở).")

        # 4. TẠO TRANSACTIONS MẪU (SỔ QUỸ THU CHI)
        tx1 = Transaction(
            id="tx-001",
            code=f"PT-{y_prefix}-001",
            transaction_type="INCOME",
            category="Thu doanh thu bán lẻ POS",
            amount=2450000,
            branch_id="branch-001",
            payment_method="BANK_TRANSFER",
            recipient_payer="Khách hàng tổng hợp",
            note="Doanh thu bán hàng ca sáng chuyển khoản VietQR",
            created_by="Hệ thống POS",
            created_at=datetime.combine(yesterday_d, time(13, 30)).replace(tzinfo=vn_tz).astimezone(timezone.utc)
        )
        tx2 = Transaction(
            id="tx-002",
            code=f"PC-{y_prefix}-001",
            transaction_type="EXPENSE",
            category="Chi phí Nguyên vật liệu & Nhập hàng",
            amount=850000,
            branch_id="branch-001",
            payment_method="BANK_TRANSFER",
            recipient_payer="Công ty TNHH Bơ Sữa Pháp Anchor",
            note="Nhập 20kg bơ lạt Pháp và 50kg bột mì T55",
            created_by="Nguyễn Quản Trị",
            created_at=datetime.combine(yesterday_d, time(10, 0)).replace(tzinfo=vn_tz).astimezone(timezone.utc)
        )
        tx3 = Transaction(
            id="tx-003",
            code=f"PC-{y_prefix}-002",
            transaction_type="EXPENSE",
            category="Chi phí Điện, Nước & Tiện ích",
            amount=320000,
            branch_id="branch-001",
            payment_method="BANK_TRANSFER",
            recipient_payer="Điện lực EVN TP.HCM",
            note="Tiền điện lò nướng công nghiệp",
            created_by="Nguyễn Quản Trị",
            created_at=datetime.combine(yesterday_d, time(11, 30)).replace(tzinfo=vn_tz).astimezone(timezone.utc)
        )
        tx4 = Transaction(
            id="tx-004",
            code=f"PC-{y_prefix}-003",
            transaction_type="EXPENSE",
            category="Chi phí Bao bì & Hộp bánh",
            amount=250000,
            branch_id="branch-001",
            payment_method="CASH",
            recipient_payer="Xưởng in bao bì Kraft Tân Bình",
            note="Nhập 500 túi giấy đựng croissant",
            created_by="Trần Thị Thu Ngân",
            created_at=datetime.combine(yesterday_d, time(9, 15)).replace(tzinfo=vn_tz).astimezone(timezone.utc)
        )
        tx5 = Transaction(
            id="tx-005",
            code=f"PT-{y_prefix}-002",
            transaction_type="INCOME",
            category="Thu bán bánh sinh nhật & sự kiện",
            amount=1850000,
            branch_id="branch-002",
            payment_method="BANK_TRANSFER",
            recipient_payer="Công ty Thiết Kế V-Creative",
            note="Đơn bánh tiệc teabreak chi nhánh Thảo Điền",
            created_by="Lê Thu Hà",
            created_at=datetime.combine(yesterday_d, time(16, 0)).replace(tzinfo=vn_tz).astimezone(timezone.utc)
        )
        tx6 = Transaction(
            id="tx-006",
            code=f"PC-{y_prefix}-004",
            transaction_type="EXPENSE",
            category="Chi phí Nguyên vật liệu & Nhập hàng",
            amount=620000,
            branch_id="branch-002",
            payment_method="CASH",
            recipient_payer="Đại lý Men & Trứng tươi Q2",
            note="Nhập trứng gà tươi và men nở lạt",
            created_by="Lê Thu Hà",
            created_at=datetime.combine(yesterday_d, time(17, 30)).replace(tzinfo=vn_tz).astimezone(timezone.utc)
        )
        db.add_all([tx1, tx2, tx3, tx4, tx5, tx6])
        db.flush()
        print("✅ Đã nạp 6 phiếu thu chi mẫu (Transactions).")

        # 5. TẠO 7 ĐƠN HÀNG LỊCH SỬ GẮN VỚI CA ĐÃ CHỐT
        # Đơn 1 (Thuộc shift_y1 - Hôm qua 08:30)
        order1 = Order(
            id="ord-1001",
            code=f"HD-{y_prefix}-01",
            customer_name="Khách lẻ - Anh Hoàng",
            customer_phone="0933112233",
            branch_id="branch-001",
            warehouse_id="wh-001",
            staff_id="user-002",
            staff_name="Trần Thị Thu Ngân",
            subtotal=140000,
            discount=0,
            total_amount=140000,
            payment_method="QR_TRANSFER",
            status="COMPLETED",
            note="Uống tại chỗ, ít ngọt",
            created_at=datetime.combine(yesterday_d, time(8, 30)).replace(tzinfo=vn_tz).astimezone(timezone.utc)
        )
        order1.items = [
            OrderItem(product_id="prod-001", product_name="Croissant Bơ Pháp Truyền Thống", price=35000, quantity=2, subtotal=70000, image="https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=400&q=80"),
            OrderItem(product_id="prod-008", product_name="Cà Phê Muối Kem Béo Artisan", price=35000, quantity=2, subtotal=70000, image="https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400&q=80")
        ]

        # Đơn 2 (Thuộc shift_y1 - Hôm qua 11:15)
        order2 = Order(
            id="ord-1002",
            code=f"HD-{y_prefix}-02",
            customer_name="Chị Mai Lan",
            customer_phone="0918889999",
            branch_id="branch-001",
            warehouse_id="wh-001",
            staff_id="user-002",
            staff_name="Trần Thị Thu Ngân",
            subtotal=380000,
            discount=0,
            total_amount=380000,
            payment_method="CARD",
            status="COMPLETED",
            note="Mang về, đóng hộp quà sinh nhật",
            created_at=datetime.combine(yesterday_d, time(11, 15)).replace(tzinfo=vn_tz).astimezone(timezone.utc)
        )
        order2.items = [
            OrderItem(product_id="prod-005", product_name="Bánh Kem Dâu Tây Matcha Nhật Bản", price=280000, quantity=1, subtotal=280000, image="https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=400&q=80"),
            OrderItem(product_id="prod-006", product_name="Tiramisu Cacao Mascarpone Ý", price=55000, quantity=1, subtotal=55000, image="https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=400&q=80"),
            OrderItem(product_id="prod-007", product_name="Cinnamon Roll Phủ Kem Phô Mai", price=42000, quantity=1, subtotal=42000, image="https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&q=80")
        ]

        # Đơn 3 (Thuộc shift_y2 - Hôm qua 15:00)
        order3 = Order(
            id="ord-1003",
            code=f"HD-{y_prefix}-03",
            customer_name="Khách vãng lai",
            customer_phone=None,
            branch_id="branch-002",
            warehouse_id="wh-003",
            staff_id="user-003",
            staff_name="Lê Thu Hà",
            subtotal=115000,
            discount=0,
            total_amount=115000,
            payment_method="CASH",
            status="COMPLETED",
            note="Cắt bánh Baguette thành lát",
            created_at=datetime.combine(yesterday_d, time(15, 0)).replace(tzinfo=vn_tz).astimezone(timezone.utc)
        )
        order3.items = [
            OrderItem(product_id="prod-004", product_name="Baguette Pháp Truyền Thống", price=25000, quantity=2, subtotal=50000, image="https://images.unsplash.com/photo-1597079910443-60c43fc4f749?w=400&q=80"),
            OrderItem(product_id="prod-002", product_name="Sourdough Men Tự Nhiên (500g)", price=65000, quantity=1, subtotal=65000, image="https://images.unsplash.com/photo-1589367920969-ab8e050bbb04?w=400&q=80")
        ]

        # Đơn 4 (Thuộc shift_2d - Hôm kia 10:20)
        order4 = Order(
            id="ord-1004",
            code=f"HD-{two_d_prefix}-01",
            customer_name="Bác Hùng Bakery Club",
            customer_phone="0909090909",
            branch_id="branch-001",
            warehouse_id="wh-001",
            staff_id="user-002",
            staff_name="Trần Thị Thu Ngân",
            subtotal=340000,
            discount=20000,
            total_amount=320000,
            payment_method="QR_TRANSFER",
            status="COMPLETED",
            note="Ưu đãi thành viên VIP",
            created_at=datetime.combine(two_days_ago_d, time(10, 20)).replace(tzinfo=vn_tz).astimezone(timezone.utc)
        )
        order4.items = [
            OrderItem(product_id="prod-001", product_name="Croissant Bơ Pháp Truyền Thống", price=35000, quantity=4, subtotal=140000, image="https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=400&q=80"),
            OrderItem(product_id="prod-003", product_name="Pain au Chocolat (Bánh Sô-cô-la)", price=40000, quantity=3, subtotal=120000, image="https://images.unsplash.com/photo-1608198093002-ad4e005484ec?w=400&q=80"),
            OrderItem(product_id="prod-008", product_name="Cà Phê Muối Kem Béo Artisan", price=35000, quantity=2, subtotal=70000, image="https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400&q=80")
        ]

        # Đơn 5 (Thuộc shift_y2 - Hôm qua 20:10)
        order5 = Order(
            id="ord-1005",
            code=f"HD-{y_prefix}-05",
            customer_name="Khách công ty FPT",
            customer_phone="0987654321",
            branch_id="branch-002",
            warehouse_id="wh-003",
            staff_id="user-003",
            staff_name="Lê Thu Hà",
            subtotal=650000,
            discount=20000,
            total_amount=630000,
            payment_method="QR_TRANSFER",
            status="COMPLETED",
            note="Tiệc trà teabreak chiều",
            created_at=datetime.combine(yesterday_d, time(20, 10)).replace(tzinfo=vn_tz).astimezone(timezone.utc)
        )
        order5.items = [
            OrderItem(product_id="prod-001", product_name="Croissant Bơ Pháp Truyền Thống", price=35000, quantity=10, subtotal=350000, image="https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=400&q=80"),
            OrderItem(product_id="prod-003", product_name="Pain au Chocolat (Bánh Sô-cô-la)", price=40000, quantity=5, subtotal=200000, image="https://images.unsplash.com/photo-1608198093002-ad4e005484ec?w=400&q=80"),
            OrderItem(product_id="prod-004", product_name="Baguette Pháp Truyền Thống", price=25000, quantity=4, subtotal=100000, image="https://images.unsplash.com/photo-1597079910443-60c43fc4f749?w=400&q=80")
        ]

        # Đơn hôm qua 1 (Thuộc shift_y1 - Hôm qua 09:00)
        order_y1 = Order(
            id="ord-0991",
            code=f"HD-{y_prefix}-06",
            customer_name="Cô Thu Ba",
            customer_phone="0903344556",
            branch_id="branch-001",
            warehouse_id="wh-001",
            staff_id="user-002",
            staff_name="Trần Thị Thu Ngân",
            subtotal=100000,
            discount=0,
            total_amount=100000,
            payment_method="CASH",
            status="COMPLETED",
            note="Khách quen",
            created_at=datetime.combine(yesterday_d, time(9, 0)).replace(tzinfo=vn_tz).astimezone(timezone.utc)
        )
        order_y1.items = [
            OrderItem(product_id="prod-002", product_name="Sourdough Men Tự Nhiên (500g)", price=65000, quantity=1, subtotal=65000, image="https://images.unsplash.com/photo-1589367920969-ab8e050bbb04?w=400&q=80"),
            OrderItem(product_id="prod-008", product_name="Cà Phê Muối Kem Béo Artisan", price=35000, quantity=1, subtotal=35000, image="https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400&q=80")
        ]

        # Đơn hôm qua 2 (Thuộc shift_y2 - Hôm qua 16:45)
        order_y2 = Order(
            id="ord-0992",
            code=f"HD-{y_prefix}-07",
            customer_name="Anh Tuấn",
            customer_phone="0912233445",
            branch_id="branch-002",
            warehouse_id="wh-003",
            staff_id="user-003",
            staff_name="Lê Thu Hà",
            subtotal=131000,
            discount=0,
            total_amount=131000,
            payment_method="QR_TRANSFER",
            status="COMPLETED",
            note="Giao trước 17h",
            created_at=datetime.combine(yesterday_d, time(16, 45)).replace(tzinfo=vn_tz).astimezone(timezone.utc)
        )
        order_y2.items = [
            OrderItem(product_id="prod-007", product_name="Cinnamon Roll Phủ Kem Phô Mai", price=42000, quantity=1, subtotal=42000, image="https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&q=80"),
            OrderItem(product_id="prod-009", product_name="Trà Sữa Oolong Nướng Trân Châu", price=38000, quantity=1, subtotal=38000, image="https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=400&q=80"),
            OrderItem(product_id="prod-006", product_name="Tiramisu Cacao Mascarpone Ý", price=55000, quantity=1, subtotal=55000, image="https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=400&q=80")
        ]

        db.add_all([order1, order2, order3, order4, order5, order_y1, order_y2])
        db.commit()
        print("✅ Đã nạp 7 đơn hàng mẫu (gắn với ca đã chốt của ngày trước).")

        # 3. TẠO LANDING PAGE CONFIG
        db.query(LandingPageConfig).delete()
        db.commit()
        landing_config = LandingPageConfig(
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
            updated_by="user-000"
        )
        db.add(landing_config)
        db.commit()
        print("✅ Đã khởi tạo cấu hình Landing Page CMS mẫu.")

        # 4. TẠO CA MẪU (SHIFT TEMPLATES) & CẤU HÌNH HỆ THỐNG (SYSTEM SETTINGS)
        templates = [
            ShiftTemplate(name="Ca Sáng (Mở Cửa & Nướng Bánh)", start_time="06:00", end_time="14:00", default_initial_cash=2000000, is_active=True),
            ShiftTemplate(name="Ca Chiều (Bán Hàng & Kết Ca)", start_time="14:00", end_time="22:00", default_initial_cash=1500000, is_active=True),
            ShiftTemplate(name="Ca Gãy / Tăng Cường", start_time="10:00", end_time="16:00", default_initial_cash=1000000, is_active=True),
        ]
        db.add_all(templates)

        sys_settings = [SystemSetting(key=k, value=str(v)) for k, v in DEFAULT_SETTINGS.items()]
        db.add_all(sys_settings)
        db.commit()
        print("✅ Đã nạp 3 ca làm việc mẫu và 12 tham số cấu hình hệ thống.")

        print("🎉 QUÁ TRÌNH SEED DỮ LIỆU HOÀN TẤT THÀNH CÔNG 100%!")

    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi khi seed dữ liệu: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
