-- =============================================================================
-- HE THONG QUAN LY DON HANG & VAN HANH CHUOI TIEM BANH (ARTISAN BAKERY)
-- TAP LENH POSTGRESQL DDL TAO CAU TRUC CO SO DU LIEU (DATABASE SCHEMA)
-- =============================================================================
-- Nguon goc ma nguon:
--   - Backend: FastAPI (Python 3.10+)
--   - ORM: SQLAlchemy 2.0 (Declarative Base, Mapped, mapped_column)
--   - Migrations: alembic/versions/ (80ead1f52855, a1b2c3d4e5f6)
--   - Models: app/models/ (12 file model, tong cong 16 bang)
-- Quy tac thiet ke:
--   1. Cu phap thuan PostgreSQL 16.
--   2. Toan bo Foreign Keys duoc tao qua ALTER TABLE de khong phu thuoc thu tu CREATE TABLE.
--   3. COMMENT ON TABLE va COMMENT ON COLUMN chi dua tren ma nguon hien huu.
--   4. Cac cho khong chac chan ve kieu, do dai, rang buoc deu duoc chu thich bang
--      comment "-- KHONG CHAC: ly do".
--   5. Cuoi file co danh sach tong hop cac diem can kiem tra de bao cao Truong nhom.
-- =============================================================================


-- =============================================================================
-- PHAN 1: TAO BANG (CREATE TABLE)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. BANG permissions: Danh muc quyen nguyen tu (PBAC)
-- -----------------------------------------------------------------------------
CREATE TABLE permissions (
    id VARCHAR(50) NOT NULL,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(150) NOT NULL,
    module VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_permissions PRIMARY KEY (id)
);

-- -----------------------------------------------------------------------------
-- 2. BANG roles: Vai tro nguoi dung trong he thong PBAC
-- -----------------------------------------------------------------------------
CREATE TABLE roles (
    id VARCHAR(50) NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    permissions_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_roles PRIMARY KEY (id)
);

-- -----------------------------------------------------------------------------
-- 3. BANG role_permissions: Bang trung gian Many-to-Many giua roles va permissions
-- -----------------------------------------------------------------------------
CREATE TABLE role_permissions (
    role_id VARCHAR(50) NOT NULL,
    permission_id VARCHAR(50) NOT NULL,
    CONSTRAINT pk_role_permissions PRIMARY KEY (role_id, permission_id)
);

-- -----------------------------------------------------------------------------
-- 4. BANG branches: Danh sach chi nhanh cua hang
-- -----------------------------------------------------------------------------
CREATE TABLE branches (
    -- KHONG CHAC: Model dung sa.String khong khai bao do dai (trong PostgreSQL tuong duong VARCHAR khong gioi han hoac TEXT). Seed/ID co dang branch-xxxxxx (10-12 ky tu), suy doan dong nhat VARCHAR(50) nhu cac bang khac.
    id VARCHAR(50) NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(150) NOT NULL,
    address VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    manager_name VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    -- KHONG CHAC: Model khai bao sa.DateTime (khong co timezone=True), PostgreSQL mac dinh tao TIMESTAMP WITHOUT TIME ZONE, khac voi TIMESTAMP WITH TIME ZONE o cac bang co migration.
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_branches PRIMARY KEY (id)
);

-- -----------------------------------------------------------------------------
-- 5. BANG warehouses: Danh sach kho hang truc thuoc chi nhanh
-- -----------------------------------------------------------------------------
CREATE TABLE warehouses (
    -- KHONG CHAC: Model dung sa.String khong khai bao do dai. Dinh dang id trong seed la wh-xxxxxx, suy doan VARCHAR(50).
    id VARCHAR(50) NOT NULL,
    -- KHONG CHAC: Model dung sa.String tham chieu branches.id, suy doan VARCHAR(50) de khop branches.id.
    branch_id VARCHAR(50) NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(150) NOT NULL,
    warehouse_type VARCHAR(50) NOT NULL DEFAULT 'RETAIL',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    -- KHONG CHAC: Model khai bao sa.DateTime (khong co timezone=True).
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_warehouses PRIMARY KEY (id)
);

-- -----------------------------------------------------------------------------
-- 6. BANG users: Tai khoan nguoi dung va nhan vien
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id VARCHAR(50) NOT NULL,
    username VARCHAR(50) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    role_id VARCHAR(50),
    -- KHONG CHAC: Migration 80ead1f52855 khai bao role la String(20), nhung model hien tai la String(50). DDL chon VARCHAR(50) theo model.
    role VARCHAR(50) NOT NULL DEFAULT 'STAFF',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    -- KHONG CHAC: default_branch_id va last_active_branch_id co trong model User nhung KHONG co trong cac file migration Alembic, va khong khai bao ForeignKey('branches.id') trong code model.
    default_branch_id VARCHAR(50),
    last_active_branch_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_users PRIMARY KEY (id),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT uq_users_username UNIQUE (username)
);

-- -----------------------------------------------------------------------------
-- 7. BANG products: Danh muc san pham banh va do uong
-- -----------------------------------------------------------------------------
CREATE TABLE products (
    id VARCHAR(50) NOT NULL,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    price INTEGER NOT NULL,
    -- KHONG CHAC: Migration 80ead1f52855 khong co default=0 va khong tao index cho stock, nhung model Product khai bao default=0 va index=True.
    stock INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    image VARCHAR(500) NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    -- KHONG CHAC: Migration khong tao index cho created_at, model khai bao index=True.
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_products PRIMARY KEY (id)
);

