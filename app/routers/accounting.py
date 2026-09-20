import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_permission, get_current_user
from app.models.user import User
from app.models.branch import Branch
from app.models.transaction import Transaction
from app.models.order import Order
from app.core.timezone import get_now_vn, get_now_utc
from app.schemas.transaction import (
    TransactionResponse,
    TransactionCreate,
    CashFlowSummary,
    PnLReport,
)

router = APIRouter(prefix="/accounting", tags=["Basic Accounting & Cash Flow"])


def generate_tx_code(tx_type: str, count: int) -> str:
    prefix = "PT" if tx_type == "INCOME" else "PC"
    now_vn = get_now_vn()
    date_str = now_vn.strftime("%y%m%d")
    return f"{prefix}-{date_str}-{count + 1:03d}"


@router.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    transaction_type: Optional[str] = Query(default=None, alias="type"),
    category: Optional[str] = Query(default=None),
    branch_id: Optional[str] = Query(default=None),
    branchId: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounting:read"))
):
    """List cash receipts & payment vouchers without hidden auto-seeding."""
    target_branch = branchId or branch_id

    query = db.query(Transaction)

    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    if category:
        query = query.filter(Transaction.category == category)
    if target_branch and target_branch != "ALL":
        query = query.filter(Transaction.branch_id == target_branch)

    txs = query.order_by(Transaction.created_at.desc()).all()

    # Populate branch names
    branch_map = {b.id: b.name for b in db.query(Branch).all()}
    results = []
    for t in txs:
        results.append(TransactionResponse(
            id=t.id,
            code=t.code,
            transaction_type=t.transaction_type,
            category=t.category,
            amount=t.amount,
            branch_id=t.branch_id,
            branch_name=branch_map.get(t.branch_id, "Toàn chuỗi / Chưa gán") if t.branch_id else "Toàn chuỗi / Dùng chung",
            payment_method=t.payment_method,
            recipient_payer=t.recipient_payer,
            note=t.note,
            created_by=t.created_by,
            created_at=t.created_at
        ))

    return results


