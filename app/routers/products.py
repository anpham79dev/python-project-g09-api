from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.dependencies import get_db, require_permission
from app.models.user import User
from app.models.product import Product
from app.models.stock import StockItem
from app.models.branch import Warehouse
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=List[ProductResponse])
def get_products(
    search: Optional[str] = Query(None, description="Search by product name or category"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by stock status"),
    db: Session = Depends(get_db)
):
    """List active products with optional search and filtering."""
    query = db.query(Product).filter(Product.is_deleted == False)

    if category and category != "Tất cả":
        query = query.filter(Product.category == category)

    if search:
        search_term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                Product.name.ilike(search_term),
                Product.category.ilike(search_term),
                Product.description.ilike(search_term)
            )
        )

    # Dynamic status filter based on stock
    if status_filter:
        if status_filter == "out_of_stock":
            query = query.filter(Product.stock == 0)
        elif status_filter == "low_stock":
            query = query.filter(Product.stock > 0, Product.stock <= 5)
        elif status_filter == "in_stock":
            query = query.filter(Product.stock > 5)

    products = query.order_by(Product.created_at.desc()).all()
    return products


@router.get("/{id}", response_model=ProductResponse)
def get_product_by_id(id: str, db: Session = Depends(get_db)):
    """Get single product details."""
    product = db.query(Product).filter(
        Product.id == id,
        Product.is_deleted == False
    ).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm có mã '{id}'!"
        )
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("products:write"))
):
    """Create a new product and sync to warehouse stock (Admin only)."""
    product = Product(
        name=product_in.name.strip(),
        category=product_in.category.strip(),
        price=product_in.price,
        stock=product_in.stock,
        description=product_in.description.strip() if product_in.description else None,
        image=product_in.image.strip(),
    )
    db.add(product)
    db.flush()

    # Sync to specific warehouse or all retail warehouses
    if product_in.warehouse_id:
        target_wh = db.query(Warehouse).filter(Warehouse.id == product_in.warehouse_id).first()
        if target_wh:
            stk = StockItem(
                warehouse_id=target_wh.id,
                product_id=product.id,
                quantity=product_in.stock,
                min_alert_stock=5
            )
            db.add(stk)
    else:
        # If no warehouse specified, seed in all retail warehouses
        retail_warehouses = db.query(Warehouse).filter(Warehouse.warehouse_type == "RETAIL").all()
        for wh in retail_warehouses:
            stk = StockItem(
                warehouse_id=wh.id,
                product_id=product.id,
                quantity=product_in.stock,
                min_alert_stock=5
            )
            db.add(stk)

    db.commit()
    db.refresh(product)
    return product


@router.put("/{id}", response_model=ProductResponse)
def update_product(
    id: str,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("products:write"))
):
    """Update an existing product (Admin only)."""
    product = db.query(Product).filter(
        Product.id == id,
        Product.is_deleted == False
    ).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm '{id}' để cập nhật!"
        )

    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if isinstance(value, str):
                setattr(product, field, value.strip())
            else:
                setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{id}")
def delete_product(
    id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("products:write"))
):
    """Soft delete a product to preserve order history integrity (Admin only)."""
    product = db.query(Product).filter(
        Product.id == id,
        Product.is_deleted == False
    ).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm '{id}' để xóa!"
        )

    product.is_deleted = True
    db.commit()
    return {"success": True, "message": f"Đã xóa sản phẩm '{product.name}' thành công!"}