-- -----------------------------------------------------------------------------
-- 8. BANG orders: Don hang ban le tai quay (POS)
-- -----------------------------------------------------------------------------
CREATE TABLE orders (
    id VARCHAR(50) NOT NULL,
    code VARCHAR(50) NOT NULL,
    customer_name VARCHAR(100) DEFAULT 'Khách vãng lai',
    customer_phone VARCHAR(20),
    -- KHONG CHAC: branch_id va warehouse_id co trong model Order nhung KHONG co trong migration 80ead1f52855, va khong khai bao ForeignKey constraint trong code model.
    branch_id VARCHAR(50),
    warehouse_id VARCHAR(50),
    staff_id VARCHAR(50) NOT NULL,
    staff_name VARCHAR(100) NOT NULL,
    subtotal INTEGER NOT NULL,
    discount INTEGER NOT NULL DEFAULT 0,
    total_amount INTEGER NOT NULL,
    payment_method VARCHAR(30) NOT NULL DEFAULT 'QR_TRANSFER',
    status VARCHAR(30) NOT NULL DEFAULT 'COMPLETED',
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_orders PRIMARY KEY (id),
    CONSTRAINT uq_orders_code UNIQUE (code)
);

-- -----------------------------------------------------------------------------
-- 9. BANG order_items: Chi tiet san pham tung don hang
-- -----------------------------------------------------------------------------
CREATE TABLE order_items (
    id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    price INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    subtotal INTEGER NOT NULL,
    image VARCHAR(500),
    CONSTRAINT pk_order_items PRIMARY KEY (id)
);

-- -----------------------------------------------------------------------------
-- 10. BANG stock_items: Ton kho san pham theo tung kho
-- -----------------------------------------------------------------------------
CREATE TABLE stock_items (
    -- KHONG CHAC: Model dung sa.String khong khai bao do dai. Seed/default tao dang stk-xxxxxxxx, suy doan VARCHAR(50).
    id VARCHAR(50) NOT NULL,
    -- KHONG CHAC: Model dung sa.String khong khai bao do dai, suy doan VARCHAR(50) de khop warehouses.id.
    warehouse_id VARCHAR(50) NOT NULL,
    -- KHONG CHAC: Model dung sa.String khong khai bao do dai, suy doan VARCHAR(50) de khop products.id.
    product_id VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    min_alert_stock INTEGER NOT NULL DEFAULT 5,
    -- KHONG CHAC: Model dung sa.DateTime (khong co timezone=True).
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_stock_items PRIMARY KEY (id),
    CONSTRAINT uq_warehouse_product_stock UNIQUE (warehouse_id, product_id)
);

-- -----------------------------------------------------------------------------
-- 11. BANG transactions: So quy thu chi ke toan (Phieu thu / Phieu chi)
-- -----------------------------------------------------------------------------
CREATE TABLE transactions (
    id VARCHAR(50) NOT NULL,
    code VARCHAR(50) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    category VARCHAR(100) NOT NULL,
    amount INTEGER NOT NULL,
    -- KHONG CHAC: branch_id mang y nghia tham chieu branches(id) nhung trong model khong khai bao ForeignKey constraint.
    branch_id VARCHAR(50),
    payment_method VARCHAR(30) NOT NULL DEFAULT 'CASH',
    recipient_payer VARCHAR(150) NOT NULL,
    note TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_transactions PRIMARY KEY (id),
    CONSTRAINT uq_transactions_code UNIQUE (code)
);

-- -----------------------------------------------------------------------------
-- 12. BANG shift_templates: Mau ca lam viec tieu chuan
-- -----------------------------------------------------------------------------
CREATE TABLE shift_templates (
    -- KHONG CHAC: Model dung sa.String khong khai bao do dai. Dinh dang id la tmpl-xxxxxx, suy doan VARCHAR(50).
    id VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    -- KHONG CHAC: Model luu start_time va end_time duoi dang chuoi String(10) (vi du "06:30", "14:30") thay vi kieu TIME cua PostgreSQL.
    start_time VARCHAR(10) NOT NULL,
    end_time VARCHAR(10) NOT NULL,
    default_initial_cash INTEGER NOT NULL DEFAULT 500000,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    note TEXT,
    -- KHONG CHAC: Model dung sa.DateTime (khong co timezone=True).
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_shift_templates PRIMARY KEY (id)
);

-- -----------------------------------------------------------------------------
-- 13. BANG work_shifts: Phien ca lam viec thuc te va doi soat ket tien
-- -----------------------------------------------------------------------------
CREATE TABLE work_shifts (
    -- KHONG CHAC: Model dung sa.String khong khai bao do dai. Dinh dang id la shift-xxxxxxxx, suy doan VARCHAR(50).
    id VARCHAR(50) NOT NULL,
    -- KHONG CHAC: branch_id tham chieu logic branches(id) nhung khong khai bao ForeignKey constraint trong model.
    branch_id VARCHAR(50),
    -- KHONG CHAC: template_id tham chieu logic shift_templates(id) nhung khong khai bao ForeignKey constraint trong model.
    template_id VARCHAR(50),
    shift_name VARCHAR(100) NOT NULL DEFAULT 'Ca làm việc tiêu chuẩn',
    -- KHONG CHAC: Model dung sa.String khong khai bao do dai, suy doan VARCHAR(50) de khop users.id.
    staff_id VARCHAR(50) NOT NULL,
    staff_name VARCHAR(100) NOT NULL,
    -- KHONG CHAC: Model dung sa.DateTime (khong co timezone=True).
    start_time TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITHOUT TIME ZONE,
    initial_cash INTEGER NOT NULL DEFAULT 500000,
    cash_revenue INTEGER NOT NULL DEFAULT 0,
    card_revenue INTEGER NOT NULL DEFAULT 0,
    qr_revenue INTEGER NOT NULL DEFAULT 0,
    total_revenue INTEGER NOT NULL DEFAULT 0,
    orders_count INTEGER NOT NULL DEFAULT 0,
    expected_cash INTEGER NOT NULL DEFAULT 500000,
    actual_cash INTEGER NOT NULL DEFAULT 0,
    difference INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    note TEXT,
    -- KHONG CHAC: Model dung sa.DateTime (khong co timezone=True).
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_work_shifts PRIMARY KEY (id)
);

-- -----------------------------------------------------------------------------
-- 14. BANG system_settings: Cau hinh dong van hanh he thong (Key-Value)
-- -----------------------------------------------------------------------------
CREATE TABLE system_settings (
    key VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    description VARCHAR(255),
    -- KHONG CHAC: Model dung sa.DateTime (khong co timezone=True).
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_system_settings PRIMARY KEY (key)
);

