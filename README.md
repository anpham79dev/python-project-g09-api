# Artisan Bakery - Backend Service (FastAPI + PostgreSQL)

Hệ thống Backend cung cấp toàn diện RESTful API cho **Hệ thống Quản lý Đơn hàng & Vận hành Chuỗi Tiệm Bánh (Artisan Bakery Management System)**, xây dựng trên nền tảng **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL 16** (Docker Compose), **Alembic Migration**, **Pydantic v2**, phân quyền động **PBAC (Permission-Based Access Control)** và bảo mật **JWT / Bcrypt**.

---

## 1. Tech Stack & Kiến Trúc

- **Core Framework:** FastAPI (Python 3.10+)
- **ORM:** SQLAlchemy 2.0 (Declarative cú pháp `Mapped` / `mapped_column`, relationship linh hoạt)
- **Database:** PostgreSQL 16 Alpine (chạy qua Docker Compose)
- **Database Migration:** Alembic (Quản lý version schema DB)
- **Data Validation & Serialization:** Pydantic v2 (CamelCase alias tự động tương thích 100% với Next.js Frontend)
- **Security & Auth:** Bcrypt (hashing mật khẩu) + PyJWT / python-jose (JWT Access Token)
- **Phân quyền:** PBAC (Permission-Based Access Control) với 21 quyền hạn nguyên tử & Audit Log
- **Concurrency Control:** `with_for_update` (Pessimistic locking) đảm bảo giao dịch POS & kho nguyên tử (Atomicity)
- **Dev Server:** Uvicorn (ASGI)

---

## 2. Cấu Trúc Thư Mục Backend

```text
be/
├── docker-compose.yml       # Cấu hình container PostgreSQL 16
├── requirements.txt         # Danh sách thư viện Python
├── .env.example             # Biến môi trường mẫu
├── .env                     # Biến môi trường cục bộ (không commit)
├── .gitignore               # Cấu hình bỏ qua tệp nhạy cảm/môi trường ảo
├── alembic.ini              # Cấu hình Alembic Migration
├── alembic/                 # Thư mục chứa migration scripts
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 80ead1f52855_initial_schema.py
│       └── a1b2c3d4e5f6_add_pbac_tables.py
├── seed.py                  # Script nạp dữ liệu mẫu ban đầu (Roles, Users, Branches, Products, Orders,...)
├── test_api.py              # Bộ test tự động kiểm thử toàn bộ API
└── app/
    ├── main.py              # Entrypoint FastAPI, CORS middleware, Exception Handlers
    ├── database.py          # SQLAlchemy engine & session factory
    ├── dependencies.py      # Auth & PBAC dependencies (get_db, get_current_user, require_permission, require_role)
    ├── core/
    │   ├── config.py        # Pydantic Settings & Environment Loading
    │   ├── rbac_config.py   # Định nghĩa 21 Permissions chuẩn & Default Roles
    │   └── security.py      # Bcrypt hash & JWT encoding/decoding
    ├── models/              # SQLAlchemy ORM Models
    │   ├── audit_log.py     # Bảng audit_logs (Nhật ký phân quyền & thao tác)
    │   ├── branch.py        # Bảng branches & warehouses (Đa chi nhánh / Đa kho)
    │   ├── landing_config.py# Bảng landing_page_configs (CMS Trang chủ)
    │   ├── order.py         # Bảng orders & order_items (Đơn hàng POS & chi tiết)
    │   ├── permission.py    # Bảng permissions (21 quyền nguyên tử)
    │   ├── product.py       # Bảng products (Sản phẩm, danh mục, soft-delete)
    │   ├── role.py          # Bảng roles & role_permissions (Vai trò tùy biến)
    │   ├── setting.py       # Bảng system_settings & shift_templates (Cấu hình ca & hệ thống)
    │   ├── shift.py         # Bảng work_shifts (Quản lý ca làm việc, chênh lệch tiền mặt)
    │   ├── stock.py         # Bảng stock_items (Tồn kho theo chi nhánh/kho)
    │   ├── transaction.py   # Bảng transactions (Sổ quỹ thu / chi kế toán)
    │   └── user.py          # Bảng users (Tài khoản, liên kết role & chi nhánh)
    ├── schemas/             # Pydantic v2 Schemas (CamelCase serialization)
    │   ├── branch.py        # Schemas Chi nhánh & Kho
    │   ├── dashboard.py     # Schemas Thống kê & Biểu đồ Dashboard
    │   ├── landing_config.py# Schemas Cấu hình Landing Page
    │   ├── order.py         # Schemas Đơn hàng & POS Checkout
    │   ├── product.py       # Schemas Sản phẩm & Danh mục
    │   ├── role.py          # Schemas Roles & Permissions
    │   ├── setting.py       # Schemas Cài đặt hệ thống & Mẫu ca
    │   ├── shift.py         # Schemas Mở ca, Đóng ca, Kết ca
    │   ├── transaction.py   # Schemas Thu chi, Phiếu thu, Phiếu chi, Đối soát
    │   └── user.py          # Schemas Người dùng & Xác thực
    └── routers/             # API Endpoints
        ├── auth.py          # /api/auth (Login, Logout, /me profile & permissions)
        ├── accounting.py    # /api/accounting (Sổ quỹ, Phiếu thu/chi, Đối soát ngân hàng)
        ├── branches.py      # /api/branches (Quản lý Chi nhánh & Kho)
        ├── dashboard.py     # /api/dashboard/stats (KPIs doanh thu, biểu đồ, Top 5 bán chạy)
        ├── landing_config.py# /api/landing-config (CMS Nội dung Landing Page)
        ├── orders.py        # /api/orders (Tạo đơn POS nguyên tử, Tra cứu, Hóa đơn)
        ├── products.py      # /api/products (CRUD Bánh, Bộ lọc danh mục & trạng thái)
        ├── roles.py         # /api/roles (CRUD Vai trò, Gán quyền hạn, Audit logs)
        ├── settings.py      # /api/settings (Cấu hình hệ thống, Mẫu ca làm việc)
        ├── shifts.py        # /api/shifts (Mở ca, Theo dõi ca hiện tại, Kết ca đối soát)
        └── users.py         # /api/users (CRUD Nhân viên, Đổi trạng thái/chi nhánh)
```

