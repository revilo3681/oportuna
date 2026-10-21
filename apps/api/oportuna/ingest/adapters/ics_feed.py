"""iCalendar adapter for official institutional calendars.

Universities publish public .ics feeds. These feeds are authoritative for the
event's existence and dates, but they rarely contain application deadlines, so
deadlines stay unknown unless the feed states them explicitly.
"""

from __future__ import annotations

from datetime import datetime

from icalendar import Calendar

from oportuna.domain.dates import (
    end_of_day,
    ensure_utc,
    parse_stated_deadline,
    utcnow,
)
from oportuna.domain.normalize import (
    clean_html,
    country_code_from_name,
    domain_of,
    guess_country,
    normalize_text,
    normalize_url,
    truncate,
)
from oportuna.domain.taxonomy import (
    classify_calendar_category,
    detect_modality,
    extract_tech_tags,
    looks_tech_strict,
)
from oportuna.ingest.adapters.base import allowed_domains_for, resolve_url
from oportuna.ingest.http import Fetcher, FetchError
from oportuna.ingest.types import RawOpportunity

DEFAULT_EXCLUDES = [
    "building hours",
    "open rec",
    "office hours",
    "drop-in advising",
    "weekly rec",
    "naloxone",
    "raffle",
    "writing",
    "wellness",
    "yoga",
    "meditation",
    "concert",
    "recital",
    "exhibit",
    "basketball",
    "fitness",
    "film screening",
]