-- -----------------------------------------------------------------------------
-- 15. BANG landing_page_config: Cau hinh noi dung CMS Landing Page
-- -----------------------------------------------------------------------------
CREATE TABLE landing_page_config (
    id VARCHAR(50) NOT NULL DEFAULT 'landing-config-current',
    version INTEGER NOT NULL DEFAULT 1,
    is_published BOOLEAN NOT NULL DEFAULT TRUE,
    -- KHONG CHAC: Model khai bao sa.JSON (PostgreSQL luu JSON). Trong PostgreSQL thuong uu tien JSONB de toi uu truy van/index.
    brand JSON NOT NULL,
    nav JSON NOT NULL,
    hero JSON NOT NULL,
    features JSON NOT NULL,
    solutions JSON NOT NULL,
    pricing_plans JSON NOT NULL,
    testimonials JSON NOT NULL,
    faqs JSON NOT NULL,
    footer JSON NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- KHONG CHAC: updated_by mang y nghia tham chieu users.id nhung khong co ForeignKey constraint trong model.
    updated_by VARCHAR(50),
    CONSTRAINT pk_landing_page_config PRIMARY KEY (id)
);

-- -----------------------------------------------------------------------------
-- 16. BANG audit_logs: Nhat ky kiem toan phan quyen va thao tac he thong
-- -----------------------------------------------------------------------------
CREATE TABLE audit_logs (
    id VARCHAR(50) NOT NULL,
    -- KHONG CHAC: user_id mang y nghia tham chieu users.id nhung khong khai bao ForeignKey constraint ca trong model lan migration a1b2c3d4e5f6.
    user_id VARCHAR(50) NOT NULL,
    user_name VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NOT NULL DEFAULT 'ROLE',
    target_id VARCHAR(50) NOT NULL,
    target_name VARCHAR(100) NOT NULL,
    changes_summary TEXT NOT NULL,
    details_json TEXT,
    ip_address VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_audit_logs PRIMARY KEY (id)
);


-- =============================================================================
-- PHAN 2: TAO CHI MUC (INDEXES)
-- =============================================================================

-- Indexes tren permissions
CREATE INDEX ix_permissions_id ON permissions (id);
CREATE UNIQUE INDEX ix_permissions_code ON permissions (code);
CREATE INDEX ix_permissions_module ON permissions (module);

-- Indexes tren roles
CREATE INDEX ix_roles_id ON roles (id);
CREATE UNIQUE INDEX ix_roles_code ON roles (code);

-- Indexes tren branches
CREATE UNIQUE INDEX ix_branches_code ON branches (code);
CREATE INDEX ix_branches_name ON branches (name);

-- Indexes tren warehouses
CREATE INDEX ix_warehouses_branch_id ON warehouses (branch_id);
CREATE UNIQUE INDEX ix_warehouses_code ON warehouses (code);

-- Indexes tren users
CREATE INDEX ix_users_id ON users (id);
CREATE UNIQUE INDEX ix_users_username ON users (username);
CREATE INDEX ix_users_role_id ON users (role_id);
CREATE INDEX ix_users_role ON users (role);
CREATE INDEX ix_users_status ON users (status);
CREATE INDEX ix_users_default_branch_id ON users (default_branch_id);

-- Indexes tren products
CREATE INDEX ix_products_id ON products (id);
CREATE INDEX ix_products_name ON products (name);
CREATE INDEX ix_products_category ON products (category);
CREATE INDEX ix_products_is_deleted ON products (is_deleted);
CREATE INDEX ix_products_stock ON products (stock);
CREATE INDEX ix_products_created_at ON products (created_at);

-- Indexes tren orders
CREATE INDEX ix_orders_id ON orders (id);
CREATE UNIQUE INDEX ix_orders_code ON orders (code);
CREATE INDEX ix_orders_staff_id ON orders (staff_id);
CREATE INDEX ix_orders_branch_id ON orders (branch_id);
CREATE INDEX ix_orders_warehouse_id ON orders (warehouse_id);
CREATE INDEX ix_orders_created_at ON orders (created_at);

-- Indexes tren order_items
CREATE INDEX ix_order_items_order_id ON order_items (order_id);
CREATE INDEX ix_order_items_product_id ON order_items (product_id);

-- Indexes tren stock_items
CREATE INDEX ix_stock_items_warehouse_id ON stock_items (warehouse_id);
CREATE INDEX ix_stock_items_product_id ON stock_items (product_id);

-- Indexes tren transactions
CREATE INDEX ix_transactions_id ON transactions (id);
CREATE UNIQUE INDEX ix_transactions_code ON transactions (code);
CREATE INDEX ix_transactions_category ON transactions (category);
CREATE INDEX ix_transactions_branch_id ON transactions (branch_id);
CREATE INDEX ix_transactions_created_at ON transactions (created_at);

-- Indexes tren shift_templates
CREATE INDEX ix_shift_templates_name ON shift_templates (name);

-- Indexes tren work_shifts
CREATE INDEX ix_work_shifts_branch_id ON work_shifts (branch_id);
CREATE INDEX ix_work_shifts_staff_id ON work_shifts (staff_id);
CREATE INDEX ix_work_shifts_start_time ON work_shifts (start_time);
CREATE INDEX ix_work_shifts_status ON work_shifts (status);
CREATE INDEX ix_work_shifts_created_at ON work_shifts (created_at);

-- Indexes tren landing_page_config
CREATE INDEX ix_landing_page_config_id ON landing_page_config (id);

-- Indexes tren audit_logs
CREATE INDEX ix_audit_logs_id ON audit_logs (id);
CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_target_id ON audit_logs (target_id);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);


-- =============================================================================
-- PHAN 3: RANG BUOC KHOA NGOAI (FOREIGN KEY CONSTRAINTS)
-- =============================================================================

-- 1. role_permissions -> roles(id)
ALTER TABLE role_permissions
    ADD CONSTRAINT fk_role_permissions_role_id
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE;

-- 2. role_permissions -> permissions(id)
ALTER TABLE role_permissions
    ADD CONSTRAINT fk_role_permissions_permission_id
    FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE;