---

## 3. Các Phân Hệ Chức Năng Chính

### 3.1. Xác thực & Phân quyền Động (Auth & PBAC)
- Đăng nhập JWT chuẩn Bearer token, băm mật khẩu Bcrypt an toàn.
- Hệ thống **21 Permissions nguyên tử** chia theo 9 module: `dashboard`, `products`, `orders`, `shifts`, `accounting`, `branches`, `users`, `roles`, `settings`.
- Phân quyền động: Có thể tạo vai trò tùy chỉnh (Custom Roles), bật/tắt quyền tức thì, ghi nhật ký phân quyền vào `audit_logs`.

### 3.2. Quản lý Đa Chi Nhánh & Kho (Multi-Branch)
- Quản lý danh sách chi nhánh (`branches`), kho trực thuộc (`warehouses`).
- Hỗ trợ lọc số liệu Dashboard, Đơn hàng, Sổ quỹ theo từng chi nhánh cụ thể hoặc toàn hệ thống.

### 3.3. Bán Hàng POS & Giao Dịch Kho Nguyên Tử
- Endpoint `/api/orders` xử lý transaction bán hàng với khóa bi quan (`with_for_update`).
- Tự động trừ kho tại chi nhánh tương ứng, đảm bảo không bị race-condition hoặc âm kho khi nhiều thu ngân thanh toán cùng lúc.
- Tự động tạo bản ghi thu tiền vào sổ quỹ kế toán khi đơn thanh toán thành công.

### 3.4. Quản lý Ca Làm Việc & Kết Ca (Shift Management)
- Quản lý mở ca, khai báo số dư đầu ca.
- Tự động thống kê doanh thu tiền mặt, chuyển khoản trong suốt ca làm việc.
- Đóng ca / Kết ca: Khai báo số tiền thực tế trong két, tự động tính chênh lệch thừa/thiếu và ghi nhận lý do giải trình.

### 3.5. Kế Toán & Sổ Quỹ Thu Chi (Accounting)
- Ghi nhận mọi dòng tiền vào/ra (Tiền bán hàng, Chi mua nguyên vật liệu, Chi trả tiền điện nước,...).
- Hỗ trợ lập Phiếu Thu / Phiếu Chi có chứng từ.
- Phân hệ Đối soát Ngân hàng: Đối chiếu giao dịch chuyển khoản với sao kê thực tế.

