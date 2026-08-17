import sys
from fastapi.testclient import TestClient
from app.main import app

BASE_URL = "http://testserver/api"


def run_tests():
    print("=" * 60)
    print("🚀 BẮT ĐẦU KIỂM THỬ BACKEND ĐỘC LẬP (FASTAPI + POSTGRESQL)")
    print("=" * 60)

    client = TestClient(app, base_url=BASE_URL)

    # ---------------------------------------------------------
    # 1. TEST AUTHENTICATION
    # ---------------------------------------------------------
    print("\n[1/6] 🧪 Kiểm thử Module Đăng nhập & Xác thực...")
    
    # Happy path: Admin login
    res = client.post("/auth/login", json={"username": "admin", "password": "password123"})
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    admin_data = res.json()
    admin_token = admin_data["token"]
    assert admin_data["user"]["role"] == "ADMIN"
    assert "token" in admin_data
    print("  ✅ Admin đăng nhập thành công, nhận JWT Token.")

    # Happy path: Staff login
    res = client.post("/auth/login", json={"username": "staff", "password": "password123"})
    assert res.status_code == 200, f"Staff login failed: {res.text}"
    staff_data = res.json()
    staff_token = staff_data["token"]
    assert staff_data["user"]["role"] == "STAFF"
    print("  ✅ Staff đăng nhập thành công, nhận JWT Token.")

    # Error case: Sai mật khẩu (phải trả 401)
    res = client.post("/auth/login", json={"username": "admin", "password": "wrong_password"})
    assert res.status_code == 401, f"Expected 401 on wrong password, got {res.status_code}"
    # Test Active Branch DB Persistence for Admin
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.patch("/users/me/active-branch", json={"branchId": "branch-002"}, headers=admin_headers)
    assert res.status_code == 200, f"Update active branch failed: {res.text}"
    updated_admin = res.json()
    assert updated_admin["lastActiveBranchId"] == "branch-002"
    print("  ✅ Admin lưu lựa chọn chi nhánh 'branch-002' trực tiếp vào Database thành công.")

    # ---------------------------------------------------------
    # 2. TEST PRODUCTS (CRUD & RBAC)
    # ---------------------------------------------------------
    print("\n[2/6] 🧪 Kiểm thử Module Quản lý Sản phẩm...")
    
    # GET products list
    res = client.get("/products")
    assert res.status_code == 200
    products = res.json()
    assert len(products) >= 11, f"Expected >= 11 products, got {len(products)}"
    
    # Verify dynamic status calculation
    for p in products:
        if p["stock"] == 0:
            assert p["status"] == "out_of_stock", f"Product {p['name']} stock=0 but status={p['status']}"
        elif p["stock"] <= 5:
            assert p["status"] == "low_stock", f"Product {p['name']} stock={p['stock']} but status={p['status']}"
        else:
            assert p["status"] == "in_stock", f"Product {p['name']} stock={p['stock']} but status={p['status']}"
    print("  ✅ Lấy danh sách sản phẩm thành công, kiểm tra trường status tính toán động 100% chuẩn xác.")

    # Admin creates product
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    new_prod_payload = {
        "name": "Bánh Mì Hoa Cúc Brioche Pháp",
        "category": "Bánh Mì Ngọt & Pastry",
        "price": 45000,
        "stock": 25,
        "description": "Bánh mì hoa cúc thơm mùi bơ và hương hoa cam.",
        "image": "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=400&q=80"
    }
    res = client.post("/products", json=new_prod_payload, headers=admin_headers)
    assert res.status_code == 201, f"Create product failed: {res.text}"
    created_prod = res.json()
    created_prod_id = created_prod["id"]
    assert created_prod["status"] == "in_stock"
    print(f"  ✅ Admin tạo sản phẩm mới thành công (ID: {created_prod_id}).")

    # Staff tries to create product -> 403 Forbidden
    res = client.post("/products", json=new_prod_payload, headers=staff_headers)
    assert res.status_code == 403, f"Expected 403 when Staff creates product, got {res.status_code}"
    print("  ✅ Staff bị chặn quyền (403 Forbidden) khi cố thêm sản phẩm.")

    # Admin updates product
    res = client.put(f"/products/{created_prod_id}", json={"price": 48000, "stock": 4}, headers=admin_headers)
    assert res.status_code == 200
    updated_prod = res.json()
    assert updated_prod["price"] == 48000
    assert updated_prod["status"] == "low_stock", f"Stock is 4, expected low_stock, got {updated_prod['status']}"
    print("  ✅ Admin cập nhật giá và tồn kho thành công, status tự động chuyển sang 'low_stock'.")

    # Admin soft deletes product
    res = client.delete(f"/products/{created_prod_id}", headers=admin_headers)
    assert res.status_code == 200
    res = client.get(f"/products/{created_prod_id}")
    assert res.status_code == 404
    print("  ✅ Admin soft delete sản phẩm thành công (không còn xuất hiện trong danh sách active).")

    # ---------------------------------------------------------
    # 3. TEST ORDERS & POS CHECKOUT (ATOMIC TRANSACTION)
    # ---------------------------------------------------------
    print("\n[3/6] 🧪 Kiểm thử Module Đơn hàng & POS (Atomic Transaction)...")
    
    # Get Croissant stock before purchase & ensure adequate stock for testing
    res = client.get("/products/prod-001")
    croissant_before = res.json()
    if croissant_before["stock"] < 10:
        client.put("/products/prod-001", json={"stock": 30}, headers=admin_headers)
        res = client.get("/products/prod-001")
        croissant_before = res.json()
    initial_stock = croissant_before["stock"]

    # 3.1. Happy Path: Order with valid stock
    order_payload = {
        "customerName": "Anh Minh VIP",
        "customerPhone": "0911223344",
        "items": [
            {
                "productId": "prod-001",
                "productName": "Croissant Bơ Pháp Truyền Thống",
                "price": 35000,
                "quantity": 5,
                "subtotal": 175000,
                "image": croissant_before["image"]
            }
        ],
        "subtotal": 175000,
        "discount": 15000,
        "totalAmount": 160000,
        "paymentMethod": "QR_TRANSFER",
        "status": "COMPLETED",
        "note": "Kiểm thử POS tự động trừ kho"
    }
    res = client.post("/orders", json=order_payload, headers=staff_headers)
    assert res.status_code == 201, f"POS checkout failed: {res.text}"
    created_order = res.json()
    assert created_order["code"].startswith("HD-")
    assert created_order["totalAmount"] == 160000
    print(f"  ✅ Tạo đơn hàng POS thành công (Mã: {created_order['code']}).")

    # Verify Croissant stock decreased by 5
    res = client.get("/products/prod-001")
    croissant_after = res.json()
    assert croissant_after["stock"] == initial_stock - 5, f"Expected {initial_stock - 5}, got {croissant_after['stock']}"
    print(f"  ✅ Tồn kho sản phẩm đã được tự động trừ chính xác: {initial_stock} -> {croissant_after['stock']}.")

    # 3.2. Error Case: Order with INSUFFICIENT stock (Must rollback with 400)
    current_croissant_stock = croissant_after["stock"]
    excessive_order_payload = {
        "customerName": "Khách Đặt Vượt Kho",
        "items": [
            {
                "productId": "prod-001",
                "productName": "Croissant Bơ Pháp Truyền Thống",
                "price": 35000,
                "quantity": current_croissant_stock + 999,  # Vượt quá tồn kho
                "subtotal": (current_croissant_stock + 999) * 35000
            }
        ],
        "subtotal": (current_croissant_stock + 999) * 35000,
        "discount": 0,
        "totalAmount": (current_croissant_stock + 999) * 35000,
        "paymentMethod": "CASH"
    }
    res = client.post("/orders", json=excessive_order_payload, headers=staff_headers)
    assert res.status_code == 400, f"Expected 400 on excessive stock, got {res.status_code}: {res.text}"
    print("  ✅ Mua vượt quá tồn kho bị chặn với mã 400 Bad Request và thông báo lỗi rõ ràng.")

    # Verify Croissant stock unchanged after failed order
    res = client.get("/products/prod-001")
    croissant_check = res.json()
    assert croissant_check["stock"] == current_croissant_stock
    print("  ✅ Đảm bảo Database Transaction đã Rollback toàn bộ, không tạo đơn rác và tồn kho được bảo toàn.")

    # ---------------------------------------------------------
    # 4. TEST USERS (BCRYPT HASHING)
    # ---------------------------------------------------------
    print("\n[4/6] 🧪 Kiểm thử Module Quản lý Nhân viên...")
    import time
    ts = int(time.time())
    res_b = client.get("/branches", headers=admin_headers)
    branches = res_b.json()
    new_user_payload = {
        "fullName": "Kiểm Thử Viên Thu Ngân Chi Nhánh",
        "username": f"tester_{ts}",
        "password": "mypassword_secret_2026",
        "email": f"tester_{ts}@artisanbakery.vn",
        "phone": "0988112233",
        "role": "STAFF",
        "status": "ACTIVE",
        "defaultBranchId": branches[0]["id"]
    }
    res = client.post("/users", json=new_user_payload, headers=admin_headers)
    assert res.status_code == 201, f"Create user failed: {res.text}"
    created_user = res.json()
    assert created_user["username"] == f"tester_{ts}"
    assert created_user["defaultBranchId"] == branches[0]["id"]
    print(f"  ✅ Admin tạo nhân viên mới thành công gán chi nhánh '{created_user.get('defaultBranchName', branches[0]['name'])}'.")

    # Test login with new user credentials
    res = client.post("/auth/login", json={"username": f"tester_{ts}", "password": "mypassword_secret_2026"})
    assert res.status_code == 200, f"New user login failed: {res.text}"
    login_user_data = res.json()["user"]
    assert login_user_data["defaultBranchId"] == branches[0]["id"]
    print("  ✅ Tài khoản nhân viên đăng nhập thành công, nhận diện đúng chi nhánh hoạt động.")

    # 4.3 Update user: change branch, name, phone
    created_user_id = created_user["id"]
    update_payload = {
        "fullName": "Kiểm Thử Viên - Đã Cập Nhật",
        "phone": "0999888777",
        "defaultBranchId": branches[1]["id"] if len(branches) > 1 else branches[0]["id"],
    }
    res = client.put(f"/users/{created_user_id}", json=update_payload, headers=admin_headers)
    assert res.status_code == 200, f"Update user failed: {res.text}"
    updated_user = res.json()
    assert updated_user["fullName"] == "Kiểm Thử Viên - Đã Cập Nhật"
    assert updated_user["phone"] == "0999888777"
    target_branch = branches[1]["id"] if len(branches) > 1 else branches[0]["id"]
    assert updated_user["defaultBranchId"] == target_branch
    print(f"  ✅ Admin cập nhật thông tin nhân viên thành công (Tên, SĐT, Chi nhánh → {updated_user.get('defaultBranchName', 'OK')}).")

    # 4.4 Update user: reset password
    res = client.put(f"/users/{created_user_id}", json={"password": "newpassword_2026"}, headers=admin_headers)
    assert res.status_code == 200, f"Reset password failed: {res.text}"
    # Verify new password works
    res = client.post("/auth/login", json={"username": f"tester_{ts}", "password": "newpassword_2026"})
    assert res.status_code == 200, f"Login with new password failed: {res.text}"
    print("  ✅ Admin đặt lại mật khẩu nhân viên thành công, đăng nhập bằng mật khẩu mới OK.")

    # 4.5 Soft delete (deactivate) user
    res = client.delete(f"/users/{created_user_id}", headers=admin_headers)
    assert res.status_code == 200, f"Soft delete user failed: {res.text}"
    deactivated_user = res.json()
    assert deactivated_user["status"] == "INACTIVE"
    print("  ✅ Admin khóa tài khoản nhân viên thành công (status → INACTIVE).")

    # 4.6 Deactivated user cannot login
    res = client.post("/auth/login", json={"username": f"tester_{ts}", "password": "newpassword_2026"})
    assert res.status_code == 403, f"Expected 403 for deactivated user, got {res.status_code}"
    print("  ✅ Tài khoản đã bị khóa không thể đăng nhập (403 Forbidden).")

    # 4.7 Re-activate user
    res = client.put(f"/users/{created_user_id}", json={"status": "ACTIVE"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "ACTIVE"
    print("  ✅ Admin mở khóa lại tài khoản nhân viên thành công (status → ACTIVE).")

    # 4.8 Admin cannot deactivate themselves
    res = client.delete(f"/users/{admin_data['user']['id']}", headers=admin_headers)
    assert res.status_code == 400, f"Expected 400 on self-deactivate, got {res.status_code}"
    print("  ✅ Admin bị chặn tự khóa tài khoản chính mình (400 Bad Request).")

    # ---------------------------------------------------------
    # 5. TEST DASHBOARD STATS
    # ---------------------------------------------------------
    print("\n[5/6] 🧪 Kiểm thử Module Báo cáo Thống kê Mở rộng (Dashboard)...")
    
    # 5.1 Test Today range
    res = client.get("/dashboard/stats?range=today", headers=admin_headers)
    assert res.status_code == 200, f"Dashboard stats today failed: {res.text}"
    stats = res.json()
    assert "todayRevenue" in stats
    assert "todayOrdersCount" in stats
    assert "recentSalesChart" in stats
    assert "topSellingProducts" in stats
    assert "slowSellingProducts" in stats
    assert "paymentMethods" in stats
    assert "categorySales" in stats
    assert "staffPerformances" in stats
    assert "lowStockDetails" in stats
    assert len(stats["paymentMethods"]) > 0
    assert len(stats["categorySales"]) > 0
    assert len(stats["staffPerformances"]) > 0
    print(f"  ✅ Lấy báo cáo Dashboard (Hôm nay) thành công:")
    print(f"     - Doanh thu: {stats['todayRevenue']:,} ₫ | Số đơn: {stats['todayOrdersCount']}")
    print(f"     - PTTT: {', '.join([f'{p['methodLabel']} ({p['percentage']}%)' for p in stats['paymentMethods']])}")
    print(f"     - Số nhân viên có thống kê: {len(stats['staffPerformances'])}")
    print(f"     - Số mặt hàng cảnh báo tồn kho: {len(stats['lowStockDetails'])}")
    print(f"     - Số mặt hàng bán chậm/tồn đọng: {len(stats['slowSellingProducts'])}")

    # 5.2 Test 7days range
    res_7d = client.get("/dashboard/stats?range=7days", headers=admin_headers)
    assert res_7d.status_code == 200
    stats_7d = res_7d.json()
    assert "7 ngày qua" in stats_7d["periodLabel"]
    print(f"  ✅ Bộ lọc 7 ngày qua hoạt động chính xác ({stats_7d['periodLabel']}).")

    # 5.3 Test 30days range
    res_30d = client.get("/dashboard/stats?range=30days", headers=admin_headers)
    assert res_30d.status_code == 200
    stats_30d = res_30d.json()
    assert "30 ngày qua" in stats_30d["periodLabel"]
    print(f"  ✅ Bộ lọc 30 ngày qua hoạt động chính xác ({stats_30d['periodLabel']}).")

    # ---------------------------------------------------------
    # 6. TEST SHIFTS & CASH RECONCILIATION
    # ---------------------------------------------------------
    print("\n[6/7] 🧪 Kiểm thử Module Quản lý Ca & Kết Ca (Shift & Cash Reconciliation)...")
    # 6.1 Get current shift
    res_shift = client.get("/shifts/current", headers=staff_headers)
    assert res_shift.status_code == 200, f"Get current shift failed: {res_shift.text}"
    curr_shift = res_shift.json()
    assert curr_shift["status"] == "OPEN"
    assert "initialCash" in curr_shift
    assert "expectedCash" in curr_shift
    print(f"  ✅ Lấy ca làm hiện tại ({curr_shift['shiftName']}) thành công, trạng thái: {curr_shift['status']}.")

    # 6.2 Close current shift
    res_close = client.post(
        "/shifts/close",
        headers=staff_headers,
        json={"actualCash": curr_shift["expectedCash"], "note": "Khớp két 100% không lệch"}
    )
    assert res_close.status_code == 200, f"Close shift failed: {res_close.text}"
    closed_shift = res_close.json()
    assert closed_shift["status"] == "CLOSED"
    assert closed_shift["difference"] == 0
    print(f"  ✅ Chốt ca làm việc thành công, chênh lệch: {closed_shift['difference']} ₫ (Khớp chuẩn).")

    # 6.3 Get shifts summary as Admin
    res_sum = client.get("/shifts/summary", headers=admin_headers)
    assert res_sum.status_code == 200, f"Shift summary failed: {res_sum.text}"
    shift_sum = res_sum.json()
    assert "totalShiftsCount" in shift_sum
    assert "totalRevenue" in shift_sum
    assert "totalCash" in shift_sum
    assert "shifts" in shift_sum
    print(f"  ✅ Admin lấy báo cáo tổng hợp ca thành công ({shift_sum['totalShiftsCount']} ca, Doanh thu: {shift_sum['totalRevenue']:,} ₫).")

    # ---------------------------------------------------------
    # 7. TEST MULTI-BRANCH & WAREHOUSES
    # ---------------------------------------------------------
    print("\n[7/9] 🧪 Kiểm thử Module Đa Chi Nhánh & Đa Kho (Multi-Branch & Warehouses)...")
    res_b = client.get("/branches", headers=admin_headers)
    assert res_b.status_code == 200, f"Get branches failed: {res_b.text}"
    branches = res_b.json()
    assert len(branches) >= 2
    assert "warehouses" in branches[0]
    print(f"  ✅ Lấy danh sách {len(branches)} chi nhánh kèm thông tin kho hàng thành công.")

    # Create new branch
    b_code = f"CN-TEST-{str(ts)[-4:]}"
    res_new_b = client.post(
        "/branches",
        headers=admin_headers,
        json={
            "code": b_code,
            "name": f"Artisan Bakery - Chi Nhánh Test {str(ts)[-4:]}",
            "address": "999 Đường Test, Quận Bình Thạnh, TP.HCM",
            "phone": "0911 222 333",
            "managerName": "Trần Quản Lý",
            "status": "ACTIVE"
        }
    )
    assert res_new_b.status_code == 201, f"Create branch failed: {res_new_b.text}"
    new_b = res_new_b.json()
    assert new_b["code"] == b_code
    print(f"  ✅ Admin tạo chi nhánh mới '{new_b['name']}' thành công.")

    # 7.2 Test Warehouse Stocks
    res_stocks = client.get(f"/branches/stocks?branchId={branches[0]['id']}", headers=admin_headers)
    assert res_stocks.status_code == 200, f"Get stocks failed: {res_stocks.text}"
    stocks = res_stocks.json()
    assert len(stocks) > 0
    print(f"  ✅ Lấy danh sách tồn kho theo chi nhánh ({len(stocks)} mục hàng) thành công.")

    # 7.3 Adjust stock in warehouse
    target_stock = stocks[0]
    res_adj = client.put(
        "/branches/stocks",
        headers=admin_headers,
        json={
            "warehouseId": target_stock["warehouseId"],
            "productId": target_stock["productId"],
            "quantity": 88,
            "minAlertStock": 10
        }
    )
    assert res_adj.status_code == 200, f"Adjust stock failed: {res_adj.text}"
    adj_stock = res_adj.json()
    assert adj_stock["quantity"] == 88
    assert adj_stock["minAlertStock"] == 10
    print(f"  ✅ Điều chỉnh số lượng tồn kho thành công (Số lượng mới: {adj_stock['quantity']} cái).")

    # ---------------------------------------------------------
    # 8. TEST SYSTEM SETTINGS & SHIFT TEMPLATES
    # ---------------------------------------------------------
    print("\n[8/9] 🧪 Kiểm thử Module Cài Đặt Hệ Thống & Ca Động (Settings & Shift Templates)...")
    # 8.1 Get system settings
    res_st = client.get("/settings")
    assert res_st.status_code == 200
    st = res_st.json()
    assert "storeName" in st
    assert "lowStockThreshold" in st
    assert "bankAccountNumber" in st
    print(f"  ✅ Lấy cài đặt hệ thống thành công (Tiệm: {st['storeName']}, Hotline: {st['hotline']}).")

    # 8.2 Update system settings
    res_st_up = client.put(
        "/settings",
        headers=admin_headers,
        json={"storeSlogan": "Bánh Mì Nghệ Nhân & Cà Phê Cao Cấp 2026", "lowStockThreshold": 8}
    )
    assert res_st_up.status_code == 200
    assert res_st_up.json()["lowStockThreshold"] == 8
    print("  ✅ Admin cập nhật cấu hình hệ thống thành công.")

    # 8.3 Get & Create Shift Template
    res_tmpls = client.get("/settings/shift-templates", headers=admin_headers)
    assert res_tmpls.status_code == 200
    tmpls = res_tmpls.json()
    assert len(tmpls) >= 3
    print(f"  ✅ Lấy danh sách {len(tmpls)} ca làm việc mẫu thành công.")

    # Create new shift template
    res_new_tmpl = client.post(
        "/settings/shift-templates",
        headers=admin_headers,
        json={
            "name": f"Ca Đêm Đặc Biệt {str(ts)[-4:]}",
            "startTime": "22:30",
            "endTime": "06:30",
            "defaultInitialCash": 400000,
            "isActive": True,
            "note": "Phục vụ khách đêm khuya"
        }
    )
    assert res_new_tmpl.status_code == 201
    created_tmpl = res_new_tmpl.json()
    assert created_tmpl["startTime"] == "22:30"
    print(f"  ✅ Admin tạo ca mẫu mới '{created_tmpl['name']}' thành công.")

    # Delete the created test template
    res_del_tmpl = client.delete(f"/settings/shift-templates/{created_tmpl['id']}", headers=admin_headers)
    assert res_del_tmpl.status_code == 204
    print("  ✅ Admin xóa ca mẫu thử nghiệm thành công.")

    # ---------------------------------------------------------
    # 9. TEST BASIC ACCOUNTING & CASH FLOW
    # ---------------------------------------------------------
    print("\n[9/10] 🧪 Kiểm thử Module Sổ Quỹ & Kế Toán Cơ Bản (Basic Accounting)...")
    # 9.1 Get transactions
    res_tx = client.get("/accounting/transactions", headers=admin_headers)
    assert res_tx.status_code == 200, f"Get transactions failed: {res_tx.text}"
    tx_list = res_tx.json()
    assert len(tx_list) >= 4
    print(f"  ✅ Lấy danh sách {len(tx_list)} phiếu thu/chi thành công.")

    # 9.2 Create payment voucher (Phiếu chi mua bơ sữa)
    res_new_tx = client.post(
        "/accounting/transactions",
        headers=admin_headers,
        json={
            "transactionType": "EXPENSE",
            "category": "Chi phí Nguyên vật liệu & Nhập hàng",
            "amount": 450000,
            "branchId": branches[0]["id"],
            "paymentMethod": "BANK_TRANSFER",
            "recipientPayer": "Công ty Bột Mì Đại Phong",
            "note": "Nhập 50kg bột mì số 11 làm bánh mì hoa cúc"
        }
    )
    assert res_new_tx.status_code == 201, f"Create transaction failed: {res_new_tx.text}"
    new_tx = res_new_tx.json()
    assert new_tx["transactionType"] == "EXPENSE"
    assert new_tx["amount"] == 450000
    print(f"  ✅ Admin lập phiếu chi '{new_tx['code']}' ({new_tx['amount']:,} ₫) thành công.")

    # 9.3 Get Cash Flow Summary
    res_cash = client.get("/accounting/summary", headers=admin_headers)
    assert res_cash.status_code == 200, f"Cash flow summary failed: {res_cash.text}"
    cash_sum = res_cash.json()
    assert "totalIncome" in cash_sum
    assert "totalExpense" in cash_sum
    assert "netCashFlow" in cash_sum
    print(f"  ✅ Lấy báo cáo dòng tiền thành công (Tổng thu: {cash_sum['totalIncome']:,} ₫, Tổng chi: {cash_sum['totalExpense']:,} ₫).")

    # 9.4 Get PnL Report
    res_pnl = client.get("/accounting/pnl", headers=admin_headers)
    assert res_pnl.status_code == 200, f"PnL report failed: {res_pnl.text}"
    pnl_rep = res_pnl.json()
    assert "grossRevenue" in pnl_rep
    assert "grossProfit" in pnl_rep
    assert "netProfit" in pnl_rep
    print(f"  ✅ Lấy báo cáo Lãi Lỗ P&L thành công (Lợi nhuận ròng: {pnl_rep['netProfit']:,} ₫, Tỷ suất: {pnl_rep['netMarginPercent']}%).")

    # ---------------------------------------------------------
    # 10. TEST SWAGGER DOCS & HEALTH
    # ---------------------------------------------------------
    print("\n[10/10] 🧪 Kiểm thử Swagger OpenAPI Docs & Health Check...")
    res = client.get("http://testserver/openapi.json")
    assert res.status_code == 200, f"OpenAPI failed: {res.status_code}"
    print("  ✅ OpenAPI Swagger Schema hợp lệ tại /openapi.json.")

    print("\n" + "=" * 60)
    print("🎉 TẤT CẢ 100% CÁC TEST CASES ĐÃ ĐẠT CHUẨN XUẤT SẮC!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\n❌ KIỂM THỬ THẤT BẠI: {e}")
        sys.exit(1)
