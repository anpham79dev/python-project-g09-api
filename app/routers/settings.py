import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_permission, get_current_user
from app.models.user import User
from app.models.setting import ShiftTemplate, SystemSetting
from app.schemas.setting import (
    ShiftTemplateResponse,
    ShiftTemplateCreate,
    ShiftTemplateUpdate,
    SystemSettingsResponse,
    UpdateSystemSettingsRequest,
)

router = APIRouter(prefix="/settings", tags=["System Settings & Shift Config"])

DEFAULT_SETTINGS = {
    "store_name": "Artisan Bakery",
    "store_slogan": "Tiệm Bánh Thủ Công Pháp & Cà Phê Thượng Hạng",
    "hotline": "0901 234 567",
    "address": "123 Đường Đồng Khởi, Quận 1, TP.HCM",
    "default_vat_rate": "8",
    "low_stock_threshold": "5",
    "allow_negative_stock": "false",
    "require_shift_reconciliation_note": "true",
    "bank_account_number": "1028889999",
    "bank_name": "Vietcombank (VCB)",
    "bank_account_holder": "TIEM BANH ARTISAN BAKERY",
    "receipt_footer_note": "Cảm ơn Quý Khách & Chúc Quý Khách Một Ngày Ngọt Ngào!"
}


@router.get("", response_model=SystemSettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    """Get store-wide dynamic settings."""
    settings_dict = dict(DEFAULT_SETTINGS)
    db_settings = db.query(SystemSetting).all()

    for s in db_settings:
        settings_dict[s.key] = s.value

    return SystemSettingsResponse(
        store_name=settings_dict["store_name"],
        store_slogan=settings_dict["store_slogan"],
        hotline=settings_dict["hotline"],
        address=settings_dict["address"],
        default_vat_rate=int(settings_dict["default_vat_rate"]),
        low_stock_threshold=int(settings_dict["low_stock_threshold"]),
        allow_negative_stock=settings_dict["allow_negative_stock"] == "true",
        require_shift_reconciliation_note=settings_dict["require_shift_reconciliation_note"] == "true",
        bank_account_number=settings_dict["bank_account_number"],
        bank_name=settings_dict["bank_name"],
        bank_account_holder=settings_dict["bank_account_holder"],
        receipt_footer_note=settings_dict["receipt_footer_note"],
    )


@router.put("", response_model=SystemSettingsResponse)
def update_settings(
    req: UpdateSystemSettingsRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("settings:manage"))
):
    """Update store-wide dynamic settings."""
    req_dict = req.model_dump(exclude_unset=True)

    for k, v in req_dict.items():
        val_str = str(v).lower() if isinstance(v, bool) else str(v)
        setting = db.query(SystemSetting).filter(SystemSetting.key == k).first()
        if setting:
            setting.value = val_str
        else:
            db.add(SystemSetting(key=k, value=val_str))

    db.commit()
    return get_settings(db)


# ==========================================
# SHIFT TEMPLATES API
# ==========================================

@router.get("/shift-templates", response_model=List[ShiftTemplateResponse])
def get_shift_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of active shift templates."""
    templates = db.query(ShiftTemplate).filter(ShiftTemplate.is_active == True).all()
    return templates


@router.post("/shift-templates", response_model=ShiftTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_shift_template(
    req: ShiftTemplateCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("settings:manage"))
):
    """Create a new dynamic shift template."""
    tmpl = ShiftTemplate(
        name=req.name.strip(),
        start_time=req.start_time.strip(),
        end_time=req.end_time.strip(),
        default_initial_cash=req.default_initial_cash,
        is_active=req.is_active,
        note=req.note
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.put("/shift-templates/{template_id}", response_model=ShiftTemplateResponse)
def update_shift_template(
    template_id: str,
    req: ShiftTemplateUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("settings:manage"))
):
    """Update an existing shift template."""
    tmpl = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Không tìm thấy ca mẫu!")

    if req.name is not None: tmpl.name = req.name
    if req.start_time is not None: tmpl.start_time = req.start_time
    if req.end_time is not None: tmpl.end_time = req.end_time
    if req.default_initial_cash is not None: tmpl.default_initial_cash = req.default_initial_cash
    if req.is_active is not None: tmpl.is_active = req.is_active
    if req.note is not None: tmpl.note = req.note

    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.delete("/shift-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift_template(
    template_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("settings:manage"))
):
    """Delete a shift template."""
    tmpl = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Không tìm thấy ca mẫu!")
    db.delete(tmpl)
    db.commit()
    return None