class IcsAdapter:
    kind = "ics"

    async def fetch(self, source, fetcher: Fetcher) -> list[RawOpportunity]:
        config = source.config or {}
        result = await fetcher.fetch_text(
            source.endpoint,
            allowed_domains=allowed_domains_for(source),
            respect_robots=bool(config.get("respect_robots", True)),
        )
        try:
            calendar = Calendar.from_ical(result.content.encode("utf-8") if isinstance(result.content, str) else result.content)
        except Exception as exc:  # noqa: BLE001 - malformed third-party calendars are expected
            raise FetchError(f"Calendario ICS inválido: {exc}", url=source.endpoint) from exc

        now = utcnow()
        lookahead_days = int(config.get("lookahead_days", 120))
        past_days = int(config.get("past_days", 1))
        limit = int(config.get("max_items", 60))
        require_tech = bool(config.get("require_tech", True))
        excludes = [e.lower() for e in (config.get("exclude_keywords") or DEFAULT_EXCLUDES)]
        default_country = country_code_from_name(config.get("default_country"))
        default_language = config.get("language", "en")

        records: list[RawOpportunity] = []
        seen: set[str] = set()
        for component in calendar.walk("VEVENT"):
            record = self._map(
                component,
                source,
                result.fetched_at,
                now,
                lookahead_days,
                past_days,
                require_tech,
                excludes,
                default_country,
                default_language,
            )
            if record and record.external_id not in seen:
                seen.add(record.external_id)
                records.append(record)
            if len(records) >= limit:
                break
        if bool(config.get("collapse_series", True)):
            records = self._collapse_series(records)
        return records

    def _collapse_series(self, records: list[RawOpportunity]) -> list[RawOpportunity]:
        groups: dict[tuple[str, str], list[RawOpportunity]] = {}
        for record in records:
            key = (normalize_text(record.title), normalize_url(record.official_url))
            groups.setdefault(key, []).append(record)

        collapsed: list[RawOpportunity] = []
        now = utcnow()
        for group in groups.values():
            if len(group) == 1:
                collapsed.append(group[0])
                continue
            group.sort(key=lambda item: item.event_start or now)
            upcoming = [item for item in group if item.event_start and item.event_start >= now]
            representative = (upcoming or group)[0]
            phases = [
                {
                    "label": f"Sesión {index + 1}",
                    "start": item.event_start.isoformat() if item.event_start else None,
                    "end": item.event_end.isoformat() if item.event_end else None,
                }
                for index, item in enumerate(group)
            ]
            representative.phases = phases
            representative.extra = {
                **(representative.extra or {}),
                "series_sessions": len(group),
                "series_last_session": group[-1].event_start.isoformat()
                if group[-1].event_start
                else None,
            }
            note = (
                f"Serie recurrente con {len(group)} sesiones"
                + (
                    f"; la última publicada es el {group[-1].event_start:%d %b %Y}."
                    if group[-1].event_start
                    else "."
                )
            )
            representative.summary = (
                (representative.summary + " " if representative.summary else "") + note
            )
            collapsed.append(representative)
        collapsed.sort(key=lambda item: item.event_start or now)
        return collapsed

    def _map(
        self,
        component,
        source,
        fetched_at,
        now: datetime,
        lookahead_days: int,
        past_days: int,
        require_tech: bool,
        excludes: list[str],
        default_country: str | None,
        default_language: str,
    ) -> RawOpportunity | None:
        title = clean_html(str(component.get("SUMMARY") or "")).strip()
        if not title:
            return None
        lowered = title.lower()
        if any(ex in lowered for ex in excludes):
            return None

        dtstart = component.get("DTSTART")
        if dtstart is None:
            return None
        start_raw = dtstart.dt
        start = ensure_utc(start_raw) if isinstance(start_raw, datetime) else ensure_utc(
            datetime.combine(start_raw, datetime.min.time())
        )
        dtend = component.get("DTEND")
        end = None
        if dtend is not None:
            end_raw = dtend.dt
            end = ensure_utc(end_raw) if isinstance(end_raw, datetime) else end_of_day(
                ensure_utc(datetime.combine(end_raw, datetime.min.time()))
            )

        if start < now.replace(hour=0, minute=0, second=0, microsecond=0) - __import__("datetime").timedelta(days=past_days):
            return None
        if start > now + __import__("datetime").timedelta(days=lookahead_days):
            return None

        location = clean_html(str(component.get("LOCATION") or ""))
        description = clean_html(str(component.get("DESCRIPTION") or ""))
        categories = str(component.get("CATEGORIES") or "")
        if require_tech and not looks_tech_strict(title):
            return None

        category = classify_calendar_category(title)
        if require_tech and category is None:
            # Strong tech signal but no recognizable format: keep as a community event.
            category = "eventos"
        modality = detect_modality(title, description, location) if location else "unknown"
        city = None
        country = default_country
        if location:
            parts = [p.strip() for p in location.split(",") if p.strip()]
            city = parts[0] if parts else None
            if modality == "online":
                city = None
        if not country:
            country = guess_country(location, title)

        url = str(component.get("URL") or "").strip()
        official_url = resolve_url(source.homepage_url, url)
        external_id = str(
            component.get("X-LIVEWHALE-ID") or component.get("UID") or official_url
        )

        organizer = None
        organizer_prop = component.get("ORGANIZER")
        if organizer_prop is not None:
            organizer = str(getattr(organizer_prop, "params", {}).get("CN", "") or "").strip() or None

        timezone = str(component.get("X-LIVEWHALE-TIMEZONE") or "") or None
        max_deadline = parse_stated_deadline(description, now=now) if description else None

        return RawOpportunity(
            external_id=external_id,
            title=title,
            official_url=official_url,
            source_url=source.endpoint,
            summary=truncate(description, 280) if description else "",
            description=description,
            category=category,
            subcategory=None,
            tech_tags=extract_tech_tags(title, description, categories),
            modality=modality,
            country=country,
            city=city,
            timezone=timezone,
            language=default_language,
            organizer=organizer,
            event_start=start,
            event_end=end,
            registration_deadline=max_deadline,
            duration_minutes=int((end - start).total_seconds() // 60) if end and end > start else None,
            confirmed=True,
            confirmation_note=(
                "Evento publicado en el calendario oficial de la institución"
                + (f"; país derivado de la fuente ({default_country})" if default_country else "")
                + "."
            ),
            raw_excerpt=f"{title} — {location}".strip(" —"),
            extra={
                "calendar": source.slug,
                "uid": external_id,
                "fetched_at": fetched_at.isoformat(),
                "domain": domain_of(official_url),
            },
        )