-- 3. users -> roles(id)
ALTER TABLE users
    ADD CONSTRAINT fk_users_role_id
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE SET NULL;

-- 4. warehouses -> branches(id)
ALTER TABLE warehouses
    ADD CONSTRAINT fk_warehouses_branch_id
    FOREIGN KEY (branch_id) REFERENCES branches (id);

-- 5. orders -> users(id)
ALTER TABLE orders
    ADD CONSTRAINT fk_orders_staff_id
    FOREIGN KEY (staff_id) REFERENCES users (id);

-- 6. order_items -> orders(id)
ALTER TABLE order_items
    ADD CONSTRAINT fk_order_items_order_id
    FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE;

-- 7. order_items -> products(id)
ALTER TABLE order_items
    ADD CONSTRAINT fk_order_items_product_id
    FOREIGN KEY (product_id) REFERENCES products (id);

-- 8. stock_items -> warehouses(id)
ALTER TABLE stock_items
    ADD CONSTRAINT fk_stock_items_warehouse_id
    FOREIGN KEY (warehouse_id) REFERENCES warehouses (id);

-- 9. stock_items -> products(id)
ALTER TABLE stock_items
    ADD CONSTRAINT fk_stock_items_product_id
    FOREIGN KEY (product_id) REFERENCES products (id);

-- 10. work_shifts -> users(id)
ALTER TABLE work_shifts
    ADD CONSTRAINT fk_work_shifts_staff_id
    FOREIGN KEY (staff_id) REFERENCES users (id);


-- =============================================================================
-- PHAN 4: CHU THICH NGHIEP VU (COMMENTS ON TABLES & COLUMNS)
-- =============================================================================

-- Bang permissions
COMMENT ON TABLE permissions IS 'Danh mục quyền nguyên tử (Atomic Permissions) trong hệ thống phân quyền PBAC';
COMMENT ON COLUMN permissions.id IS 'Mã định danh quyền hạn (dạng perm-xxx)';
COMMENT ON COLUMN permissions.code IS 'Mã quyền hạn duy nhất (vd: dashboard:view, products:write)';
COMMENT ON COLUMN permissions.name IS 'Tên hiển thị chi tiết của quyền hạn';
COMMENT ON COLUMN permissions.module IS 'Phân hệ chức năng áp dụng quyền (vd: Tổng Quan, POS, Sản Phẩm, Kho Hàng)';
COMMENT ON COLUMN permissions.description IS 'Mô tả mục đích và phạm vi thao tác của quyền';
COMMENT ON COLUMN permissions.created_at IS 'Thời điểm tạo quyền hạn trong hệ thống';

-- Bang roles
COMMENT ON TABLE roles IS 'Danh mục vai trò người dùng (Roles) hỗ trợ phân quyền động PBAC';
COMMENT ON COLUMN roles.id IS 'Mã định danh vai trò (dạng role-xxx)';
COMMENT ON COLUMN roles.code IS 'Mã vai trò duy nhất (vd: SUPER_ADMIN, ADMIN, STAFF)';
COMMENT ON COLUMN roles.name IS 'Tên hiển thị vai trò';
COMMENT ON COLUMN roles.description IS 'Mô tả quyền hạn của vai trò';
COMMENT ON COLUMN roles.is_system IS 'Cờ đánh dấu vai trò mặc định của hệ thống (không cho phép xóa)';
COMMENT ON COLUMN roles.permissions_version IS 'Phiên bản quyền của vai trò, tự động tăng khi cập nhật quyền để vô hiệu hóa token cũ';
COMMENT ON COLUMN roles.created_at IS 'Thời điểm tạo vai trò';
COMMENT ON COLUMN roles.updated_at IS 'Thời điểm cập nhật vai trò gần nhất';

-- Bang role_permissions
COMMENT ON TABLE role_permissions IS 'Bảng liên kết nhiều-nhiều giữa vai trò (roles) và quyền hạn (permissions)';
COMMENT ON COLUMN role_permissions.role_id IS 'Khóa ngoại tham chiếu đến roles(id)';
COMMENT ON COLUMN role_permissions.permission_id IS 'Khóa ngoại tham chiếu đến permissions(id)';

-- Bang branches
COMMENT ON TABLE branches IS 'Danh sách các chi nhánh cửa hàng bánh trong toàn chuỗi';
COMMENT ON COLUMN branches.id IS 'Mã định danh chi nhánh (dạng branch-xxx)';
COMMENT ON COLUMN branches.code IS 'Mã chi nhánh duy nhất (vd: CN-Q1, CN-TD)';
COMMENT ON COLUMN branches.name IS 'Tên chi nhánh cửa hàng';
COMMENT ON COLUMN branches.address IS 'Địa chỉ chi nhánh';
COMMENT ON COLUMN branches.phone IS 'Số điện thoại liên hệ chi nhánh';
COMMENT ON COLUMN branches.manager_name IS 'Họ tên quản lý chi nhánh';
COMMENT ON COLUMN branches.status IS 'Trạng thái hoạt động chi nhánh (ACTIVE, INACTIVE)';
COMMENT ON COLUMN branches.created_at IS 'Thời điểm tạo chi nhánh';

-- Bang warehouses
COMMENT ON TABLE warehouses IS 'Danh sách các kho hàng trực thuộc chi nhánh (Kho bán lẻ, kho lạnh, kho trung tâm)';
COMMENT ON COLUMN warehouses.id IS 'Mã định danh kho hàng (dạng wh-xxx)';
COMMENT ON COLUMN warehouses.branch_id IS 'Khóa ngoại tham chiếu đến chi nhánh sở hữu branches(id)';
COMMENT ON COLUMN warehouses.code IS 'Mã kho hàng duy nhất (vd: KHO-Q1-POS, KHO-Q1-COLD)';
COMMENT ON COLUMN warehouses.name IS 'Tên kho hàng';
COMMENT ON COLUMN warehouses.warehouse_type IS 'Phân loại kho (RETAIL, COLD_STORAGE, CENTRAL)';
COMMENT ON COLUMN warehouses.status IS 'Trạng thái kho hàng (ACTIVE, INACTIVE)';
COMMENT ON COLUMN warehouses.created_at IS 'Thời điểm tạo kho';

