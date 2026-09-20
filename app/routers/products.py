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
from app.core.inventory import recalc_product_stock

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=List[ProductResponse])
def get_products(
    search: Optional[str] = Query(None, description="Search by product name or category"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by stock status"),
    branch_id: Optional[str] = Query(None, description="Filter stock by branch"),
    branchId: Optional[str] = Query(None, description="Alias for branch_id"),
    warehouse_id: Optional[str] = Query(None, description="Filter stock by warehouse"),
    warehouseId: Optional[str] = Query(None, description="Alias for warehouse_id"),
    db: Session = Depends(get_db)
):
    """List active products with optional search and filtering.
    If branch_id or warehouse_id is specified, product stock is scoped to that warehouse.
    Otherwise, product stock represents the sum across all warehouses.
    """
    target_branch_id = branchId or branch_id
    target_warehouse_id = warehouseId or warehouse_id
    if target_branch_id == "ALL":
        target_branch_id = None
    if target_warehouse_id == "ALL":
        target_warehouse_id = None

    if target_branch_id and not target_warehouse_id:
        retail_wh = db.query(Warehouse).filter(
            Warehouse.branch_id == target_branch_id,
            Warehouse.warehouse_type == "RETAIL"
        ).first()
        if not retail_wh:
            retail_wh = db.query(Warehouse).filter(Warehouse.branch_id == target_branch_id).first()
        if retail_wh:
            target_warehouse_id = retail_wh.id

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

    # Scoped warehouse stock
    if target_warehouse_id:
        products = query.order_by(Product.created_at.desc()).all()
        stock_items = db.query(StockItem).filter(StockItem.warehouse_id == target_warehouse_id).all()
        stock_map = {item.product_id: item.quantity for item in stock_items}

        results = []
        for p in products:
            p_stock = stock_map.get(p.id, 0)
            if status_filter:
                if status_filter == "out_of_stock" and p_stock != 0:
                    continue
                elif status_filter == "low_stock" and not (0 < p_stock <= 5):
                    continue
                elif status_filter == "in_stock" and p_stock <= 5:
                    continue

            results.append(ProductResponse(
                id=p.id,
                name=p.name,
                category=p.category,
                price=p.price,
                stock=p_stock,
                description=p.description,
                image=p.image,
                created_at=p.created_at
            ))
        return results

    # Global total stock across all warehouses
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
def get_product_by_id(
    id: str,
    branch_id: Optional[str] = Query(None),
    branchId: Optional[str] = Query(None),
    warehouse_id: Optional[str] = Query(None),
    warehouseId: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get single product details, optionally scoped to branch or warehouse stock."""
    product = db.query(Product).filter(
        Product.id == id,
        Product.is_deleted == False
    ).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm có mã '{id}'!"
        )

    target_branch_id = branchId or branch_id
    target_warehouse_id = warehouseId or warehouse_id
    if target_branch_id == "ALL":
        target_branch_id = None
    if target_warehouse_id == "ALL":
        target_warehouse_id = None

    if target_branch_id and not target_warehouse_id:
        retail_wh = db.query(Warehouse).filter(
            Warehouse.branch_id == target_branch_id,
            Warehouse.warehouse_type == "RETAIL"
        ).first()
        if not retail_wh:
            retail_wh = db.query(Warehouse).filter(Warehouse.branch_id == target_branch_id).first()
        if retail_wh:
            target_warehouse_id = retail_wh.id

    if target_warehouse_id:
        stk = db.query(StockItem).filter(
            StockItem.warehouse_id == target_warehouse_id,
            StockItem.product_id == id
        ).first()
        p_stock = stk.quantity if stk else 0
        return ProductResponse(
            id=product.id,
            name=product.name,
            category=product.category,
            price=product.price,
            stock=p_stock,
            description=product.description,
            image=product.image,
            created_at=product.created_at
        )

    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("products:write"))
):
    """Create a new product and initialize stock items with 0 quantity (Admin only)."""
    product = Product(
        name=product_in.name.strip(),
        category=product_in.category.strip(),
        price=product_in.price,
        stock=0,  # Stock is NOT set directly from payload
        description=product_in.description.strip() if product_in.description else None,
        image=product_in.image.strip() if product_in.image else "",
    )
    db.add(product)
    db.flush()

    # Initialize StockItem for all warehouses with quantity=0
    warehouses = db.query(Warehouse).all()
    for wh in warehouses:
        stk = StockItem(
            warehouse_id=wh.id,
            product_id=product.id,
            quantity=0,
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
    """Update an existing product (Admin only). Direct stock modification is ignored."""
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
    update_data.pop("stock", None)
    update_data.pop("warehouse_id", None)
    update_data.pop("warehouseId", None)

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
