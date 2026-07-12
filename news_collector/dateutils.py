from __future__ import annotations

from datetime import date, datetime
from typing import Optional

try:
    import jdatetime
except ImportError:  # pragma: no cover - optional dependency
    jdatetime = None


PERSIAN_NUMBERS = "۰۱۲۳۴۵۶۷۸۹"
ENGLISH_NUMBERS = "0123456789"
PERSIAN_TO_ENGLISH = str.maketrans(PERSIAN_NUMBERS, ENGLISH_NUMBERS)
ENGLISH_TO_PERSIAN = str.maketrans(ENGLISH_NUMBERS, PERSIAN_NUMBERS)

PERSIAN_MONTHS = [
    "", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]
PERSIAN_WEEKDAYS = [
    "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یک‌شنبه",
]


def to_persian_numbers(text: str) -> str:
    """Convert English digits to Persian digits."""
    return text.translate(ENGLISH_TO_PERSIAN)


def to_english_numbers(text: str) -> str:
    """Convert Persian digits to English digits."""
    return text.translate(PERSIAN_TO_ENGLISH)


def to_jalali(dt: Optional[date | datetime] = None) -> Optional[jdatetime.date]:
    """Convert Gregorian date to Jalali (Persian) date."""
    if dt is None:
        return None
    if jdatetime is None:
        return None
    if isinstance(dt, datetime):
        dt = dt.date()
    return jdatetime.date.fromgregorian(date=dt)


def format_jalali(
    dt: Optional[date | datetime] = None,
    *,
    include_weekday: bool = True,
    short: bool = False,
) -> str:
    """Format date in Persian (Jalali) with Persian numbers."""
    jd = to_jalali(dt)
    if jd is None:
        if dt is None:
            return ""
        return dt.strftime("%Y-%m-%d")

    if short:
        day = to_persian_numbers(str(jd.day))
        month = to_persian_numbers(str(jd.month))
        year = to_persian_numbers(str(jd.year))
        return f"{day}/{month}/{year}"

    weekday = PERSIAN_WEEKDAYS[jd.weekday()] if include_weekday else ""
    day = to_persian_numbers(str(jd.day))
    month = PERSIAN_MONTHS[jd.month]
    year = to_persian_numbers(str(jd.year))

    if include_weekday:
        return f"{weekday}، {day} {month} {year}"
    return f"{day} {month} {year}"


def format_iso_jalali(dt: Optional[date | datetime] = None) -> str:
    """Format date as YYYY-MM-DD in Jalali with Persian numbers."""
    jd = to_jalali(dt)
    if jd is None:
        if dt is None:
            return ""
        return dt.strftime("%Y-%m-%d")
    return to_persian_numbers(f"{jd.year:04d}-{jd.month:02d}-{jd.day:02d}")


def now_jalali_str(*, include_time: bool = True, include_weekday: bool = True) -> str:
    """Current time in Persian with Persian numbers."""
    now = datetime.now()
    date_part = format_jalali(now, include_weekday=include_weekday)
    if not include_time:
        return date_part
    time_str = now.strftime("%H:%M:%S")
    return f"{date_part} · {to_persian_numbers(time_str)}"


def parse_persian_date(text: str) -> Optional[date]:
    """Parse a Persian date string (YYYY-MM-DD with Persian numbers) to Gregorian date."""
    if not text:
        return None
    en_text = to_english_numbers(text.strip())
    try:
        parts = en_text.split("-")
        if len(parts) != 3:
            return None
        jy, jm, jd = map(int, parts)
        if jdatetime is None:
            return None
        jd_date = jdatetime.date(jy, jm, jd)
        return jd_date.togregorian()
    except (ValueError, AttributeError):
        return None


def get_persian_month_name(month: int) -> str:
    """Get Persian month name (1-12)."""
    if 1 <= month <= 12:
        return PERSIAN_MONTHS[month]
    return ""


def get_persian_weekday_name(weekday: int) -> str:
    """Get Persian weekday name (0=Monday ... 6=Sunday)."""
    if 0 <= weekday <= 6:
        return PERSIAN_WEEKDAYS[weekday]
    return ""


__all__ = [
    "to_persian_numbers",
    "to_english_numbers",
    "to_jalali",
    "format_jalali",
    "format_iso_jalali",
    "now_jalali_str",
    "parse_persian_date",
    "get_persian_month_name",
    "get_persian_weekday_name",
    "PERSIAN_MONTHS",
    "PERSIAN_WEEKDAYS",
]