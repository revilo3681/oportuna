"""Date parsing and lifecycle rules.

Core rule: event date and application deadline are different facts. A missing
deadline stays missing (``None``) and is shown as unknown; it is never guessed.
"""

from __future__ import annotations

import calendar
import re
from datetime import UTC, date, datetime, time, timedelta

from dateutil import parser as date_parser

UTC = UTC
_MONTHS = {name.lower(): index for index, name in enumerate(calendar.month_name) if name}
_MONTHS.update({name.lower(): index for index, name in enumerate(calendar.month_abbr) if name})
_MONTHS.update({
    "sept": 9, "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
})


def utcnow() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def end_of_day(value: datetime) -> datetime:
    return ensure_utc(value).replace(hour=23, minute=59, second=59, microsecond=0)


def start_of_day(value: datetime) -> datetime:
    return ensure_utc(value).replace(hour=0, minute=0, second=0, microsecond=0)


def parse_datetime(value: object) -> datetime | None:
    """Parse a concrete date/datetime. Returns None instead of guessing."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_utc(value)
    if isinstance(value, date):
        return datetime.combine(value, time(0, 0), tzinfo=UTC)
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = date_parser.parse(text, fuzzy=False)
    except (ValueError, TypeError, OverflowError):
        return None
    return ensure_utc(parsed)


def _month_day_year(part: str) -> tuple[int | None, int | None, int | None]:
    """Extract (day, month, year) from forms like 'Aug 31', '31 August', 'Oct 23, 2026'."""
    text = re.sub(r"\s+", " ", part.strip().lower().replace(",", " "))
    tokens = text.split()
    month = None
    day = None
    year = None
    for token in tokens:
        if token.isdigit() and len(token) == 4:
            year = int(token)
        elif token.isdigit() and 1 <= int(token) <= 31 and day is None:
            day = int(token)
        elif token.rstrip(".") in _MONTHS:
            month = _MONTHS[token.rstrip(".")]
    if month is None:
        for token in tokens:
            for key, val in _MONTHS.items():
                if token.startswith(key[:3]) and len(key) >= 3:
                    month = val
                    break
            if month:
                break
    return day, month, year


def parse_date_range(text: str | None) -> tuple[datetime | None, datetime | None, str]:
    """Parse 'Aug 31 - Oct 23, 2026' style ranges.

    Returns (start, end, note). Never fabricates a year: if no year is present in
    the string the range is rejected with an explanatory note.
    """
    if not text:
        return None, None, "sin fechas"
    cleaned = text.strip()
    if not cleaned:
        return None, None, "sin fechas"

    # Split only on spaced dashes, so ISO dates (2026-08-31) are preserved.
    parts = re.split(r"\s+[-–—]\s+", cleaned)
    if len(parts) == 2:
        left, right = parts
        left_day, left_month, left_year = _month_day_year(left)
        right_day, right_month, right_year = _month_day_year(right)
        year = right_year or left_year
        if not year:
            return None, None, "rango sin año explicito"
        if left_month is None and right_month is not None:
            left_month = right_month
        if right_month is None and left_month is not None:
            right_month = left_month
        if left_day is None or right_day is None or left_month is None or right_month is None:
            return None, None, "rango de fechas incompleto"
        try:
            start_year = year
            if right_year is not None and (right_month, right_day) < (left_month, left_day):
                # "Dec 28 - Jan 4, 2026": the stated year belongs to the end date.
                start_year = right_year - 1
            start = datetime(start_year, left_month, left_day, tzinfo=UTC)
            end_year = right_year if right_year is not None else start_year
            if (right_month, right_day) < (left_month, left_day) and right_year is None:
                end_year = start_year + 1
            end = datetime(end_year, right_month, right_day, 23, 59, 59, tzinfo=UTC)
        except ValueError:
            return None, None, "rango de fechas invalido"
        if end < start:
            return None, None, "rango de fechas invertido"
        return start, end, ""

    single = parse_datetime(cleaned)
    if single is None:
        return None, None, "fecha no interpretable"
    if not re.search(r"\b(19|20)\d{2}\b", cleaned):
        return None, None, "fecha sin año explicito"
    return start_of_day(single), end_of_day(single), ""


def parse_deadline(value: object, *, end_of_day_default: bool = True) -> datetime | None:
    """Deadlines are stored at end of day when only a date is supplied."""
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    if end_of_day_default and isinstance(value, str) and len(value.strip()) <= 10:
        return end_of_day(parsed)
    if end_of_day_default and isinstance(value, date) and not isinstance(value, datetime):
        return end_of_day(parsed)
    return parsed


def parse_stated_deadline(text: str | None, *, now: datetime | None = None) -> datetime | None:
    """Extract a deadline only when the source states it explicitly.

    Accepts patterns such as "Application Deadline: 22 November 2026" or
    "Fecha límite: 8 de diciembre de 2026". Never infers a date from context.
    """
    if not text:
        return None
    current = now or utcnow()
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    trigger = re.compile(
        r"(?:application deadline|deadline|closing date|applications? close|fecha l[ií]mite|cierre de (?:la )?convocatoria)\s*[:\-–]?\s*",
        re.IGNORECASE,
    )
    date_pattern = re.compile(
        r"(\d{1,2}\s+de\s+[A-Za-zÁÉÍÓÚáéíóúñ]+\s+(?:de\s+)?20\d{2}"
        r"|\d{1,2}\s+[A-Za-z]{3,9},?\s+20\d{2}"
        r"|[A-Za-z]{4,9}\s+\d{1,2},?\s+20\d{2}"
        r"|\d{4}-\d{2}-\d{2})"
        r"(?:[, ]+(\d{1,2}(?::\d{2})?\s*(?:am|pm|h|hrs)?))?",
        re.IGNORECASE,
    )
    for match in trigger.finditer(cleaned):
        segment = cleaned[match.end() : match.end() + 120]
        date_match = date_pattern.search(segment)
        if not date_match:
            continue
        raw = date_match.group(0)
        try:
            parsed = date_parser.parse(raw, fuzzy=True)
        except (ValueError, OverflowError):
            continue
        parsed = ensure_utc(parsed)
        if not date_match.group(2) or parsed.hour == 0:
            parsed = end_of_day(parsed)
        if parsed < current:
            continue
        if not (current.year - 1 <= parsed.year <= current.year + 3):
            continue
        return parsed
    return None


def effective_deadline(
    registration_deadline: datetime | None, submission_deadline: datetime | None
) -> datetime | None:
    candidates = [d for d in (registration_deadline, submission_deadline) if d is not None]
    if not candidates:
        return None
    return min(candidates)


def days_left(deadline: datetime | None, now: datetime | None = None) -> int | None:
    if deadline is None:
        return None
    reference = now or utcnow()
    delta = ensure_utc(deadline) - reference
    return int(delta.total_seconds() // 86400)


def deadline_urgency(deadline: datetime | None, now: datetime | None = None) -> str:
    """Coarse, display-oriented urgency bucket."""
    if deadline is None:
        return "unknown"
    days = days_left(deadline, now)
    if days is None:
        return "unknown"
    if days < 0:
        return "expired"
    if days <= 2:
        return "imminent"
    if days <= 7:
        return "soon"
    if days <= 30:
        return "upcoming"
    return "distant"


def deadline_label(deadline: datetime | None, now: datetime | None = None, locale: str = "es") -> str:
    if deadline is None:
        return "Fecha límite desconocida"
    reference = now or utcnow()
    seconds = (ensure_utc(deadline) - reference).total_seconds()
    days = days_left(deadline, reference)
    if seconds < 0:
        if days <= -2:
            return f"Cerró hace {-days} días"
        return "Cerrada"
    if seconds < 86400:
        hours = max(int(seconds // 3600), 1)
        return f"Cierra en {hours} h" if locale == "es" else f"Closes in {hours} h"
    if days == 0:
        return "Cierra hoy"
    if days == 1:
        return "Cierra mañana"
    if days <= 45:
        return f"Cierra en {days} días" if locale == "es" else f"Closes in {days} days"
    return deadline.strftime("%d %b %Y")


def derive_lifecycle(
    *,
    event_start: datetime | None,
    event_end: datetime | None,
    registration_deadline: datetime | None,
    rolling: bool = False,
    cancelled: bool = False,
    now: datetime | None = None,
) -> tuple[str, str]:
    """Return (lifecycle, registration_state).

    registration_state stays ``unknown`` when there is no stated deadline and the
    program is not explicitly continuous. A reachable URL never implies "open".
    """
    reference = now or utcnow()
    if cancelled:
        return "cancelled", "closed"
    end = event_end or event_start
    if end is not None and ensure_utc(end) < reference:
        return "finished", "closed"
    if rolling:
        return "rolling", "open"
    if registration_deadline is not None:
        if ensure_utc(registration_deadline) < reference:
            return "closed", "closed"
        return "open", "open"
    if event_start is not None and ensure_utc(event_start) < reference and end is None:
        return "closed", "unknown"
    return "open", "unknown"


def format_date_range(start: datetime | None, end: datetime | None, locale: str = "es") -> str:
    if start is None and end is None:
        return "Fechas por confirmar"
    if start is not None and end is not None:
        if start.date() == end.date():
            return start.strftime("%d %b %Y")
        if start.year == end.year:
            end_fmt = end.strftime("%d %b")
            start_fmt = start.strftime("%d %b %Y")
        else:
            start_fmt, end_fmt = start.strftime("%d %b %Y"), end.strftime("%d %b %Y")
        return f"{start_fmt} – {end_fmt}"
    single = start or end
    assert single is not None
    return single.strftime("%d %b %Y")


def add_days(value: datetime, days: int) -> datetime:
    return value + timedelta(days=days)
