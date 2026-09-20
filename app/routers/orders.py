from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.dependencies import get_db, get_current_user_optional
from app.models.user import User
from app.models.product import Product
from app.models.stock import StockItem
from app.models.branch import Warehouse
from app.models.order import Order, OrderItem
from app.models.setting import SystemSetting
from app.models.shift import WorkShift
from app.core.inventory import recalc_product_stock
from app.core.timezone import get_now_utc, get_date_range_vn, VN_TZ
from app.schemas.order import OrderCreate, OrderResponse

router = APIRouter(prefix="/orders", tags=["Orders"])


def generate_next_order_code(db: Session, now: datetime) -> str:
    """Generate sequential order code format HD-YYMMDD-XX based on Vietnam timezone."""
    now_vn = now.astimezone(VN_TZ) if now.tzinfo else now.replace(tzinfo=timezone.utc).astimezone(VN_TZ)
    date_prefix = now_vn.strftime("%y%m%d")
    code_pattern = f"HD-{date_prefix}-%"

    count = db.query(func.count(Order.id)).filter(
        Order.code.like(code_pattern)
    ).scalar() or 0

    next_num = count + 1
    return f"HD-{date_prefix}-{next_num:02d}"


@router.get("", response_model=List[OrderResponse])
def get_orders(
    search: Optional[str] = Query(None, description="Search by code, customer name, staff name"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by order status"),
    staff_id: Optional[str] = Query(None, description="Filter by staff ID"),
    staffId: Optional[str] = Query(None, description="Alias for staff_id"),
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    branchId: Optional[str] = Query(None, description="Alias for branch_id"),
    date_str: Optional[str] = Query(None, alias="date", description="Filter by date YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """List orders with optional search and filters (SARGable queries)."""
    target_branch = branchId or branch_id
    target_staff = staffId or staff_id
    query = db.query(Order)

    if status_filter and status_filter != "ALL":
        query = query.filter(Order.status == status_filter)

    if target_staff:
        query = query.filter(Order.staff_id == target_staff)

    if target_branch and target_branch != "ALL":
        query = query.filter(Order.branch_id == target_branch)

    if search:
        search_term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                Order.code.ilike(search_term),
                Order.customer_name.ilike(search_term),
                Order.customer_phone.ilike(search_term),
                Order.staff_name.ilike(search_term)
            )
        )

    if date_str:
        try:
            start_utc, end_utc = get_date_range_vn(date_str)
            query = query.filter(Order.created_at >= start_utc, Order.created_at < end_utc)
        except Exception:
            pass

    orders = query.order_by(Order.created_at.desc()).all()
    return orders


@router.get("/{id}", response_model=OrderResponse)
def get_order_by_id(id: str, db: Session = Depends(get_db)):
    """Get single order detail by ID or order code."""
    order = db.query(Order).filter(
        or_(Order.id == id, Order.code == id)
    ).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy đơn hàng '{id}'!"
        )
    return order


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Atomic POS checkout transaction:
    1. Validate active OPEN shift for the seller.
    2. Lock StockItem in target warehouse and check availability.
    3. Deduct stock and sync product.stock.
    4. Save Order, OrderItem, and update shift live statistics.
    """
    if not order_in.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đơn hàng phải có ít nhất 1 sản phẩm!"
        )

    # Determine staff info
    active_staff_id = current_user.id if current_user else (order_in.staff_id or "user-002")
    active_staff_name = current_user.full_name if current_user else (order_in.staff_name or "Thu Ngân")

    # Check for active OPEN shift
    open_shift = db.query(WorkShift).filter(
        WorkShift.staff_id == active_staff_id,
        WorkShift.status == "OPEN"
    ).first()

    if not open_shift:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chưa có ca làm việc nào đang mở cho nhân viên này! Vui lòng mở ca trước khi tạo đơn hàng."
        )

    now = get_now_utc()
    order_code = generate_next_order_code(db, now)

    target_branch_id = order_in.branch_id or open_shift.branch_id or "branch-001"
    target_warehouse_id = order_in.warehouse_id
    if not target_warehouse_id:
        retail_wh = db.query(Warehouse).filter(
            Warehouse.branch_id == target_branch_id,
            Warehouse.warehouse_type == "RETAIL"
        ).first()
        target_warehouse_id = retail_wh.id if retail_wh else "wh-001"

    # Check allow_negative_stock setting
    neg_setting = db.query(SystemSetting).filter(SystemSetting.key == "allow_negative_stock").first()
    allow_negative_stock = (neg_setting.value.lower() == "true") if neg_setting else False

    try:
        # 1. Lock and validate each StockItem in target warehouse
        order_items_to_create = []
        for item in order_in.items:
            product = db.query(Product).filter(
                Product.id == item.product_id,
                Product.is_deleted == False
            ).first()

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sản phẩm '{item.product_name}' (ID: {item.product_id}) không tồn tại hoặc đã ngừng bán!"
                )

            # Lock StockItem row for this warehouse and product
            stock_item = db.query(StockItem).filter(
                StockItem.warehouse_id == target_warehouse_id,
                StockItem.product_id == item.product_id
            ).with_for_update().first()

            available_qty = stock_item.quantity if stock_item else 0
            if not allow_negative_stock and available_qty < item.quantity:
                wh_obj = db.query(Warehouse).filter(Warehouse.id == target_warehouse_id).first()
                wh_name = wh_obj.name if wh_obj else target_warehouse_id
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sản phẩm '{product.name}' tại kho '{wh_name}' không đủ số lượng tồn kho (Chỉ còn {available_qty}, yêu cầu {item.quantity})!"
                )

            # Deduct warehouse stock
            if stock_item:
                stock_item.quantity -= item.quantity
            else:
                stock_item = StockItem(
                    warehouse_id=target_warehouse_id,
                    product_id=item.product_id,
                    quantity=-item.quantity,
                    min_alert_stock=5
                )
                db.add(stock_item)

            # Synchronize product.stock
            recalc_product_stock(db, item.product_id)

            # Prepare order item
            order_item = OrderItem(
                product_id=product.id,
                product_name=product.name,
                price=item.price,
                quantity=item.quantity,
                subtotal=item.subtotal,
                image=item.image or product.image
            )
            order_items_to_create.append(order_item)

        # 2. Create Order
        new_order = Order(
            code=order_code,
            customer_name=order_in.customer_name or "Khách vãng lai",
            customer_phone=order_in.customer_phone,
            branch_id=target_branch_id,
            warehouse_id=target_warehouse_id,
            staff_id=active_staff_id,
            staff_name=active_staff_name,
            subtotal=order_in.subtotal,
            discount=order_in.discount,
            total_amount=order_in.total_amount,
            payment_method=order_in.payment_method,
            status=order_in.status,
            note=order_in.note,
            created_at=now,
            items=order_items_to_create
        )
        db.add(new_order)

        # 3. Update active shift live stats
        open_shift.orders_count += 1
        open_shift.total_revenue += order_in.total_amount
        if order_in.payment_method == "CASH":
            open_shift.cash_revenue += order_in.total_amount
            open_shift.expected_cash = open_shift.initial_cash + open_shift.cash_revenue
            open_shift.difference = open_shift.actual_cash - open_shift.expected_cash
        elif order_in.payment_method == "CARD":
            open_shift.card_revenue += order_in.total_amount
        elif order_in.payment_method == "QR_TRANSFER":
            open_shift.qr_revenue += order_in.total_amount

        db.commit()
        db.refresh(new_order)
        return new_order

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xử lý giao dịch thanh toán: {str(e)}"
        )
