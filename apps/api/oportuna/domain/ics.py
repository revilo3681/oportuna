"""iCalendar export for saved opportunities and deadlines."""

from __future__ import annotations

from datetime import UTC, date, datetime

from icalendar import Calendar, Event

from oportuna.config import get_settings


def _as_date_or_datetime(value: datetime) -> date | datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    if (value.hour, value.minute) == (0, 0):
        return value.date()
    return value.astimezone(UTC)


def build_calendar(items: list[dict], *, name: str = "Oportuna") -> bytes:
    """Build a standards-compliant ICS feed.

    Each item: uid, title, date (deadline or event start), end (optional),
    kind ("deadline" | "event"), description, url, location.
    """
    settings = get_settings()
    calendar = Calendar()
    calendar.add("prodid", "-//Oportuna//Opportunity Radar//ES")
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("method", "PUBLISH")
    calendar.add("x-wr-calname", name)
    calendar.add("x-wr-timezone", "UTC")

    now = datetime.now(UTC)
    for item in items:
        starts = item.get("date")
        if not starts:
            continue
        event = Event()
        kind = item.get("kind", "deadline")
        suffix = "deadline" if kind == "deadline" else "event"
        event.add("uid", f"{suffix}-{item['uid']}@oportuna")
        title = item.get("title", "Oportunidad")
        event.add("summary", f"[Cierre] {title}" if kind == "deadline" else title)
        event.add("dtstart", _as_date_or_datetime(starts))
        ends = item.get("end")
        if ends:
            event.add("dtend", _as_date_or_datetime(ends))
        description = item.get("description") or ""
        source = item.get("url") or f"{settings.public_site_url}/oportunidades/{item['uid']}"
        event.add("description", f"{description}\n\nFuente: {source}")
        if item.get("url"):
            event.add("url", item["url"])
        if item.get("location"):
            event.add("location", item["location"])
        event.add("dtstamp", now)
        event.add("status", "CONFIRMED")
        event.add("categories", ["Oportuna", kind])
        calendar.add_component(event)

    return calendar.to_ical()
