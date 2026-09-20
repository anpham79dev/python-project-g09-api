from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo
from typing import Tuple, Optional

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def get_now_vn() -> datetime:
    """Get current datetime in Vietnam timezone (Asia/Ho_Chi_Minh)."""
    return datetime.now(VN_TZ)


def get_now_utc() -> datetime:
    """Get current datetime in UTC with timezone awareness."""
    return datetime.now(timezone.utc)


def get_date_range_vn(date_str: str) -> Tuple[datetime, datetime]:
    """Given 'YYYY-MM-DD', returns (start_utc, end_utc) corresponding to that Vietnam calendar day."""
    d = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    start_vn = datetime.combine(d, time.min).replace(tzinfo=VN_TZ)
    end_vn = start_vn + timedelta(days=1)
    return start_vn.astimezone(timezone.utc), end_vn.astimezone(timezone.utc)


def get_period_range_vn(
    range_type: str,
    start_str: Optional[str] = None,
    end_str: Optional[str] = None
) -> Tuple[datetime, datetime]:
    """Calculate UTC bounds for a given time range based on Vietnam calendar dates.
    Supported range_types: 'today', '7days'/'7d', '30days'/'30d', 'custom'.
    """
    now_vn = get_now_vn()
    today_vn = now_vn.date()

    if range_type in ["7days", "7d"]:
        start_d = today_vn - timedelta(days=6)
        end_d = today_vn
    elif range_type in ["30days", "30d", "month"]:
        start_d = today_vn - timedelta(days=29)
        end_d = today_vn
    elif range_type == "custom" and start_str and end_str:
        try:
            start_d = datetime.strptime(start_str.strip(), "%Y-%m-%d").date()
            end_d = datetime.strptime(end_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            start_d = today_vn
            end_d = today_vn
    else:  # "today"
        start_d = today_vn
        end_d = today_vn

    start_vn = datetime.combine(start_d, time.min).replace(tzinfo=VN_TZ)
    end_vn = datetime.combine(end_d + timedelta(days=1), time.min).replace(tzinfo=VN_TZ)
    return start_vn.astimezone(timezone.utc), end_vn.astimezone(timezone.utc)
