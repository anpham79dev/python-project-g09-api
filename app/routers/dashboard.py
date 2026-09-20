from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.dependencies import get_db, require_permission
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.setting import SystemSetting
from app.core.timezone import get_now_vn, get_period_range_vn, get_date_range_vn, VN_TZ
from app.schemas.dashboard import (
    DashboardStatsResponse,
    HourlySaleItem,
    TopSellingProductItem,
    SlowSellingProductItem,
    PaymentMethodStat,
    CategoryStat,
    StaffPerformanceStat,
    LowStockDetailItem
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    time_range: str = Query(default="today", alias="range", description="Time range: today, 7days, 30days, custom"),
    start_date: Optional[str] = Query(default=None, description="Start date YYYY-MM-DD for custom range"),
    end_date: Optional[str] = Query(default=None, description="End date YYYY-MM-DD for custom range"),
    branch_id: Optional[str] = Query(default=None, description="Branch ID filter"),
    branchId: Optional[str] = Query(default=None, description="Alias for branch_id"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("dashboard:view"))
):
    """Calculate executive KPI analytics dynamically from DB using Vietnam timezone (Asia/Ho_Chi_Minh)."""
    target_branch = branchId or branch_id
    if target_branch == "ALL":
        target_branch = None

    now_vn = get_now_vn()
    today_vn = now_vn.date()

    # Determine exact UTC bounds for current period using VN calendar
    cur_start_dt, cur_end_dt = get_period_range_vn(time_range, start_date, end_date)

    # Determine previous period for comparative growth metrics
    if time_range in ["7days", "7d"]:
        cur_start_d = today_vn - timedelta(days=6)
        cur_end_d = today_vn
        prev_start_d = cur_start_d - timedelta(days=7)
        prev_end_d = cur_start_d - timedelta(days=1)
        prev_start_dt, _ = get_date_range_vn(prev_start_d.strftime("%Y-%m-%d"))
        _, prev_end_dt = get_date_range_vn(prev_end_d.strftime("%Y-%m-%d"))
        period_label = f"7 ngày qua ({cur_start_d.strftime('%d/%m')} - {cur_end_d.strftime('%d/%m')})"
        previous_period_label = "so với 7 ngày trước"
    elif time_range in ["30days", "30d", "month"]:
        cur_start_d = today_vn - timedelta(days=29)
        cur_end_d = today_vn
        prev_start_d = cur_start_d - timedelta(days=30)
        prev_end_d = cur_start_d - timedelta(days=1)
        prev_start_dt, _ = get_date_range_vn(prev_start_d.strftime("%Y-%m-%d"))
        _, prev_end_dt = get_date_range_vn(prev_end_d.strftime("%Y-%m-%d"))
        period_label = f"30 ngày qua ({cur_start_d.strftime('%d/%m')} - {cur_end_d.strftime('%d/%m')})"
        previous_period_label = "so với 30 ngày trước"
    elif time_range == "custom" and start_date and end_date:
        try:
            cur_start_d = datetime.strptime(start_date.strip(), "%Y-%m-%d").date()
            cur_end_d = datetime.strptime(end_date.strip(), "%Y-%m-%d").date()
            diff_days = (cur_end_d - cur_start_d).days + 1
            prev_start_d = cur_start_d - timedelta(days=diff_days)
            prev_end_d = cur_start_d - timedelta(days=1)
            prev_start_dt, _ = get_date_range_vn(prev_start_d.strftime("%Y-%m-%d"))
            _, prev_end_dt = get_date_range_vn(prev_end_d.strftime("%Y-%m-%d"))
            period_label = f"Tùy chọn ({cur_start_d.strftime('%d/%m')} - {cur_end_d.strftime('%d/%m')})"
            previous_period_label = f"so với {diff_days} ngày trước đó"
        except Exception:
            yesterday_vn = today_vn - timedelta(days=1)
            prev_start_dt, prev_end_dt = get_date_range_vn(yesterday_vn.strftime("%Y-%m-%d"))
            period_label = "Hôm nay"
            previous_period_label = "so với hôm qua"
    else:  # "today"
        yesterday_vn = today_vn - timedelta(days=1)
        prev_start_dt, prev_end_dt = get_date_range_vn(yesterday_vn.strftime("%Y-%m-%d"))
        period_label = "Hôm nay"
        previous_period_label = "so với hôm qua"

    # 1. Query Current Period Orders
    cur_query = db.query(Order).filter(
        Order.created_at >= cur_start_dt,
        Order.created_at < cur_end_dt,
        Order.status == "COMPLETED"
    )
    if target_branch:
        cur_query = cur_query.filter(Order.branch_id == target_branch)
    current_orders = cur_query.all()

    today_revenue = sum(o.total_amount for o in current_orders)
    today_orders_count = len(current_orders)

    # 2. Query Previous Period Orders for Comparison
    prev_query = db.query(Order).filter(
        Order.created_at >= prev_start_dt,
        Order.created_at < prev_end_dt,
        Order.status == "COMPLETED"
    )
    if target_branch:
        prev_query = prev_query.filter(Order.branch_id == target_branch)
    prev_orders = prev_query.all()

    yesterday_revenue = sum(o.total_amount for o in prev_orders)
    yesterday_orders_count = len(prev_orders)

    if yesterday_revenue > 0:
        revenue_growth = round(((today_revenue - yesterday_revenue) / yesterday_revenue) * 100, 1)
    else:
        revenue_growth = 0.0

    if yesterday_orders_count > 0:
        orders_growth = round(((today_orders_count - yesterday_orders_count) / yesterday_orders_count) * 100, 1)
    else:
        orders_growth = 0.0

    average_order_value = (today_revenue // today_orders_count) if today_orders_count > 0 else 0

    # 3. Low stock details
    all_products = db.query(Product).filter(Product.is_deleted == False).all()
    total_products_count = len(all_products)

    threshold_setting = db.query(SystemSetting).filter(SystemSetting.key == "low_stock_threshold").first()
    try:
        low_stock_threshold = int(threshold_setting.value) if threshold_setting and int(threshold_setting.value) > 0 else 5
    except (ValueError, TypeError):
        low_stock_threshold = 5

    low_stock_details: List[LowStockDetailItem] = []
    for p in all_products:
        if p.stock <= low_stock_threshold:
            low_stock_details.append(LowStockDetailItem(
                id=p.id,
                name=p.name,
                category=p.category,
                stock=p.stock,
                threshold=low_stock_threshold,
                status="Hết hàng" if p.stock == 0 else "Sắp hết",
                image=p.image
            ))
    low_stock_details.sort(key=lambda x: x.stock)
    low_stock_count = len(low_stock_details)

    # 4. Sales Over Time Chart (recentSalesChart)
    recent_sales_chart: List[HourlySaleItem] = []
    if time_range == "today":
        time_slots = [
            ("07:00 - 09:00", 7, 9),
            ("09:00 - 11:00", 9, 11),
            ("11:00 - 13:00", 11, 13),
            ("13:00 - 15:00", 13, 15),
            ("15:00 - 17:00", 15, 17),
            ("17:00 - 19:00", 17, 19),
            ("19:00 - 21:00", 19, 21),
            ("21:00 - 23:00", 21, 23),
        ]
        for label, start_h, end_h in time_slots:
            slot_orders = [
                o for o in current_orders
                if start_h <= o.created_at.astimezone(VN_TZ).hour < end_h
            ]
            slot_rev = sum(o.total_amount for o in slot_orders)
            slot_cnt = len(slot_orders)
            recent_sales_chart.append(HourlySaleItem(
                time=label,
                revenue=slot_rev,
                orders=slot_cnt
            ))
    else:
        # Daily points in VN timezone
        s_date = cur_start_dt.astimezone(VN_TZ).date()
        e_date = (cur_end_dt - timedelta(seconds=1)).astimezone(VN_TZ).date()
        day_count = (e_date - s_date).days + 1
        for i in range(day_count):
            d = s_date + timedelta(days=i)
            day_orders = [o for o in current_orders if o.created_at.astimezone(VN_TZ).date() == d]
            d_rev = sum(o.total_amount for o in day_orders)
            d_cnt = len(day_orders)
            recent_sales_chart.append(HourlySaleItem(
                time=d.strftime("%d/%m"),
                revenue=d_rev,
                orders=d_cnt
            ))

    # 5. Product sales map
    current_order_ids = [o.id for o in current_orders]
    product_sales_map: Dict[str, Dict[str, int]] = {}

    if current_order_ids:
        cur_items = db.query(OrderItem).filter(OrderItem.order_id.in_(current_order_ids)).all()
        for item in cur_items:
            if item.product_id not in product_sales_map:
                product_sales_map[item.product_id] = {
                    "sold_count": 0,
                    "revenue": 0
                }
            product_sales_map[item.product_id]["sold_count"] += item.quantity
            product_sales_map[item.product_id]["revenue"] += item.subtotal

    # Top 5 Best Selling Products
    sorted_top = sorted(
        product_sales_map.items(),
        key=lambda x: x[1]["sold_count"],
        reverse=True
    )[:5]

    top_selling_products: List[TopSellingProductItem] = []
    for pid, s in sorted_top:
        prod = next((p for p in all_products if p.id == pid), None)
        if prod:
            top_selling_products.append(TopSellingProductItem(
                id=prod.id,
                name=prod.name,
                category=prod.category,
                sold_count=s["sold_count"],
                revenue=s["revenue"],
                image=prod.image
            ))

    if not top_selling_products and all_products:
        for p in all_products[:5]:
            top_selling_products.append(TopSellingProductItem(
                id=p.id,
                name=p.name,
                category=p.category,
                sold_count=0,
                revenue=0,
                image=p.image
            ))

    # 6. Slow Selling Products
    product_performance_list = []
    for p in all_products:
        sold = product_sales_map.get(p.id, {}).get("sold_count", 0)
        rev = product_sales_map.get(p.id, {}).get("revenue", 0)
        product_performance_list.append({
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "sold_count": sold,
            "revenue": rev,
            "stock": p.stock,
            "image": p.image
        })

    product_performance_list.sort(key=lambda x: (x["sold_count"], -x["stock"]))
    slow_selling_products = [
        SlowSellingProductItem(**item)
        for item in product_performance_list[:5]
    ]

    # 7. Payment Methods Breakdown
    payment_methods_map = {
        "QR_TRANSFER": {"label": "Chuyển khoản QR", "count": 0, "revenue": 0},
        "CASH": {"label": "Tiền mặt", "count": 0, "revenue": 0},
        "CARD": {"label": "Quẹt thẻ POS", "count": 0, "revenue": 0},
    }
    for o in current_orders:
        method = o.payment_method or "CASH"
        if method not in payment_methods_map:
            payment_methods_map[method] = {"label": method, "count": 0, "revenue": 0}
        payment_methods_map[method]["count"] += 1
        payment_methods_map[method]["revenue"] += o.total_amount

    payment_methods: List[PaymentMethodStat] = []
    for method_key, data in payment_methods_map.items():
        pct = round((data["revenue"] / today_revenue * 100), 1) if today_revenue > 0 else 0.0
        payment_methods.append(PaymentMethodStat(
            method=method_key,
            method_label=data["label"],
            count=data["count"],
            revenue=data["revenue"],
            percentage=pct
        ))

    # 8. Category Breakdown
    category_map: Dict[str, Dict[str, int]] = {}
    if current_order_ids:
        cur_items = db.query(OrderItem).filter(OrderItem.order_id.in_(current_order_ids)).all()
        for it in cur_items:
            prod = next((p for p in all_products if p.id == it.product_id), None)
            cat_name = prod.category if prod else "Khác"
            if cat_name not in category_map:
                category_map[cat_name] = {"revenue": 0, "sold_count": 0}
            category_map[cat_name]["revenue"] += it.subtotal
            category_map[cat_name]["sold_count"] += it.quantity

    standard_cats = ["Bánh Mì Nghệ Nhân (Artisan)", "Bánh Mì Ngọt & Pastry", "Bánh Kem & Sinh Nhật", "Cà Phê & Đồ Uống"]
    for c in standard_cats:
        if c not in category_map:
            category_map[c] = {"revenue": 0, "sold_count": 0}

    category_sales: List[CategoryStat] = []
    total_cat_rev = sum(c["revenue"] for c in category_map.values())
    for cat_name, data in category_map.items():
        pct = round((data["revenue"] / total_cat_rev * 100), 1) if total_cat_rev > 0 else 0.0
        category_sales.append(CategoryStat(
            category=cat_name,
            revenue=data["revenue"],
            sold_count=data["sold_count"],
            percentage=pct
        ))
    category_sales.sort(key=lambda x: x.revenue, reverse=True)

    # 9. Staff Leaderboard
    staff_map: Dict[str, Dict[str, any]] = {}
    all_staff = db.query(User).all()
    for st in all_staff:
        staff_map[st.id] = {
            "staff_id": st.id,
            "staff_name": st.full_name,
            "orders_count": 0,
            "revenue": 0,
        }

    for o in current_orders:
        s_id = o.staff_id or "unknown"
        if s_id not in staff_map:
            staff_map[s_id] = {
                "staff_id": s_id,
                "staff_name": o.staff_name or "Nhân viên",
                "orders_count": 0,
                "revenue": 0,
            }
        staff_map[s_id]["orders_count"] += 1
        staff_map[s_id]["revenue"] += o.total_amount

    staff_performances: List[StaffPerformanceStat] = []
    for s_data in staff_map.values():
        cnt = s_data["orders_count"]
        rev = s_data["revenue"]
        aov = (rev // cnt) if cnt > 0 else 0
        staff_performances.append(StaffPerformanceStat(
            staff_id=s_data["staff_id"],
            staff_name=s_data["staff_name"],
            orders_count=cnt,
            revenue=rev,
            average_order_value=aov
        ))
    staff_performances.sort(key=lambda x: x.revenue, reverse=True)

    return DashboardStatsResponse(
        period_label=period_label,
        previous_period_label=previous_period_label,
        today_revenue=today_revenue,
        yesterday_revenue=yesterday_revenue,
        revenue_growth=revenue_growth,
        today_orders_count=today_orders_count,
        yesterday_orders_count=yesterday_orders_count,
        orders_growth=orders_growth,
        average_order_value=average_order_value,
        total_products_count=total_products_count,
        low_stock_count=low_stock_count,
        recent_sales_chart=recent_sales_chart,
        top_selling_products=top_selling_products,
        slow_selling_products=slow_selling_products,
        payment_methods=payment_methods,
        category_sales=category_sales,
        staff_performances=staff_performances,
        low_stock_details=low_stock_details
    )
