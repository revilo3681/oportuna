"""Devpost public hackathon listing adapter.

Devpost exposes a public JSON listing. We read it as-is, keep the organizer's
URL, and never claim that registration is open just because a submission link
exists. ``submission_period_dates`` is a submission window, not a registration
deadline, so it maps to event dates + submission_deadline.
"""

from __future__ import annotations

import json
from urllib.parse import urlencode

from oportuna.domain.dates import parse_date_range
from oportuna.domain.normalize import clean_html, domain_of, guess_country
from oportuna.domain.taxonomy import classify_category, detect_modality, extract_tech_tags
from oportuna.ingest.adapters.base import allowed_domains_for, parse_price
from oportuna.ingest.http import Fetcher, FetchError
from oportuna.ingest.types import RawOpportunity


class DevpostAdapter:
    kind = "devpost"

    async def fetch(self, source, fetcher: Fetcher) -> list[RawOpportunity]:
        config = source.config or {}
        params: list[tuple[str, str]] = [("per_page", str(min(int(config.get("per_page", 100)), 100)))]
        for status in config.get("statuses", ["open"]):
            params.append(("status[]", status))
        url = f"{source.endpoint}?{urlencode(params)}"
        result = await fetcher.fetch_text(
            url,
            allowed_domains=allowed_domains_for(source),
            respect_robots=bool(config.get("respect_robots", True)),
        )
        try:
            payload = json.loads(result.content)
        except json.JSONDecodeError as exc:
            raise FetchError("Respuesta de Devpost no es JSON válido", url=url) from exc

        items = payload.get("hackathons") or []
        limit = int(config.get("max_items", 100))
        records: list[RawOpportunity] = []
        for item in items[:limit]:
            record = self._map(item, source, result.fetched_at)
            if record:
                records.append(record)
        return records

    def _map(self, item: dict, source, fetched_at) -> RawOpportunity | None:
        title = clean_html(item.get("title") or "")
        official_url = (item.get("url") or "").strip()
        if not title or not official_url:
            return None

        location = (item.get("displayed_location") or {}).get("location") or ""
        modality = detect_modality(location)
        if re_online(location):
            modality = "online"
        city = None
        country = None
        if modality != "online" and location:
            parts = [p.strip() for p in location.split(",") if p.strip()]
            city = parts[0] if parts else None
            country = guess_country(location)

        start, end, date_note = parse_date_range(item.get("submission_period_dates"))
        themes = [t.get("name", "") for t in item.get("themes", []) if isinstance(t, dict)]
        theme_text = " ".join(themes)
        tags = extract_tech_tags(title, theme_text)
        category = classify_category(title, theme_text) or "hackathons"

        prize_amount, currency = parse_price(item.get("prize_amount"))
        prizes_counts = item.get("prizes_counts") or {}
        prizes: list[dict] = []
        if prize_amount:
            prizes.append(
                {
                    "type": "cash",
                    "amount": prize_amount,
                    "currency": currency or "USD",
                    "label": "Premio acumulado en efectivo",
                }
            )
        if int(prizes_counts.get("cash") or 0):
            prizes.append(
                {
                    "type": "cash",
                    "count": int(prizes_counts["cash"]),
                    "label": f"{prizes_counts['cash']} premios en efectivo",
                }
            )
        if int(prizes_counts.get("other") or 0):
            prizes.append(
                {
                    "type": "other",
                    "count": int(prizes_counts["other"]),
                    "label": f"{prizes_counts['other']} premios adicionales",
                }
            )

        organizer = (item.get("organization_name") or "").strip() or None
        open_state = item.get("open_state") or ""
        winners = bool(item.get("winners_announced"))
        stated = "finished" if winners else ("open" if open_state == "open" else ("closed" if open_state else None))

        modality_text = {"online": "online", "presencial": "presencial", "hibrida": "híbrida"}.get(modality, "")
        headline = f"Hackathon {modality_text}".strip()
        if organizer:
            headline += f" organizado por {organizer}"
        summary = headline + "."
        if themes:
            summary += " Temáticas: " + ", ".join(themes[:4]) + "."
        if date_note:
            summary += f" Fechas: {date_note}."

        registration_url = (item.get("start_a_submission_url") or "").strip() or None
        duration = None
        if start and end:
            duration = int((end - start).total_seconds() // 60)

        return RawOpportunity(
            external_id=str(item.get("id") or official_url),
            title=title,
            official_url=official_url,
            source_url=official_url,
            summary=summary,
            description="",
            category=category,
            subcategory="hackathon",
            tech_tags=tags,
            modality=modality,
            country=country,
            city=city,
            language="en",
            organizer=organizer,
            registration_url=registration_url,
            event_start=start,
            event_end=end,
            submission_deadline=end,
            duration_minutes=duration,
            cost_type="unknown",
            prizes=prizes,
            eligibility={"invite_only": True} if item.get("invite_only") else {},
            stated_lifecycle=stated,
            confirmed=True,
            confirmation_note="Listado oficial de Devpost y enlace de envío del organizador.",
            raw_excerpt=summary,
            extra={
                "registrations_count": item.get("registrations_count"),
                "themes": themes,
                "time_left": item.get("time_left_to_submission"),
                "fetched_at": fetched_at.isoformat(),
                "domain": domain_of(official_url),
            },
        )


def re_online(location: str) -> bool:
    import re

    return bool(re.search(r"\b(online|virtual|remote)\b", location, re.IGNORECASE))
