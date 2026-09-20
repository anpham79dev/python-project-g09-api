from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.setting import ShiftTemplate
from app.core.timezone import get_now_vn


def get_current_schedule(db: Session) -> Dict[str, Any]:
    """Single source of truth function determining the current working shift
    based on current Vietnam time and shift_templates table.
    """
    now_vn = get_now_vn()
    cur_time_str = now_vn.strftime("%H:%M")

    active_templates = db.query(ShiftTemplate).filter(
        ShiftTemplate.is_active == True
    ).all()

    matched_template: Optional[ShiftTemplate] = None

    for tmpl in active_templates:
        st = tmpl.start_time.strip()
        et = tmpl.end_time.strip()

        if st <= et:
            if st <= cur_time_str < et:
                matched_template = tmpl
                break
        else:
            # Overnight shift (e.g. 22:30 -> 06:30)
            if cur_time_str >= st or cur_time_str < et:
                matched_template = tmpl
                break

    if matched_template:
        return {
            "template_id": matched_template.id,
            "name": matched_template.name,
            "start_time": matched_template.start_time,
            "end_time": matched_template.end_time,
            "shift_name": f"{matched_template.name} ({matched_template.start_time} - {matched_template.end_time})",
            "display_text": f"Ca: {matched_template.start_time} - {matched_template.end_time}",
            "is_working_hour": True,
            "default_initial_cash": matched_template.default_initial_cash or 500000
        }

    return {
        "template_id": None,
        "name": "Ngoài giờ làm việc",
        "start_time": None,
        "end_time": None,
        "shift_name": "Ngoài giờ làm việc",
        "display_text": "Ngoài giờ làm việc",
        "is_working_hour": False,
        "default_initial_cash": 500000
    }