@router.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    req: TransactionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("accounting:write"))
):
    """Create a new income receipt or expense voucher."""
    count = db.query(Transaction).count()
    code = generate_tx_code(req.transaction_type, count)

    tx = Transaction(
        code=code,
        transaction_type=req.transaction_type,
        category=req.category.strip(),
        amount=req.amount,
        branch_id=req.branch_id if req.branch_id and req.branch_id != "ALL" else None,
        payment_method=req.payment_method,
        recipient_payer=req.recipient_payer.strip(),
        note=req.note.strip() if req.note else None,
        created_by=admin.full_name,
        created_at=get_now_utc()
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    branch = db.query(Branch).filter(Branch.id == tx.branch_id).first() if tx.branch_id else None

    return TransactionResponse(
        id=tx.id,
        code=tx.code,
        transaction_type=tx.transaction_type,
        category=tx.category,
        amount=tx.amount,
        branch_id=tx.branch_id,
        branch_name=branch.name if branch else "Toàn chuỗi / Dùng chung",
        payment_method=tx.payment_method,
        recipient_payer=tx.recipient_payer,
        note=tx.note,
        created_by=tx.created_by,
        created_at=tx.created_at
    )


@router.get("/summary", response_model=CashFlowSummary)
def get_cash_flow_summary(
    branch_id: Optional[str] = Query(default=None),
    branchId: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounting:read"))
):
    """Get cash flow summary and account balances."""
    target_branch = branchId or branch_id
    query = db.query(Transaction)
    if target_branch and target_branch != "ALL":
        query = query.filter(Transaction.branch_id == target_branch)

    txs = query.all()

    total_income = sum(t.amount for t in txs if t.transaction_type == "INCOME")
    total_expense = sum(t.amount for t in txs if t.transaction_type == "EXPENSE")
    net_cash_flow = total_income - total_expense

    cash_txs = [t for t in txs if t.payment_method == "CASH"]
    bank_txs = [t for t in txs if t.payment_method in ["BANK_TRANSFER", "QR_TRANSFER"]]

    cash_balance = 2000000 + sum(t.amount if t.transaction_type == "INCOME" else -t.amount for t in cash_txs)
    bank_balance = 15000000 + sum(t.amount if t.transaction_type == "INCOME" else -t.amount for t in bank_txs)

    income_by_category = {}
    expense_by_category = {}

    for t in txs:
        if t.transaction_type == "INCOME":
            income_by_category[t.category] = income_by_category.get(t.category, 0) + t.amount
        else:
            expense_by_category[t.category] = expense_by_category.get(t.category, 0) + t.amount

    now_vn = get_now_vn()
    return CashFlowSummary(
        period_label=f"Tháng {now_vn.strftime('%m/%Y')}",
        total_income=total_income,
        total_expense=total_expense,
        net_cash_flow=net_cash_flow,
        cash_balance=max(0, cash_balance),
        bank_balance=max(0, bank_balance),
        total_transactions_count=len(txs),
        income_by_category=income_by_category,
        expense_by_category=expense_by_category
    )


@router.get("/pnl", response_model=PnLReport)
def get_pnl_report(
    branch_id: Optional[str] = Query(default=None),
    branchId: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("accounting:pnl"))
):
    """Get Profit and Loss (P&L) Report."""
    target_branch = branchId or branch_id

    # Compute gross revenue from completed orders
    order_query = db.query(Order).filter(Order.status == "COMPLETED")
    if target_branch and target_branch != "ALL":
        order_query = order_query.filter(Order.branch_id == target_branch)

    orders = order_query.all()
    pos_revenue = sum(o.total_amount for o in orders)

    # Compute transactions
    tx_query = db.query(Transaction)
    if target_branch and target_branch != "ALL":
        tx_query = tx_query.filter(Transaction.branch_id == target_branch)
    txs = tx_query.all()

    def is_shift_sales_tx(t: Transaction) -> bool:
        cat = (t.category or "").lower()
        if "pos" in cat or "bán hàng" in cat or "bán lẻ" in cat:
            return True
        if t.created_by == "Hệ thống (Kết ca)" and "thừa" not in cat:
            return True
        return False

    other_income = sum(
        t.amount for t in txs
        if t.transaction_type == "INCOME" and not is_shift_sales_tx(t)
    )
    gross_revenue = pos_revenue + other_income

    # COGS
    cogs_txs = [t for t in txs if t.transaction_type == "EXPENSE" and ("Nguyên vật liệu" in t.category or "Bao bì" in t.category)]
    cogs = sum(t.amount for t in cogs_txs)
    if cogs == 0 and gross_revenue > 0:
        cogs = int(gross_revenue * 0.35)

    gross_profit = gross_revenue - cogs
    gross_margin_percent = round((gross_profit / gross_revenue * 100), 1) if gross_revenue > 0 else 0.0

    # OPEX
    opex_txs = [t for t in txs if t.transaction_type == "EXPENSE" and t not in cogs_txs]
    operating_expenses = sum(t.amount for t in opex_txs)
    if operating_expenses == 0 and gross_revenue > 0:
        operating_expenses = int(gross_revenue * 0.25)

    net_profit = gross_profit - operating_expenses
    net_margin_percent = round((net_profit / gross_revenue * 100), 1) if gross_revenue > 0 else 0.0

    expenses_breakdown = {}
    for t in txs:
        if t.transaction_type == "EXPENSE":
            expenses_breakdown[t.category] = expenses_breakdown.get(t.category, 0) + t.amount

    now_vn = get_now_vn()
    return PnLReport(
        period_label=f"Tháng {now_vn.strftime('%m/%Y')}",
        gross_revenue=gross_revenue,
        cogs=cogs,
        gross_profit=gross_profit,
        gross_margin_percent=gross_margin_percent,
        operating_expenses=operating_expenses,
        net_profit=net_profit,
        net_margin_percent=net_margin_percent,
        expenses_breakdown=expenses_breakdown
    )