-- Bang users
COMMENT ON TABLE users IS 'Bảng quản lý tài khoản người dùng và nhân viên trong hệ thống';
COMMENT ON COLUMN users.id IS 'Mã định danh người dùng (dạng user-xxx)';
COMMENT ON COLUMN users.username IS 'Tên đăng nhập duy nhất';
COMMENT ON COLUMN users.hashed_password IS 'Mật khẩu đã băm bằng thuật toán Bcrypt';
COMMENT ON COLUMN users.full_name IS 'Họ và tên người dùng';
COMMENT ON COLUMN users.email IS 'Địa chỉ email duy nhất của người dùng';
COMMENT ON COLUMN users.phone IS 'Số điện thoại liên lạc';
COMMENT ON COLUMN users.role_id IS 'Khóa ngoại liên kết tới vai trò PBAC roles(id)';
COMMENT ON COLUMN users.role IS 'Mã vai trò kế thừa (legacy fallback, vd: SUPER_ADMIN, ADMIN, STAFF)';
COMMENT ON COLUMN users.status IS 'Trạng thái tài khoản (ACTIVE, INACTIVE)';
COMMENT ON COLUMN users.default_branch_id IS 'Chi nhánh mặc định làm việc của nhân viên (tham chiếu logic branches.id)';
COMMENT ON COLUMN users.last_active_branch_id IS 'Chi nhánh được chọn làm việc gần nhất trong phiên làm việc';
COMMENT ON COLUMN users.created_at IS 'Thời điểm tạo tài khoản';
COMMENT ON COLUMN users.updated_at IS 'Thời điểm cập nhật tài khoản gần nhất';

-- Bang products
COMMENT ON TABLE products IS 'Bảng danh mục các loại bánh và đồ uống của tiệm bánh';
COMMENT ON COLUMN products.id IS 'Mã định danh sản phẩm (dạng prod-xxx)';
COMMENT ON COLUMN products.name IS 'Tên sản phẩm bánh';
COMMENT ON COLUMN products.category IS 'Danh mục sản phẩm (vd: Bánh Mì Ngọt & Pastry, Bánh Kem & Sinh Nhật, Cà Phê & Đồ Uống)';
COMMENT ON COLUMN products.price IS 'Đơn giá bán sản phẩm tính bằng VND';
COMMENT ON COLUMN products.stock IS 'Số lượng tồn kho hiển thị (phục vụ tính trạng thái out_of_stock, low_stock, in_stock)';
COMMENT ON COLUMN products.description IS 'Mô tả chi tiết nguyên liệu và hương vị bánh';
COMMENT ON COLUMN products.image IS 'Đường dẫn URL ảnh sản phẩm';
COMMENT ON COLUMN products.is_deleted IS 'Cờ xóa mềm (soft-delete), true nghĩa là đã ngừng kinh doanh';
COMMENT ON COLUMN products.created_at IS 'Thời điểm tạo sản phẩm';
COMMENT ON COLUMN products.updated_at IS 'Thời điểm cập nhật sản phẩm gần nhất';

-- Bang orders
COMMENT ON TABLE orders IS 'Bảng quản lý đơn hàng bán lẻ tại quầy thu ngân (POS)';
COMMENT ON COLUMN orders.code IS 'Mã hóa đơn bán hàng duy nhất (vd: HD-260816-01)';
COMMENT ON COLUMN orders.customer_name IS 'Tên khách mua hàng (mặc định Khách vãng lai)';
COMMENT ON COLUMN orders.customer_phone IS 'Số điện thoại khách hàng';
COMMENT ON COLUMN orders.branch_id IS 'Mã chi nhánh thực hiện đơn hàng (tham chiếu logic branches.id)';
COMMENT ON COLUMN orders.warehouse_id IS 'Mã kho xuất hàng bán (tham chiếu logic warehouses.id)';
COMMENT ON COLUMN orders.staff_id IS 'Khóa ngoại tham chiếu nhân viên thu ngân lập đơn users(id)';
COMMENT ON COLUMN orders.staff_name IS 'Họ tên nhân viên thu ngân tại thời điểm bán hàng';
COMMENT ON COLUMN orders.subtotal IS 'Tổng tiền hàng trước chiết khấu giảm giá (VND)';
COMMENT ON COLUMN orders.discount IS 'Số tiền chiết khấu giảm giá đơn hàng (VND)';
COMMENT ON COLUMN orders.total_amount IS 'Tổng số tiền thực tế khách phải thanh toán (VND)';
COMMENT ON COLUMN orders.payment_method IS 'Phương thức thanh toán (CASH, QR_TRANSFER, CARD)';
COMMENT ON COLUMN orders.status IS 'Trạng thái đơn hàng (COMPLETED, PENDING, CANCELLED)';
COMMENT ON COLUMN orders.note IS 'Ghi chú đơn hàng (yêu cầu riêng của khách)';
COMMENT ON COLUMN orders.created_at IS 'Thời điểm tạo đơn hàng';
COMMENT ON COLUMN orders.updated_at IS 'Thời điểm cập nhật đơn hàng gần nhất';

-- Bang order_items
COMMENT ON TABLE order_items IS 'Chi tiết các mặt hàng và số lượng trong từng đơn hàng bán lẻ';
COMMENT ON COLUMN order_items.id IS 'Mã định danh dòng chi tiết đơn hàng (dạng item-xxx)';
COMMENT ON COLUMN order_items.order_id IS 'Khóa ngoại tham chiếu đến đơn hàng orders(id)';
COMMENT ON COLUMN order_items.product_id IS 'Khóa ngoại tham chiếu đến sản phẩm products(id)';
COMMENT ON COLUMN order_items.product_name IS 'Tên sản phẩm tại thời điểm lập đơn';
COMMENT ON COLUMN order_items.price IS 'Đơn giá bán tại thời điểm lập đơn (VND)';
COMMENT ON COLUMN order_items.quantity IS 'Số lượng sản phẩm đặt mua';
COMMENT ON COLUMN order_items.subtotal IS 'Thành tiền của dòng sản phẩm = price * quantity (VND)';
COMMENT ON COLUMN order_items.image IS 'Ảnh sản phẩm lưu kèm tại thời điểm bán';

