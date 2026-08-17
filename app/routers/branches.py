import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_permission, get_current_user
from app.models.user import User
from app.models.product import Product
from app.models.branch import Branch, Warehouse
from app.models.stock import StockItem
from app.schemas.branch import (
    BranchResponse,
    BranchCreate,
    BranchUpdate,
    WarehouseResponse,
    WarehouseCreate,
    StockItemResponse,
    UpdateStockRequest,
)

router = APIRouter(prefix="/branches", tags=["Multi-Branch & Warehouses"])


@router.get("", response_model=List[BranchResponse])
def get_branches(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all store branches."""
    query = db.query(Branch)
    if status:
        query = query.filter(Branch.status == status)
    branches = query.order_by(Branch.created_at.asc()).all()

    # If no branches exist, seed default branches
    if not branches:
        b1 = Branch(
            id="branch-001",
            code="CN-Q1",
            name="Artisan Bakery - Chi Nhánh Quận 1 (Trụ Sở)",
            address="123 Đường Đồng Khởi, Bến Nghé, Quận 1, TP.HCM",
            phone="0901 234 567",
            manager_name="Nguyễn Quản Trị",
            status="ACTIVE"
        )
        b2 = Branch(
            id="branch-002",
            code="CN-TD",
            name="Artisan Bakery - Chi Nhánh Thảo Điền",
            address="45 Đường Xuân Thủy, Thảo Điền, TP. Thủ Đức, TP.HCM",
            phone="0909 888 777",
            manager_name="Lê Thu Hà",
            status="ACTIVE"
        )
        db.add_all([b1, b2])
        db.flush()

        # Seed Retail Warehouses
        w1 = Warehouse(id="wh-001", branch_id=b1.id, code="KHO-Q1-POS", name="Kho Quầy Bán Lẻ Q1", warehouse_type="RETAIL")
        w2 = Warehouse(id="wh-002", branch_id=b1.id, code="KHO-Q1-COLD", name="Kho Lạnh Bảo Quản Q1", warehouse_type="COLD_STORAGE")
        w3 = Warehouse(id="wh-003", branch_id=b2.id, code="KHO-TD-POS", name="Kho Quầy Bán Lẻ Thảo Điền", warehouse_type="RETAIL")
        db.add_all([w1, w2, w3])
        db.commit()

        branches = [b1, b2]

    return branches


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
def create_branch(
    req: BranchCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("branches:manage"))
):
    """Create a new branch and automatically generate its default retail warehouse."""
    existing = db.query(Branch).filter(Branch.code == req.code.upper().strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Mã chi nhánh '{req.code}' đã tồn tại!")

    branch = Branch(
        code=req.code.upper().strip(),
        name=req.name.strip(),
        address=req.address.strip(),
        phone=req.phone.strip(),
        manager_name=req.manager_name,
        status=req.status
    )
    db.add(branch)
    db.flush()

    # Automatically create default retail warehouse for the new branch
    wh = Warehouse(
        branch_id=branch.id,
        code=f"KHO-{branch.code}-POS",
        name=f"Kho Quầy Bán Lẻ - {branch.name}",
        warehouse_type="RETAIL",
        status="ACTIVE"
    )
    db.add(wh)
    db.commit()
    db.refresh(branch)

    return branch


@router.get("/stocks", response_model=List[StockItemResponse])
def get_warehouse_stocks(
    branch_id: Optional[str] = Query(default=None),
    warehouse_id: Optional[str] = Query(default=None),
    product_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get real-time stock levels per product across warehouses and branches."""
    query = db.query(StockItem).join(Warehouse, StockItem.warehouse_id == Warehouse.id).join(Product, StockItem.product_id == Product.id)

    if warehouse_id:
        query = query.filter(StockItem.warehouse_id == warehouse_id)
    if branch_id and branch_id != "ALL":
        query = query.filter(Warehouse.branch_id == branch_id)
    if product_id:
        query = query.filter(StockItem.product_id == product_id)

    stocks = query.all()
    
    # Auto seed stock item if empty
    if not stocks and not branch_id and not warehouse_id:
        wh1 = db.query(Warehouse).first()
        prod1 = db.query(Product).first()
        if wh1 and prod1:
            stk = StockItem(warehouse_id=wh1.id, product_id=prod1.id, quantity=15, min_alert_stock=5)
            db.add(stk)
            db.commit()
            stocks = [stk]

    results = []
    for s in stocks:
        wh = db.query(Warehouse).filter(Warehouse.id == s.warehouse_id).first()
        prod = db.query(Product).filter(Product.id == s.product_id).first()
        branch = db.query(Branch).filter(Branch.id == wh.branch_id).first() if wh and wh.branch_id else None
        
        calc_status = "in_stock" if s.quantity > s.min_alert_stock else "low_stock" if s.quantity > 0 else "out_of_stock"

        results.append(StockItemResponse(
            id=s.id,
            warehouse_id=s.warehouse_id,
            warehouse_name=wh.name if wh else "Kho mặc định",
            branch_id=branch.id if branch else None,
            branch_name=branch.name if branch else "Toàn chuỗi",
            product_id=s.product_id,
            product_name=prod.name if prod else "Sản phẩm",
            product_image=prod.image if prod else None,
            product_category=prod.category if prod else None,
            quantity=s.quantity,
            min_alert_stock=s.min_alert_stock,
            status=calc_status,
            updated_at=s.updated_at
        ))

    return results


@router.put("/stocks", response_model=StockItemResponse)
def update_warehouse_stock(
    req: UpdateStockRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("inventory:write"))
):
    """Adjust stock quantity for a product in a specific warehouse."""
    wh = db.query(Warehouse).filter(Warehouse.id == req.warehouse_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Không tìm thấy kho hàng!")

    prod = db.query(Product).filter(Product.id == req.product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm!")

    stock = db.query(StockItem).filter(
        StockItem.warehouse_id == req.warehouse_id,
        StockItem.product_id == req.product_id
    ).first()

    if not stock:
        stock = StockItem(
            warehouse_id=req.warehouse_id,
            product_id=req.product_id,
            quantity=req.quantity,
            min_alert_stock=req.min_alert_stock or 5
        )
        db.add(stock)
    else:
        stock.quantity = req.quantity
        if req.min_alert_stock is not None:
            stock.min_alert_stock = req.min_alert_stock

    db.commit()
    db.refresh(stock)

    branch = db.query(Branch).filter(Branch.id == wh.branch_id).first()
    calc_status = "in_stock" if stock.quantity > stock.min_alert_stock else "low_stock" if stock.quantity > 0 else "out_of_stock"

    return StockItemResponse(
        id=stock.id,
        warehouse_id=wh.id,
        warehouse_name=wh.name,
        branch_id=branch.id if branch else None,
        branch_name=branch.name if branch else None,
        product_id=prod.id,
        product_name=prod.name,
        product_image=prod.image,
        product_category=prod.category,
        quantity=stock.quantity,
        min_alert_stock=stock.min_alert_stock,
        status=calc_status,
        updated_at=stock.updated_at
    )


@router.put("/{branch_id}", response_model=BranchResponse)
def update_branch(
    branch_id: str,
    req: BranchUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("branches:manage"))
):
    """Update branch details."""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Không tìm thấy chi nhánh!")

    if req.name is not None: branch.name = req.name
    if req.address is not None: branch.address = req.address
    if req.phone is not None: branch.phone = req.phone
    if req.manager_name is not None: branch.manager_name = req.manager_name
    if req.status is not None: branch.status = req.status

    db.commit()
    db.refresh(branch)
    return branch