### 3.6. Cấu Hình Hệ Thống & CMS Landing Page
- Cấu hình thông tin thương hiệu, thuế VAT, thời gian ca làm việc linh hoạt.
- Quản lý nội dung công khai trên Landing Page (Hero banner, Bánh nổi bật, Câu chuyện thương hiệu, Lời chứng thực).

---

## 4. Hướng Dẫn Cài Đặt & Khởi Chạy

### Bước 1: Khởi động cơ sở dữ liệu PostgreSQL (Docker Compose)
```bash
cd be
docker compose up -d
```
> Container `artisan_bakery_postgres` sẽ chạy trên cổng `5432` với volume lưu trữ an toàn `be_postgres_data`.

### Bước 2: Tạo môi trường ảo và cài đặt thư viện
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Bước 3: Cấu hình biến môi trường
Tạo tệp `.env` từ `.env.example`:
```bash
cp .env.example .env
```

### Bước 4: Chạy Database Migration (Alembic)
```bash
alembic upgrade head
```

### Bước 5: Nạp dữ liệu mẫu ban đầu (Seed Data)
```bash
python seed.py
```
> Dữ liệu seed bao gồm: 21 Quyền, 3 Vai trò hệ thống, 2 Chi nhánh, 5 Tài khoản nhân viên, 11 Món bánh, 7 Đơn hàng mẫu, 12 Giao dịch thu/chi, Ca làm việc, và Cấu hình Landing Page.

### Bước 6: Khởi chạy Backend Dev Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **API Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 5. Danh Sách Tài Khoản Mẫu

Tất cả các tài khoản mặc định đều dùng chung mật khẩu: **`password123`**

| Username | Họ và tên | Vai trò (Role) | Chi nhánh | Quyền hạn nổi bật |
| :--- | :--- | :--- | :--- | :--- |
| `superadmin` | Tổng Quản Trị Hệ Thống | **SUPER_ADMIN** | Toàn hệ thống | Toàn bộ 21 quyền (quản lý phân quyền, cấu hình hệ thống) |
| `admin` | Nguyễn Quản Trị | **ADMIN** | CN Quận 1 | Quản lý Dashboard, Bánh, Đơn hàng, Nhân viên, Ca làm, Sổ quỹ |
| `staff` | Trần Thị Thu Ngân | **STAFF** | CN Quận 1 | Bán hàng POS, Mở/Đóng ca làm việc, Xem đơn hàng của mình |
| `lethuha` | Lê Thu Hà | **STAFF** | CN Thảo Điền | Thu ngân chi nhánh Thảo Điền |
| `phamminh` | Phạm Minh Bếp Bánh | **STAFF** | CN Quận 1 | Nhân viên bếp (Tài khoản thử nghiệm) |

---

## 6. Kiểm Thử Tự Động (Integration Tests)

Chạy bộ kiểm thử tự động toàn diện kiểm tra tất cả các endpoint:
```bash
python test_api.py
```

### Nội dung bộ test bao gồm:
1. **Auth & Profile:** Đăng nhập SuperAdmin / Admin / Staff, lấy JWT token và kiểm tra `GET /api/auth/me` cùng mảng permissions.
2. **PBAC Authorization:** Kiểm tra chặn truy cập khi nhân viên thiếu quyền (403 Forbidden).
3. **Products CRUD:** Thêm mới, chỉnh sửa, lọc danh mục và xóa mềm sản phẩm.
4. **POS Atomic Transaction:** Kiểm tra giao dịch tạo đơn hàng đồng thời trừ tồn kho, kiểm tra rollback khi số lượng mua vượt tồn kho.
5. **Shifts & Cash Reconciliation:** Mở ca, tạo doanh thu, kết ca và tính toán chênh lệch tiền mặt.
6. **Accounting & Cash Book:** Lập phiếu thu/chi, kiểm tra số dư quỹ, lọc giao dịch theo chi nhánh.
7. **Branch Filtering & Dashboard KPIs:** Kiểm tra số liệu thống kê Dashboard theo chi nhánh và toàn hệ thống.