-- Bang stock_items
COMMENT ON TABLE stock_items IS 'Quản lý số lượng tồn kho thực tế của từng sản phẩm theo từng kho';
COMMENT ON COLUMN stock_items.id IS 'Mã định danh bản ghi tồn kho (dạng stk-xxx)';
COMMENT ON COLUMN stock_items.warehouse_id IS 'Khóa ngoại tham chiếu đến kho hàng warehouses(id)';
COMMENT ON COLUMN stock_items.product_id IS 'Khóa ngoại tham chiếu đến sản phẩm products(id)';
COMMENT ON COLUMN stock_items.quantity IS 'Số lượng sản phẩm thực tế còn trong kho';
COMMENT ON COLUMN stock_items.min_alert_stock IS 'Định mức tồn tối thiểu để kích hoạt cảnh báo sắp hết hàng (mặc định 5)';
COMMENT ON COLUMN stock_items.created_at IS 'Thời điểm tạo bản ghi tồn kho';
COMMENT ON COLUMN stock_items.updated_at IS 'Thời điểm cập nhật tồn kho gần nhất';

-- Bang transactions
COMMENT ON TABLE transactions IS 'Bảng sổ quỹ thu chi kế toán và nhật ký dòng tiền (Phiếu thu / Phiếu chi)';
COMMENT ON COLUMN transactions.id IS 'Mã định danh giao dịch sổ quỹ (dạng tx-xxx)';
COMMENT ON COLUMN transactions.code IS 'Mã phiếu thu/chi duy nhất (vd: PT-260816-001, PC-260816-001)';
COMMENT ON COLUMN transactions.transaction_type IS 'Phân loại giao dịch (INCOME - Thu tiền, EXPENSE - Chi tiền)';
COMMENT ON COLUMN transactions.category IS 'Hạng mục thu/chi (vd: Thu doanh thu bán lẻ POS, Chi mua nguyên vật liệu, RENTAL, UTILITIES, SALARY, MARKETING, OTHER)';
COMMENT ON COLUMN transactions.amount IS 'Số tiền phát sinh giao dịch (VND)';
COMMENT ON COLUMN transactions.branch_id IS 'Chi nhánh phát sinh dòng tiền (tham chiếu logic branches.id)';
COMMENT ON COLUMN transactions.payment_method IS 'Hình thức thanh toán (CASH, BANK_TRANSFER)';
COMMENT ON COLUMN transactions.recipient_payer IS 'Họ tên đối tác/khách hàng nộp hoặc nhận tiền';
COMMENT ON COLUMN transactions.note IS 'Ghi chú giải trình lý do thu/chi';
COMMENT ON COLUMN transactions.created_by IS 'Tên người lập phiếu hoặc nguồn hệ thống tự động sinh';
COMMENT ON COLUMN transactions.created_at IS 'Thời điểm ghi sổ giao dịch';

-- Bang shift_templates
COMMENT ON TABLE shift_templates IS 'Bảng cấu hình các ca làm việc mẫu định kỳ';
COMMENT ON COLUMN shift_templates.id IS 'Mã mẫu ca làm việc (dạng tmpl-xxx)';
COMMENT ON COLUMN shift_templates.name IS 'Tên gọi ca mẫu (vd: Ca Sáng Tiêu Chuẩn, Ca Chiều)';
COMMENT ON COLUMN shift_templates.start_time IS 'Thời gian bắt đầu ca dạng chuỗi HH:MM (vd: 06:30)';
COMMENT ON COLUMN shift_templates.end_time IS 'Thời gian kết thúc ca dạng chuỗi HH:MM (vd: 14:30)';
COMMENT ON COLUMN shift_templates.default_initial_cash IS 'Số tiền mặt định mức bàn giao đầu ca (VND, mặc định 500000)';
COMMENT ON COLUMN shift_templates.is_active IS 'Trạng thái cho phép áp dụng mẫu ca';
COMMENT ON COLUMN shift_templates.note IS 'Ghi chú cấu hình ca';
COMMENT ON COLUMN shift_templates.created_at IS 'Thời điểm tạo mẫu ca';

-- Bang work_shifts
COMMENT ON TABLE work_shifts IS 'Bảng theo dõi ca làm việc thực tế của nhân viên thu ngân và đối soát két tiền mặt';
COMMENT ON COLUMN work_shifts.id IS 'Mã định danh ca làm việc (dạng shift-xxx)';
COMMENT ON COLUMN work_shifts.branch_id IS 'Chi nhánh diễn ra ca làm việc (tham chiếu logic branches.id)';
COMMENT ON COLUMN work_shifts.template_id IS 'Mã mẫu ca áp dụng nếu có (tham chiếu logic shift_templates.id)';
COMMENT ON COLUMN work_shifts.shift_name IS 'Tên ca làm việc thực tế';
COMMENT ON COLUMN work_shifts.staff_id IS 'Khóa ngoại tham chiếu nhân viên phụ trách ca users(id)';
COMMENT ON COLUMN work_shifts.staff_name IS 'Họ tên nhân viên phụ trách ca';
COMMENT ON COLUMN work_shifts.start_time IS 'Thời điểm nhân viên bấm mở ca';
COMMENT ON COLUMN work_shifts.end_time IS 'Thời điểm nhân viên bấm đóng ca và kết toán';
COMMENT ON COLUMN work_shifts.initial_cash IS 'Số tiền mặt ban đầu trong két khi mở ca (VND)';
COMMENT ON COLUMN work_shifts.cash_revenue IS 'Tổng doanh thu tiền mặt thu được trong suốt ca (VND)';
COMMENT ON COLUMN work_shifts.card_revenue IS 'Tổng doanh thu qua thẻ ngân hàng trong ca (VND)';
COMMENT ON COLUMN work_shifts.qr_revenue IS 'Tổng doanh thu quét mã VietQR trong ca (VND)';
COMMENT ON COLUMN work_shifts.total_revenue IS 'Tổng toàn bộ doanh thu bán hàng trong ca (VND)';
COMMENT ON COLUMN work_shifts.orders_count IS 'Tổng số đơn hàng thực hiện trong ca';
COMMENT ON COLUMN work_shifts.expected_cash IS 'Tiền mặt lý thuyết trong két = initial_cash + cash_revenue (VND)';
COMMENT ON COLUMN work_shifts.actual_cash IS 'Tiền mặt thực tế nhân viên kiểm đếm khi đóng ca (VND)';
COMMENT ON COLUMN work_shifts.difference IS 'Chênh lệch tiền mặt = actual_cash - expected_cash (VND)';
COMMENT ON COLUMN work_shifts.status IS 'Trạng thái ca làm việc (OPEN - Đang mở, CLOSED - Đã chốt ca)';
COMMENT ON COLUMN work_shifts.note IS 'Ghi chú bàn giao hoặc giải trình lý do thừa/thiếu tiền mặt';
COMMENT ON COLUMN work_shifts.created_at IS 'Thời điểm khởi tạo bản ghi ca làm việc';

