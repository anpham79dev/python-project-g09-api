from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.dependencies import get_db, get_current_user_optional
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.schemas.order import OrderCreate, OrderResponse

router = APIRouter(prefix="/orders", tags=["Orders"])


def generate_next_order_code(db: Session, now: datetime) -> str:
    """Generate sequential order code format HD-YYMMDD-XX."""
    date_prefix = now.strftime("%y%m%d")  # e.g. 260816
    code_pattern = f"HD-{date_prefix}-%"

    # Count orders created on this date
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
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    date_str: Optional[str] = Query(None, alias="date", description="Filter by date YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """List orders with optional search and filters (SARGable queries)."""
    query = db.query(Order)

    if status_filter and status_filter != "ALL":
        query = query.filter(Order.status == status_filter)

    if staff_id:
        query = query.filter(Order.staff_id == staff_id)

    if branch_id and branch_id != "ALL":
        query = query.filter(Order.branch_id == branch_id)

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
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            end_dt = start_dt + timedelta(days=1)
            query = query.filter(Order.created_at >= start_dt, Order.created_at < end_dt)
        except ValueError:
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
    """
    Atomic POS checkout transaction:
    1. Lock products and check stock availability.
    2. Deduct product stock.
    3. Generate sequential order code.
    4. Save Order and OrderItem records.
    """
    if not order_in.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đơn hàng phải có ít nhất 1 sản phẩm!"
        )

    now = datetime.now(timezone.utc)
    order_code = generate_next_order_code(db, now)

    # Determine staff info
    staff_id = current_user.id if current_user else (order_in.staff_id or "user-default")
    staff_name = current_user.full_name if current_user else (order_in.staff_name or "Thu Ngân")

    try:
        # 1. Lock and validate each product
        order_items_to_create = []
        for item in order_in.items:
            # Query product with row lock for update
            product = db.query(Product).filter(
                Product.id == item.product_id,
                Product.is_deleted == False
            ).with_for_update().first()

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sản phẩm '{item.product_name}' (ID: {item.product_id}) không tồn tại hoặc đã ngừng bán!"
                )

            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sản phẩm '{product.name}' không đủ số lượng tồn kho (Chỉ còn {product.stock}, yêu cầu {item.quantity})!"
                )

            # Deduct stock
            product.stock -= item.quantity

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
            branch_id=order_in.branch_id or "branch-001",
            warehouse_id=order_in.warehouse_id or "wh-001",
            staff_id=staff_id,
            staff_name=staff_name,
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
