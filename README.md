# Artisan Bakery - Backend Service (FastAPI + PostgreSQL)

Hệ thống Backend cung cấp toàn bộ RESTful API cho **Hệ thống Quản lý Đơn hàng Tiệm Bánh Nhỏ (Artisan Bakery)**, xây dựng trên nền tảng **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL 16** (Docker Compose), **Alembic**, **Pydantic v2** và **JWT / Bcrypt**.

---

## 1. Tech Stack

- **Framework:** FastAPI (Python 3.10+)
- **ORM:** SQLAlchemy 2.0 (cú pháp Declarative hiện đại `Mapped` / `mapped_column`)
- **Database:** PostgreSQL 16 Alpine (chạy qua Docker Compose)
- **Database Migration:** Alembic
- **Validation & Serialization:** Pydantic v2 (CamelCase alias tự động tương thích 100% với Next.js FE)
- **Security:** Bcrypt (hashing mật khẩu) + PyJWT / python-jose (JWT Access Token)
- **Dev Server:** Uvicorn

---

## 2. Cấu Trúc Thư Mục

```text
be/
├── docker-compose.yml       # Cấu hình container PostgreSQL 16
├── requirements.txt         # Danh sách thư viện Python
├── .env                     # Biến môi trường kết nối DB & JWT Secret
├── alembic.ini              # Cấu hình Alembic Migration
├── alembic/                 # Thư mục chứa migration scripts
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── seed.py                  # Script nạp dữ liệu mẫu ban đầu
├── test_api.py              # Bộ test tự động kiểm thử toàn bộ API
└── app/
    ├── main.py              # Entrypoint FastAPI, CORS middleware
    ├── database.py          # SQLAlchemy engine & session factory
    ├── dependencies.py      # Auth & RBAC dependencies (get_db, get_current_user, require_role)
    ├── core/
    │   ├── config.py        # Pydantic Settings
    │   └── security.py      # Bcrypt hash & JWT encoding/decoding
    ├── models/              # SQLAlchemy Models
    │   ├── user.py          # Bảng users
    │   ├── product.py       # Bảng products (soft-delete, dynamic status)
    │   └── order.py         # Bảng orders & order_items
    ├── schemas/             # Pydantic Schemas (CamelCase)
    │   ├── user.py
    │   ├── product.py
    │   ├── order.py
    │   └── dashboard.py
    └── routers/             # API Endpoints
        ├── auth.py          # /api/auth/login, /api/auth/me
        ├── products.py      # /api/products CRUD + bộ lọc
        ├── orders.py        # /api/orders (Transaction POS nguyên tử)
        ├── users.py         # /api/users (CRUD tài khoản)
        └── dashboard.py     # /api/dashboard/stats (KPIs, biểu đồ, Top 5)
```

---

## 3. Hướng Dẫn Cài Đặt & Khởi Chạy

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

### Bước 3: Chạy Database Migration (Alembic)
```bash
alembic upgrade head
```

### Bước 4: Nạp dữ liệu mẫu ban đầu (Seed Data)
```bash
python seed.py
```
> Dữ liệu nạp gồm: 4 tài khoản nhân viên (đã băm mật khẩu Bcrypt), 11 món bánh, 7 đơn hàng mẫu.

### Bước 5: Chạy Backend Dev Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Docs (Swagger UI): http://localhost:8000/docs
- API Redoc: http://localhost:8000/redoc

---

## 4. Chạy Bộ Kiểm Thử Tự Động (Integration Tests)

```bash
python test_api.py
```
Bộ test kiểm tra tự động các nghiệp vụ:
1. Xác thực đăng nhập Admin / Staff, lấy JWT token.
2. Kiểm tra phân quyền RBAC (Staff bị chặn khi thêm sản phẩm / xem user).
3. Thêm / sửa / xóa sản phẩm (soft-delete).
4. **Transaction bán hàng POS nguyên tử (`with_for_update`)**:
   - Trừ kho tự động khi tạo đơn.
   - Rollback toàn bộ khi số lượng mua vượt quá tồn kho hiện có.
5. Tạo tài khoản nhân viên mới và kiểm tra băm mật khẩu Bcrypt.
6. Tính toán số liệu Dashboard KPI, biểu đồ doanh thu theo giờ và Top 5 bán chạy.

---

## 5. Danh Sách Tài Khoản Mẫu

| Username | Password | Họ và tên | Vai trò (Role) | Quyền hạn |
| :--- | :--- | :--- | :--- | :--- |
| `admin` | `password123` | Nguyễn Quản Trị | **ADMIN** | Toàn quyền xem Dashboard, Quản lý bánh, Đơn hàng, Nhân viên |
| `staff` | `password123` | Trần Thị Thu Ngân | **STAFF** | Bán hàng POS, xem Lịch sử đơn hàng |
| `lethuha` | `password123` | Lê Thu Hà | **STAFF** | Bán hàng POS, xem Lịch sử đơn hàng |
| `phamminh` | `password123` | Phạm Minh Bếp Bánh | **STAFF** | Tài khoản tạm khóa |