-- Bang system_settings
COMMENT ON TABLE system_settings IS 'Bảng lưu trữ thông số cấu hình hệ thống dạng Key-Value';
COMMENT ON COLUMN system_settings.key IS 'Khóa định danh cấu hình duy nhất (vd: store_name, default_vat_rate, low_stock_threshold)';
COMMENT ON COLUMN system_settings.value IS 'Giá trị cấu hình dạng chuỗi ký tự';
COMMENT ON COLUMN system_settings.description IS 'Mô tả ý nghĩa của thông số cấu hình';
COMMENT ON COLUMN system_settings.updated_at IS 'Thời điểm cập nhật thông số gần nhất';

-- Bang landing_page_config
COMMENT ON TABLE landing_page_config IS 'Bảng lưu cấu hình nội dung hiển thị trang chủ Landing Page (CMS)';
COMMENT ON COLUMN landing_page_config.id IS 'Mã bản ghi cấu hình (mặc định landing-config-current)';
COMMENT ON COLUMN landing_page_config.version IS 'Số thứ tự phiên bản nội dung';
COMMENT ON COLUMN landing_page_config.is_published IS 'Cờ kích hoạt xuất bản nội dung ra trang chủ';
COMMENT ON COLUMN landing_page_config.brand IS 'Dữ liệu JSON chứa thông tin nhận diện thương hiệu (tên, logo, slogan, màu sắc)';
COMMENT ON COLUMN landing_page_config.nav IS 'Dữ liệu JSON danh sách menu điều hướng thanh tiêu đề';
COMMENT ON COLUMN landing_page_config.hero IS 'Dữ liệu JSON nội dung khối Hero Banner đầu trang';
COMMENT ON COLUMN landing_page_config.features IS 'Dữ liệu JSON danh sách đặc điểm nổi bật của tiệm bánh';
COMMENT ON COLUMN landing_page_config.solutions IS 'Dữ liệu JSON các giải pháp/dịch vụ cung cấp';
COMMENT ON COLUMN landing_page_config.pricing_plans IS 'Dữ liệu JSON các gói sản phẩm/combo giá';
COMMENT ON COLUMN landing_page_config.testimonials IS 'Dữ liệu JSON lời chứng thực, nhận xét của khách hàng';
COMMENT ON COLUMN landing_page_config.faqs IS 'Dữ liệu JSON các câu hỏi thường gặp và giải đáp';
COMMENT ON COLUMN landing_page_config.footer IS 'Dữ liệu JSON thông tin liên hệ và liên kết chân trang';
COMMENT ON COLUMN landing_page_config.updated_at IS 'Thời điểm cập nhật cấu hình Landing Page gần nhất';
COMMENT ON COLUMN landing_page_config.updated_by IS 'Mã người dùng thực hiện cập nhật gần nhất (tham chiếu logic users.id)';

-- Bang audit_logs
COMMENT ON TABLE audit_logs IS 'Bảng nhật ký kiểm toán (Audit Trail) ghi lại mọi thay đổi phân quyền và vai trò';
COMMENT ON COLUMN audit_logs.id IS 'Mã định danh bản ghi nhật ký (dạng audit-YYMMDD-xxxxxx)';
COMMENT ON COLUMN audit_logs.user_id IS 'Mã người dùng thực hiện thao tác (tham chiếu logic users.id)';
COMMENT ON COLUMN audit_logs.user_name IS 'Họ tên người dùng tại thời điểm thực hiện thao tác';
COMMENT ON COLUMN audit_logs.action IS 'Loại hành động thực hiện (ROLE_CREATE, ROLE_UPDATE_PERMISSIONS, ROLE_DELETE, USER_ROLE_CHANGE)';
COMMENT ON COLUMN audit_logs.target_type IS 'Loại đối tượng chịu tác động (ROLE, USER)';
COMMENT ON COLUMN audit_logs.target_id IS 'Mã đối tượng bị tác động';
COMMENT ON COLUMN audit_logs.target_name IS 'Tên đối tượng bị tác động';
COMMENT ON COLUMN audit_logs.changes_summary IS 'Tóm tắt nội dung thay đổi phân quyền';
COMMENT ON COLUMN audit_logs.details_json IS 'Chi tiết thay đổi dạng JSON string (before, after, diff_added, diff_removed)';
COMMENT ON COLUMN audit_logs.ip_address IS 'Địa chỉ IP của client gửi yêu cầu';
COMMENT ON COLUMN audit_logs.created_at IS 'Thời điểm ghi nhật ký kiểm toán';


