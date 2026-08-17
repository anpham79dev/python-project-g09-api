"""
Single Source of Truth for RBAC Permissions Catalog & System Roles.
"""

from typing import Dict, List, TypedDict


class PermissionDef(TypedDict):
    code: str
    name: str
    module: str
    description: str


# Catalog of exactly 21 atomic permissions across 8 modules
ALL_PERMISSIONS: List[PermissionDef] = [
    # 1. Tổng Quan & Dashboard
    {
        "code": "dashboard:view",
        "name": "Xem Báo Cáo & Thống Kê",
        "module": "Tổng Quan",
        "description": "Xem báo cáo doanh thu, xu hướng bán hàng và thống kê tổng quan",
    },
    # 2. Quầy Bán Hàng (POS)
    {
        "code": "pos:access",
        "name": "Truy Cập Quầy Thu Ngân",
        "module": "POS",
        "description": "Truy cập giao diện quầy bán lẻ POS và danh mục bán",
    },
    {
        "code": "pos:checkout",
        "name": "Thanh Toán & In Hóa Đơn",
        "module": "POS",
        "description": "Thực hiện thanh toán đơn hàng (Tiền mặt, QR, Thẻ) và in hóa đơn",
    },
    # 3. Sản Phẩm & Danh Mục
    {
        "code": "products:read",
        "name": "Xem Danh Mục Sản Phẩm",
        "module": "Sản Phẩm",
        "description": "Xem danh sách và chi tiết các loại bánh, giá bán và công thức",
    },
    {
        "code": "products:write",
        "name": "Thêm/Sửa/Xóa Sản Phẩm",
        "module": "Sản Phẩm",
        "description": "Tạo mới, chỉnh sửa thông tin giá và ngừng kinh doanh sản phẩm",
    },
    # 4. Kho Hàng & Tồn Kho
    {
        "code": "inventory:read",
        "name": "Xem Tồn Kho Chi Nhánh",
        "module": "Kho Hàng",
        "description": "Xem số lượng tồn kho thực tế theo từng chi nhánh/kho hàng",
    },
    {
        "code": "inventory:write",
        "name": "Cập Nhật Tồn Kho & Định Mức",
        "module": "Kho Hàng",
        "description": "Điều chỉnh số lượng tồn kho, cấu hình mức cảnh báo tối thiểu",
    },
    # 5. Đơn Hàng & Hóa Đơn
    {
        "code": "orders:read",
        "name": "Xem Lịch Sử Đơn Hàng",
        "module": "Đơn Hàng",
        "description": "Xem danh sách hóa đơn bán hàng và chi tiết từng giao dịch",
    },
    {
        "code": "orders:export",
        "name": "In Lại & Xuất Hóa Đơn",
        "module": "Đơn Hàng",
        "description": "In lại hóa đơn bán lẻ hoặc xuất dữ liệu đơn hàng",
    },
    # 6. Ca Làm Việc & Bàn Giao
    {
        "code": "shifts:read",
        "name": "Xem Lịch Sử Ca & Bàn Giao Két",
        "module": "Ca Làm Việc",
        "description": "Xem thông tin ca đang mở và lịch sử các ca làm việc đã kết ca",
    },
    {
        "code": "shifts:manage",
        "name": "Quản Lý Ca & Mẫu Ca",
        "module": "Ca Làm Việc",
        "description": "Bắt đầu ca, kết ca, kiểm đếm tiền két và quản lý ca làm việc mẫu",
    },
    # 7. Tài Chính & Kế Toán
    {
        "code": "accounting:read",
        "name": "Xem Sổ Quỹ Thu Chi",
        "module": "Kế Toán",
        "description": "Xem danh sách các phiếu thu, phiếu chi và tổng kết dòng tiền",
    },
    {
        "code": "accounting:write",
        "name": "Lập Phiếu Thu / Chi Tiền",
        "module": "Kế Toán",
        "description": "Tạo mới phiếu thu tiền mặt/chuyển khoản hoặc lập phiếu chi mua nguyên liệu",
    },
    {
        "code": "accounting:pnl",
        "name": "Xem Báo Cáo Lãi Lỗ (P&L)",
        "module": "Kế Toán",
        "description": "Xem báo cáo kết quả hoạt động kinh doanh, lợi nhuận ròng P&L",
    },
    # 8. Chi Nhánh & Địa Điểm
    {
        "code": "branches:read",
        "name": "Xem Danh Sách Chi Nhánh",
        "module": "Chi Nhánh",
        "description": "Xem danh sách các cửa hàng và kho trực thuộc",
    },
    {
        "code": "branches:manage",
        "name": "Thêm/Sửa Chi Nhánh & Kho",
        "module": "Chi Nhánh",
        "description": "Thêm chi nhánh mới, cập nhật thông tin địa chỉ và kho hàng",
    },
    # 9. Nhân Sự & Tài Khoản
    {
        "code": "users:read",
        "name": "Xem Danh Sách Nhân Viên",
        "module": "Nhân Sự",
        "description": "Xem danh sách tài khoản nhân viên và thông tin vai trò",
    },
    {
        "code": "users:manage",
        "name": "Thêm/Sửa/Khóa Tài Khoản",
        "module": "Nhân Sự",
        "description": "Tạo tài khoản mới, phân vai trò và khóa/mở khóa nhân viên",
    },
    # 10. Hệ Thống & Vai Trò
    {
        "code": "roles:manage",
        "name": "Quản Lý Vai Trò & Phân Quyền",
        "module": "Hệ Thống",
        "description": "Tạo vai trò mới và cấu hình phân quyền nguyên tử cho các vai trò",
    },
    {
        "code": "settings:manage",
        "name": "Cài Đặt Hệ Thống & Cửa Hàng",
        "module": "Hệ Thống",
        "description": "Cập nhật thông tin tiệm bánh, cấu hình thanh toán VietQR và ca mẫu",
    },
    # 11. Landing Page CMS
    {
        "code": "landing_page:edit",
        "name": "Quản Trị Nội Dung Landing Page",
        "module": "Landing CMS",
        "description": "Chỉnh sửa nội dung thương hiệu, hero, bảng giá và xuất bản Landing Page",
    },
]

