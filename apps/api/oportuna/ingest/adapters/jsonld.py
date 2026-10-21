"""JSON-LD (schema.org Event) adapter for official event pages."""

from __future__ import annotations

import json
import re

from oportuna.domain.dates import parse_datetime
from oportuna.domain.normalize import (
    clean_html,
    country_code_from_name,
    country_name_from_code,
    domain_of,
    guess_country,
    truncate,
)
from oportuna.domain.taxonomy import (
    classify_category,
    detect_modality,
    extract_tech_tags,
    looks_tech,
)
from oportuna.ingest.adapters.base import allowed_domains_for
from oportuna.ingest.http import Fetcher, FetchError
from oportuna.ingest.types import RawOpportunity

LD_JSON = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.IGNORECASE | re.DOTALL
)


def _iter_nodes(payload) -> list[dict]:
    nodes: list[dict] = []
    if isinstance(payload, list):
        for item in payload:
            nodes.extend(_iter_nodes(item))
    elif isinstance(payload, dict):
        if "@graph" in payload and isinstance(payload["@graph"], list):
            nodes.extend(_iter_nodes(payload["@graph"]))
        nodes.append(payload)
    return nodes


def _types(node: dict) -> list[str]:
    raw = node.get("@type")
    if isinstance(raw, list):
        return [str(t) for t in raw]
    return [str(raw)] if raw else []


def extract_event_nodes(html_text: str) -> list[dict]:
    events: list[dict] = []
    for block in LD_JSON.findall(html_text):
        try:
            payload = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        for node in _iter_nodes(payload):
            if any("Event" in t for t in _types(node)):
                events.append(node)
    return events


class JsonLdAdapter:
    kind = "jsonld"

    async def fetch(self, source, fetcher: Fetcher) -> list[RawOpportunity]:
        config = source.config or {}
        result = await fetcher.fetch_text(
            source.endpoint,
            allowed_domains=allowed_domains_for(source),
            respect_robots=bool(config.get("respect_robots", True)),
        )
        nodes = extract_event_nodes(result.content)
        if not nodes:
            raise FetchError("No se encontraron eventos schema.org en la página", url=source.endpoint)

        records: list[RawOpportunity] = []
        limit = int(config.get("max_items", 60))
        require_tech = bool(config.get("require_tech", True))
        for node in nodes:
            record = self._map(node, source, result.fetched_at, require_tech)
            if record:
                records.append(record)
            if len(records) >= limit:
                break
        return records

    def _map(self, node: dict, source, fetched_at, require_tech: bool) -> RawOpportunity | None:
        title = clean_html(node.get("name") or "").strip()
        official_url = (node.get("url") or "").strip()
        if not title or not official_url:
            return None

        raw_description = node.get("description") or ""
        # schema.org data is sometimes double-escaped.
        description = clean_html(clean_html(str(raw_description)))
        if require_tech and not looks_tech(title, description):
            return None

        start = parse_datetime(node.get("startDate"))
        end = parse_datetime(node.get("endDate"))
        if start is None:
            return None

        location = node.get("location") or {}
        city = None
        country = None
        if isinstance(location, dict):
            address = location.get("address") or {}
            if isinstance(address, dict):
                city = address.get("addressLocality")
                country = country_code_from_name(address.get("addressCountry"))
            if not city:
                place_name = (location.get("name") or "").strip()
                city = place_name.split(",")[0] if place_name else None
        elif isinstance(location, str):
            city = location.split(",")[0].strip() if location else None
            country = guess_country(location)

        attendance = str(node.get("eventAttendanceMode") or "")
        if "Online" in attendance:
            modality = "online"
        elif "Mixed" in attendance:
            modality = "hibrida"
        elif "Offline" in attendance:
            modality = "presencial"
        else:
            modality = detect_modality(title, description, str(location))

        status = str(node.get("eventStatus") or "")
        stated = "closed" if "Cancelled" in status else None

        offers = node.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        cost_type = "unknown"
        cost_amount = None
        currency = None
        if isinstance(offers, dict) and offers.get("price") is not None:
            currency = offers.get("priceCurrency")
            try:
                cost_amount = float(str(offers.get("price")).replace(",", ""))
                cost_type = "free" if cost_amount == 0 else "paid"
            except ValueError:
                cost_type = "unknown"

        category = classify_category(title) or classify_category(title, description) or "eventos"
        tags = extract_tech_tags(title, description)

        organizer = None
        organizer_url = None
        organizer_node = node.get("organizer") or node.get("performer")
        if isinstance(organizer_node, dict) and organizer_node.get("name"):
            organizer = clean_html(str(organizer_node["name"]))
            organizer_url = organizer_node.get("url")
        elif isinstance(organizer_node, str) and organizer_node not in {"Organization", "Person"}:
            organizer = organizer_node

        summary = truncate(description, 280)

        return RawOpportunity(
            external_id=str(node.get("identifier") or official_url),
            title=title,
            official_url=official_url,
            source_url=source.endpoint,
            summary=summary,
            description=description,
            category=category,
            subcategory=None,
            tech_tags=tags,
            modality=modality,
            country=country,
            city=city,
            language=(node.get("inLanguage") or "en") if isinstance(node.get("inLanguage"), str) else "en",
            organizer=organizer,
            organizer_url=organizer_url,
            event_start=start,
            event_end=end,
            duration_minutes=int((end - start).total_seconds() // 60) if end and start and end > start else None,
            cost_type=cost_type,
            cost_amount=cost_amount,
            currency=currency,
            stated_lifecycle=stated,
            confirmed=True,
            confirmation_note="Datos estructurados schema.org de la página oficial del organizador.",
            raw_excerpt=summary,
            extra={
                "attendance_mode": attendance,
                "event_status": status,
                "country_name": country_name_from_code(country),
                "fetched_at": fetched_at.isoformat(),
                "domain": domain_of(official_url),
            },
        )