-- =============================================================================
-- PHAN 5: DANH SACH CAC DIEM CHUA CHAC CHAN (DE TRUONG NHOM KIEM TRA)
-- =============================================================================
/*
DANH SACH CAC CHO KHONG CHAC (UNCERTAINTIES & DISCREPANCIES IN CODEBASE):

1. LECH NHAU GIUA ALEMBIC MIGRATIONS VA SQLALCHEMY MODELS:
   - Thu muc `alembic/versions` chi co 2 tap tin migration quan ly 8 bang:
     + 80ead1f52855_initial_schema.py (products, users, orders, order_items)
     + a1b2c3d4e5f6_add_pbac_tables.py (permissions, roles, role_permissions, audit_logs; bo sung role_id vao users)
   - 8 bang con lai (`branches`, `warehouses`, `stock_items`, `transactions`, `work_shifts`, `shift_templates`, `system_settings`, `landing_page_config`)
     CHUA CO tap tin migration Alembic tuong ung. Trong he thong, chung duoc tao tu dong bang lenh
     `Base.metadata.create_all(bind=engine)` tai `seed.py`.
   - Bang `users`: Trong migration 80ead1f52855, cot `role` la `String(20)`, nhung trong model `User` hien tai la `String(50)`.
     Ngoai ra, 2 cot `default_branch_id` va `last_active_branch_id` moi chi co trong model `User`, chua co migration.
   - Bang `orders`: 2 cot `branch_id` va `warehouse_id` da duoc bo sung vao model `Order`, nhung chua co migration.
   - Bang `products`: Model co `index=True` tren `stock` va `created_at`, co `default=0` cho `stock`, nhung migration ban dau khong co.

2. DO DAI KIEU DU LIEU CHUOI KHONG KHAI BAO (UNBOUNDED VARCHAR):
   - Trong SQLAlchemy, `sa.String()` khong co tham so do dai se duoc bien dich sang PostgreSQL thanh kieu `VARCHAR` khong gioi han (tuong duong `TEXT`).
   - Cac cot sau trong model khong khai bao do dai:
     + `branches.id` (seed.py tao dang `branch-xxxxxx`, tam quy uoc VARCHAR(50))
     + `warehouses.id` (seed.py tao dang `wh-xxxxxx`, tam quy uoc VARCHAR(50))
     + `warehouses.branch_id` (tham chieu branches.id, tam quy uoc VARCHAR(50))
     + `stock_items.id` (default tao dang `stk-xxxxxxxx`, tam quy uoc VARCHAR(50))
     + `stock_items.warehouse_id` (tham chieu warehouses.id, tam quy uoc VARCHAR(50))
     + `stock_items.product_id` (tham chieu products.id, tam quy uoc VARCHAR(50))
     + `work_shifts.id` (default tao dang `shift-xxxxxxxx`, tam quy uoc VARCHAR(50))
     + `work_shifts.staff_id` (tham chieu users.id, tam quy uoc VARCHAR(50))
     + `shift_templates.id` (default tao dang `tmpl-xxxxxx`, tam quy uoc VARCHAR(50))
   -> Kien nghi: Truong nhom can chot do dai toi da cu the cho cac khoa chinh / khoa ngoai nay tren Production.

3. DONG BO MUI GIO CHO CAC COT THOI GIAN (TIMEZONE):
   - Cac bang trong migration Alembic dung `sa.DateTime(timezone=True)` -> `TIMESTAMP WITH TIME ZONE` (UTC).
   - Cac bang tao sau trong `app/models/` (`branches`, `warehouses`, `stock_items`, `shift_templates`, `work_shifts`, `system_settings`)
     chi dung `sa.DateTime` khong co timezone -> PostgreSQL mac dinh tao `TIMESTAMP WITHOUT TIME ZONE`.
   -> Kien nghi: Nen dong bo toan bo cac cot thoi gian ve `TIMESTAMP WITH TIME ZONE` de nhat quan luu tru gio UTC.

4. CAC COT MANG Y NGHIA KHOA NGOAI LOGIC NHUNG THIEU RANG BUOC FOREIGN KEY VAT LY TRONG CODE:
   Trong code Python, nhieu cot duoc su dung de JOIN hoac filter theo id cua bang khac nhung KHONG co khai bao `ForeignKey(...)`:
   - `users.default_branch_id` -> logic lien ket toi `branches(id)`.
   - `users.last_active_branch_id` -> logic lien ket toi `branches(id)`.
   - `orders.branch_id` -> logic lien ket toi `branches(id)`.
   - `orders.warehouse_id` -> logic lien ket toi `warehouses(id)`.
   - `transactions.branch_id` -> logic lien ket toi `branches(id)`.
   - `work_shifts.branch_id` -> logic lien ket toi `branches(id)`.
   - `work_shifts.template_id` -> logic lien ket toi `shift_templates(id)`.
   - `audit_logs.user_id` -> logic lien ket toi `users(id)` (co the co y de khong bi chan khi xoa user).
   - `landing_page_config.updated_by` -> logic lien ket toi `users(id)`.
   -> QRD quy dinh khong tu doan bieu nen trong schema.sql khong tu y tao FOREIGN KEY vat ly cho cac cot nay,
      chi tao FK cho 10 quan he co khai bao `ForeignKey` chinh thuc trong code.

5. KIEU DU LIEU GIO TRONG BANG shift_templates:
   - Cot `start_time` va `end_time` trong `shift_templates` dang luu chuoi `VARCHAR(10)` (vd: "06:30", "14:30") thay vi kieu `TIME` cua PostgreSQL.

6. KIEU DU LIEU JSON VS JSONB TRONG landing_page_config:
   - Model khai bao `sa.JSON` (PostgreSQL compile thanh `JSON`).
   -> Kien nghi: Co the chuyen sang `JSONB` tren PostgreSQL 16 de tang toc truy van va giam dung luong luu tru.

7. GIA TRI MAC DINH PHIA PYTHON VS PHIA DATABASE (DEFAULT VS SERVER_DEFAULT):
   - Phan lon cac cot trong SQLAlchemy model chi co `default=...` (Python-level default duoc danh gia khi app insert),
     chi co `roles.is_system` va `roles.permissions_version` la co `server_default='...'` trong migration.
   - Trong schema.sql, cac gia tri nay da duoc dien thanh `DEFAULT ...` trong DDL de dam bao khi insert truc tiep bang SQL khong bi null.
*/
