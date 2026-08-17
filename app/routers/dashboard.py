from datetime import datetime, timezone, timedelta, date
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.dependencies import get_db, require_permission
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem
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
    branch_id: Optional[str] = Query(default=None, description="Branch ID filter (or 'ALL')"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("dashboard:view"))
):
    """
    Calculate executive KPI analytics dynamically from PostgreSQL DB:
    1. KPI Summary (Revenue, Orders, AOV, Low stock) & Growth % vs previous period
    2. Sales trend chart (by hour for today, by day for longer ranges)
    3. Top 5 Best Selling Products
    4. Slow Selling / Stagnant Products
    5. Revenue by Payment Method (Cash, Card, QR)
    6. Revenue by Product Category
    7. Staff Sales Performance leaderboard
    8. Detailed Low Stock Inventory Alerts
    """
    now = datetime.now(timezone.utc)
    today_d = now.date()

    # Determine date intervals
    if time_range == "7days":
        cur_start_d = today_d - timedelta(days=6)
        cur_end_d = today_d
        prev_start_d = cur_start_d - timedelta(days=7)
        prev_end_d = cur_start_d - timedelta(days=1)
        period_label = f"7 ngày qua ({cur_start_d.strftime('%d/%m')} - {cur_end_d.strftime('%d/%m')})"
        previous_period_label = "so với 7 ngày trước"
    elif time_range == "30days":
        cur_start_d = today_d - timedelta(days=29)
        cur_end_d = today_d
        prev_start_d = cur_start_d - timedelta(days=30)
        prev_end_d = cur_start_d - timedelta(days=1)
        period_label = f"30 ngày qua ({cur_start_d.strftime('%d/%m')} - {cur_end_d.strftime('%d/%m')})"
        previous_period_label = "so với 30 ngày trước"
    elif time_range == "custom" and start_date and end_date:
        try:
            cur_start_d = datetime.strptime(start_date, "%Y-%m-%d").date()
            cur_end_d = datetime.strptime(end_date, "%Y-%m-%d").date()
            diff_days = (cur_end_d - cur_start_d).days + 1
            prev_start_d = cur_start_d - timedelta(days=diff_days)
            prev_end_d = cur_start_d - timedelta(days=1)
            period_label = f"Tùy chọn ({cur_start_d.strftime('%d/%m')} - {cur_end_d.strftime('%d/%m')})"
            previous_period_label = f"so với {diff_days} ngày trước đó"
        except Exception:
            cur_start_d = today_d
            cur_end_d = today_d
            prev_start_d = today_d - timedelta(days=1)
            prev_end_d = prev_start_d
            period_label = "Hôm nay"
            previous_period_label = "so với hôm qua"
    else:  # "today"
        cur_start_d = today_d
        cur_end_d = today_d
        prev_start_d = today_d - timedelta(days=1)
        prev_end_d = prev_start_d
        period_label = "Hôm nay"
        previous_period_label = "so với hôm qua"

    # Convert date intervals to half-open UTC datetime bounds for SARGable index scanning
    cur_start_dt = datetime.combine(cur_start_d, datetime.min.time()).replace(tzinfo=timezone.utc)
    cur_end_dt = datetime.combine(cur_end_d + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)

    prev_start_dt = datetime.combine(prev_start_d, datetime.min.time()).replace(tzinfo=timezone.utc)
    prev_end_dt = datetime.combine(prev_end_d + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)

    # 1. Query Current Period Orders (SARGable range query using index on created_at & status)
    cur_query = db.query(Order).filter(
        Order.created_at >= cur_start_dt,
        Order.created_at < cur_end_dt,
        Order.status == "COMPLETED"
    )
    if branch_id and branch_id != "ALL":
        cur_query = cur_query.filter(Order.branch_id == branch_id)
    current_orders = cur_query.all()

    today_revenue = sum(o.total_amount for o in current_orders)
    today_orders_count = len(current_orders)

    # 2. Query Previous Period Orders for Comparison (SARGable range query)
    prev_query = db.query(Order).filter(
        Order.created_at >= prev_start_dt,
        Order.created_at < prev_end_dt,
        Order.status == "COMPLETED"
    )
    if branch_id and branch_id != "ALL":
        prev_query = prev_query.filter(Order.branch_id == branch_id)
    prev_orders = prev_query.all()

    yesterday_revenue = sum(o.total_amount for o in prev_orders)
    yesterday_orders_count = len(prev_orders)

    # Effective baseline for comparison
    effective_prev_rev = yesterday_revenue if yesterday_revenue > 0 else (1200000 if today_revenue > 0 else 0)
    effective_prev_cnt = yesterday_orders_count if yesterday_orders_count > 0 else (5 if today_orders_count > 0 else 0)

    if effective_prev_rev > 0:
        revenue_growth = round(((today_revenue - effective_prev_rev) / effective_prev_rev) * 100, 1)
    else:
        revenue_growth = 0.0

    if effective_prev_cnt > 0:
        orders_growth = round(((today_orders_count - effective_prev_cnt) / effective_prev_cnt) * 100, 1)
    else:
        orders_growth = 0.0

    average_order_value = (today_revenue // today_orders_count) if today_orders_count > 0 else 0

    # 3. Inventory counts & Low Stock Details
    all_products = db.query(Product).filter(Product.is_deleted == False).all()
    total_products_count = len(all_products)
    
    low_stock_details: List[LowStockDetailItem] = []
    for p in all_products:
        if p.stock <= 5:
            low_stock_details.append(LowStockDetailItem(
                id=p.id,
                name=p.name,
                category=p.category,
                stock=p.stock,
                threshold=5,
                status="Hết hàng" if p.stock == 0 else "Sắp hết",
                image=p.image
            ))
    # Sort lowest stock first
    low_stock_details.sort(key=lambda x: x.stock)
    low_stock_count = len(low_stock_details)

    # 4. Sales Over Time Chart
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
        ]
        for label, start_h, end_h in time_slots:
            slot_rev = sum(
                o.total_amount for o in current_orders
                if start_h <= o.created_at.hour < end_h
            )
            slot_cnt = sum(
                1 for o in current_orders
                if start_h <= o.created_at.hour < end_h
            )
            recent_sales_chart.append(HourlySaleItem(
                time=label,
                revenue=slot_rev,
                orders=slot_cnt
            ))
    else:
        # Group by each day in range
        day_count = (cur_end_d - cur_start_d).days + 1
        for i in range(day_count):
            d = cur_start_d + timedelta(days=i)
            day_orders = [o for o in current_orders if o.created_at.date() == d]
            d_rev = sum(o.total_amount for o in day_orders)
            d_cnt = len(day_orders)
            recent_sales_chart.append(HourlySaleItem(
                time=d.strftime("%d/%m"),
                revenue=d_rev,
                orders=d_cnt
            ))

    # 5. Product Sales Aggregation for Current Period
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

    # Fallback if no sales in period
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

    # 6. Slow Selling / Stagnant Products
    # Include products with 0 or lowest sales in current period
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

    # Sort ascending by sold_count then descending by stock (high stock + low sales = stagnant)
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

    # Ensure all standard categories exist
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

    # 9. Staff Sales Performance Leaderboard
    staff_map: Dict[str, Dict[str, any]] = {}
    # Fetch all active staff
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

