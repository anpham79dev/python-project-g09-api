from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.dependencies import get_db, get_current_user, require_permission
from app.models.user import User
from app.models.order import Order
from app.models.shift import WorkShift
from app.schemas.shift import (
    WorkShiftResponse,
    OpenShiftRequest,
    CloseShiftRequest,
    ShiftScheduleResponse,
    ShiftSummaryResponse
)
from app.core.timezone import get_now_vn, get_now_utc, get_date_range_vn
from app.core.shifts import get_current_schedule

router = APIRouter(prefix="/shifts", tags=["Shift & Cash Management"])


def _calculate_shift_live_stats(shift: WorkShift, db: Session) -> WorkShift:
    """Dynamically aggregate orders completed during the shift window."""
    if shift.status == "CLOSED":
        return shift

    # Query all completed orders created by this staff member since shift start_time
    orders_query = db.query(Order).filter(
        Order.staff_id == shift.staff_id,
        Order.created_at >= shift.start_time,
        Order.status == "COMPLETED"
    )
    if shift.end_time:
        orders_query = orders_query.filter(Order.created_at <= shift.end_time)

    orders = orders_query.all()

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


@router.get("/current-schedule", response_model=ShiftScheduleResponse)
def get_current_shift_schedule(db: Session = Depends(get_db)):
    """Single source of truth for the active shift schedule based on current Vietnam time."""
    schedule = get_current_schedule(db)
    return ShiftScheduleResponse(**schedule)


@router.get("/current", response_model=Optional[WorkShiftResponse])
def get_current_shift(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the currently open shift for the logged-in staff member (Read-only).
    Returns null if the staff has not opened a shift. Never auto-creates records.
    """
    open_shift = db.query(WorkShift).filter(
        WorkShift.staff_id == current_user.id,
        WorkShift.status == "OPEN"
    ).order_by(WorkShift.start_time.desc()).first()

    if not open_shift:
        return None

    open_shift = _calculate_shift_live_stats(open_shift, db)
    db.commit()
    db.refresh(open_shift)
    return open_shift


@router.post("/open", response_model=WorkShiftResponse, status_code=status.HTTP_201_CREATED)
def open_shift(
    req: OpenShiftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Open a new working shift with initial cash float."""
    # 1. Check if user already has an active OPEN shift
    existing = db.query(WorkShift).filter(
        WorkShift.staff_id == current_user.id,
        WorkShift.status == "OPEN"
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn đã có ca làm việc đang mở. Vui lòng kết ca hiện tại trước khi mở ca mới!"
        )

    # 2. Determine schedule and title according to shift_templates and VN time
    schedule = get_current_schedule(db)
    now_vn = get_now_vn()
    now_utc = get_now_utc()

    if schedule.get("start_time"):
        shift_title = f"{schedule['name']} ({schedule['start_time']} - {schedule['end_time']}) - {now_vn.strftime('%d/%m/%Y')}"
    else:
        shift_title = f"{schedule['name']} ({now_vn.strftime('%H:%M')}) - {now_vn.strftime('%d/%m/%Y')}"

    target_branch = req.branch_id or current_user.default_branch_id or "branch-001"

    new_shift = WorkShift(
        branch_id=target_branch,
        template_id=schedule.get("template_id"),
        shift_name=shift_title,
        staff_id=current_user.id,
        staff_name=current_user.full_name,
        start_time=now_utc,
        initial_cash=req.initial_cash,
        expected_cash=req.initial_cash,
        actual_cash=0,
        difference=-req.initial_cash,
        status="OPEN",
        note=req.note
    )
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)
    return new_shift


@router.post("/close", response_model=WorkShiftResponse)
def close_current_shift(
    req: CloseShiftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Close the current staff member's shift, reconcile cash, and record discrepancies."""
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

    # Reconcile cash: expected = initial_cash + cash_revenue, difference = actual_cash - expected_cash
    open_shift.actual_cash = req.actual_cash
    open_shift.expected_cash = open_shift.initial_cash + open_shift.cash_revenue
    open_shift.difference = req.actual_cash - open_shift.expected_cash
    open_shift.note = req.note
    open_shift.end_time = get_now_utc()
    open_shift.status = "CLOSED"

    db.commit()
    db.refresh(open_shift)
    return open_shift


@router.get("", response_model=List[WorkShiftResponse])
def get_shifts_list(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    staff_id: Optional[str] = Query(default=None),
    staffId: Optional[str] = Query(default=None),
    date_filter: Optional[str] = Query(default=None, alias="date"),
    branch_id: Optional[str] = Query(default=None),
    branchId: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List work shifts with optional filters. Staff sees own shifts, Admin sees all."""
    query = db.query(WorkShift)

    target_staff = staffId or staff_id
    target_branch = branchId or branch_id

    if current_user.role_code not in ["SUPER_ADMIN", "ADMIN"] and "shifts:manage" not in current_user.get_permissions():
        query = query.filter(WorkShift.staff_id == current_user.id)
    elif target_staff:
        query = query.filter(WorkShift.staff_id == target_staff)

    if status_filter and status_filter != "ALL":
        query = query.filter(WorkShift.status == status_filter)

    if target_branch and target_branch != "ALL":
        query = query.filter(WorkShift.branch_id == target_branch)

    if date_filter:
        try:
            start_utc, end_utc = get_date_range_vn(date_filter)
            query = query.filter(WorkShift.start_time >= start_utc, WorkShift.start_time < end_utc)
        except Exception:
            pass

    shifts = query.order_by(WorkShift.start_time.desc()).all()

    # Re-calc live stats for any OPEN shifts in list
    for s in shifts:
        if s.status == "OPEN":
            _calculate_shift_live_stats(s, db)

    return shifts


@router.get("/summary", response_model=ShiftSummaryResponse)
def get_shift_summary(
    date_filter: Optional[str] = Query(default=None, alias="date"),
    branch_id: Optional[str] = Query(default=None),
    branchId: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("shifts:read"))
):
    """Comprehensive shift summary for Admin, filtered by VN date and branch."""
    target_branch = branchId or branch_id
    query = db.query(WorkShift)
    if target_branch and target_branch != "ALL":
        query = query.filter(WorkShift.branch_id == target_branch)

    if date_filter:
        try:
            start_utc, end_utc = get_date_range_vn(date_filter)
            query = query.filter(WorkShift.start_time >= start_utc, WorkShift.start_time < end_utc)
        except Exception:
            pass

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
