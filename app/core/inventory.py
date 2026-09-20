from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.product import Product
from app.models.stock import StockItem


def recalc_product_stock(db: Session, product_id: str) -> int:
    """
    Calculate SUM(StockItem.quantity) for a product across all warehouses
    and synchronize Product.stock so that Product.stock is always a cached sum.
    """
    total_qty = db.query(func.coalesce(func.sum(StockItem.quantity), 0))\
        .filter(StockItem.product_id == product_id)\
        .scalar()
    total_qty = int(total_qty or 0)

    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        product.stock = total_qty
        db.flush()

    return total_qty