# Set of all 21 permission codes
ALL_PERMISSION_CODES: List[str] = [p["code"] for p in ALL_PERMISSIONS]

# System Roles Default Permissions Mapping
SYSTEM_ROLES_CONFIG: Dict[str, Dict] = {
    "SUPER_ADMIN": {
        "id": "role-superadmin",
        "code": "SUPER_ADMIN",
        "name": "Tổng Quản Trị Hệ Thống",
        "description": "Toàn quyền truy cập và quản trị toàn bộ hệ thống ERP SaaS và Landing Page CMS.",
        "is_system": True,
        "permissions": ALL_PERMISSION_CODES,  # 21/21 permissions
    },
    "ADMIN": {
        "id": "role-admin",
        "code": "ADMIN",
        "name": "Quản Trị Viên (Chủ Chuỗi)",
        "description": "Toàn quyền quản trị nghiệp vụ chuỗi tiệm bánh (Bán hàng, Kho, Đơn, Sổ quỹ, Nhân sự, Cài đặt).",
        "is_system": True,
        "permissions": [code for code in ALL_PERMISSION_CODES if code != "landing_page:edit"],  # 20/21 permissions
    },
    "STAFF": {
        "id": "role-staff",
        "code": "STAFF",
        "name": "Nhân Viên Thu Ngân",
        "description": "Quyền bán hàng POS, xem danh mục sản phẩm, quản lý đơn hàng và bàn giao ca làm việc.",
        "is_system": True,
        "permissions": [
            "pos:access",
            "pos:checkout",
            "products:read",
            "orders:read",
            "shifts:read",
        ],  # 5/21 permissions
    },
}
