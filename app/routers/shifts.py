from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user, require_permission
from app.models.user import User
from app.models.order import Order
from app.models.shift import WorkShift
from app.schemas.shift import (
    WorkShiftResponse,
    CloseShiftRequest,
    ShiftSummaryResponse
)

router = APIRouter(prefix="/shifts", tags=["Shift & Cash Management"])


def _parse_day_range(date_filter: Optional[str]):
    """Convert a 'YYYY-MM-DD' filter into a half-open UTC datetime range, or (None, None)."""
    if not date_filter:
        return None, None
    try:
        d = datetime.strptime(date_filter, "%Y-%m-%d").date()
    except ValueError:
        return None, None
    start_dt = datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc)
    return start_dt, start_dt + timedelta(days=1)


def _calculate_shift_live_stats(shift: WorkShift, db: Session) -> WorkShift:
    """Dynamically aggregate orders completed during the shift window."""
    if shift.status == "CLOSED":
        return shift

    # Query all completed orders created by this staff member since shift start_time
    orders = db.query(Order).filter(
        Order.staff_id == shift.staff_id,
        Order.created_at >= shift.start_time,
        Order.status == "COMPLETED"
    ).all()

    cash_rev = sum(o.total_amount for o in orders if (o.payment_method or "CASH") == "CASH")
    card_rev = sum(o.total_amount for o in orders if o.payment_method == "CARD")
    qr_rev = sum(o.total_amount for o in orders if o.payment_method == "QR_TRANSFER")
    tot_rev = sum(o.total_amount for o in orders)

    shift.cash_revenue = cash_rev
    shift.card_revenue = card_rev
    shift.qr_revenue = qr_rev
    shift.total_revenue = tot_rev
    shift.orders_count = len(orders)
    shift.expected_cash = shift.initial_cash + cash_rev
    shift.difference = shift.actual_cash - shift.expected_cash

    return shift


@router.get("/current", response_model=WorkShiftResponse)
def get_current_shift(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get or automatically initialize the currently open shift for the logged-in staff member.
    """
    # 1. Find existing OPEN shift for this user
    open_shift = db.query(WorkShift).filter(
        WorkShift.staff_id == current_user.id,
        WorkShift.status == "OPEN"
    ).order_by(WorkShift.start_time.desc()).first()

    # 2. If no open shift exists, initialize one
    if not open_shift:
        now = datetime.now(timezone.utc)
        # Shift name heuristic based on hour
        hour = now.hour
        shift_name = "Ca sáng (07:00 - 15:00)" if hour < 15 else "Ca chiều tối (15:00 - 22:00)"
        
        open_shift = WorkShift(
            shift_name=f"{shift_name} - {now.strftime('%d/%m/%Y')}",
            staff_id=current_user.id,
            staff_name=current_user.full_name,
            start_time=now,
            initial_cash=500000,
            expected_cash=500000,
            status="OPEN"
        )
        db.add(open_shift)
        db.commit()
        db.refresh(open_shift)

    # 3. Calculate live stats
    open_shift = _calculate_shift_live_stats(open_shift, db)
    db.commit()
    db.refresh(open_shift)

    return open_shift


@router.post("/close", response_model=WorkShiftResponse)
def close_current_shift(
    req: CloseShiftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Close the current staff member's shift, reconcile cash, and record discrepancies.
    """
    open_shift = db.query(WorkShift).filter(
        WorkShift.staff_id == current_user.id,
        WorkShift.status == "OPEN"
    ).order_by(WorkShift.start_time.desc()).first()

    if not open_shift:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy ca làm việc đang mở để kết ca!"
        )

    # Calculate final sales stats
    open_shift = _calculate_shift_live_stats(open_shift, db)
    
    # Record actual cash & discrepancy
    open_shift.actual_cash = req.actual_cash
    open_shift.difference = req.actual_cash - open_shift.expected_cash
    open_shift.note = req.note
    open_shift.end_time = datetime.now(timezone.utc)
    open_shift.status = "CLOSED"

    db.commit()
    db.refresh(open_shift)

    return open_shift


@router.get("", response_model=List[WorkShiftResponse])
def get_shifts_list(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    staff_id: Optional[str] = Query(default=None),
    date_filter: Optional[str] = Query(default=None, alias="date"),
    branch_id: Optional[str] = Query(default=None, alias="branchId"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List work shifts with optional filters.
    Staff can view their own shifts, Admin can view all shifts.
    """
    query = db.query(WorkShift)

    if current_user.role_code not in ["SUPER_ADMIN", "ADMIN"] and "shifts:manage" not in current_user.get_permissions():
        query = query.filter(WorkShift.staff_id == current_user.id)
    elif staff_id:
        query = query.filter(WorkShift.staff_id == staff_id)

    if status_filter:
        query = query.filter(WorkShift.status == status_filter)

    if branch_id and branch_id != "ALL":
        query = query.filter(WorkShift.branch_id == branch_id)

    start_dt, end_dt = _parse_day_range(date_filter)
    if start_dt:
        query = query.filter(WorkShift.start_time >= start_dt, WorkShift.start_time < end_dt)

    shifts = query.order_by(WorkShift.start_time.desc()).all()

    # Re-calc live stats for any OPEN shifts in list
    for s in shifts:
        if s.status == "OPEN":
            _calculate_shift_live_stats(s, db)

    return shifts


@router.get("/summary", response_model=ShiftSummaryResponse)
def get_shift_summary(
    date_filter: Optional[str] = Query(default=None, alias="date"),
    branch_id: Optional[str] = Query(default=None, alias="branchId"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("shifts:read"))
):
    """
    Comprehensive shift executive summary for Admin:
    Aggregates total revenue, cash reconciliation, and all shifts for the day/range (SARGable).
    """
    query = db.query(WorkShift)
    if branch_id and branch_id != "ALL":
        query = query.filter(WorkShift.branch_id == branch_id)

    start_dt, end_dt = _parse_day_range(date_filter)
    if start_dt:
        query = query.filter(WorkShift.start_time >= start_dt, WorkShift.start_time < end_dt)

    shifts = query.order_by(WorkShift.start_time.desc()).all()
    for s in shifts:
        if s.status == "OPEN":
            _calculate_shift_live_stats(s, db)

    total_shifts = len(shifts)
    closed_shifts = sum(1 for s in shifts if s.status == "CLOSED")
    open_shifts = sum(1 for s in shifts if s.status == "OPEN")
    
    total_rev = sum(s.total_revenue for s in shifts)
    total_cash = sum(s.cash_revenue for s in shifts)
    total_card = sum(s.card_revenue for s in shifts)
    total_qr = sum(s.qr_revenue for s in shifts)
    total_diff = sum(s.difference for s in shifts if s.status == "CLOSED")

    return ShiftSummaryResponse(
        total_shifts_count=total_shifts,
        closed_shifts_count=closed_shifts,
        open_shifts_count=open_shifts,
        total_revenue=total_rev,
        total_cash=total_cash,
        total_card=total_card,
        total_qr=total_qr,
        total_difference=total_diff,
        shifts=shifts
    )
