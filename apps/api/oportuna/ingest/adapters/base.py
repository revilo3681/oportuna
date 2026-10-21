"""Shared adapter helpers."""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from oportuna.domain.normalize import (
    clean_html,
    country_code_from_name,
    domain_of,
    registrable_domain,
)
from oportuna.domain.taxonomy import detect_modality


def allowed_domains_for(source) -> list[str]:
    config = source.config or {}
    domains = config.get("allowed_domains") or []
    if not domains:
        domains = [registrable_domain(source.endpoint)]
    return [d.lower() for d in domains if d]


def parse_price(value: object) -> tuple[float | None, str | None]:
    if value is None:
        return None, None
    text = html.unescape(str(value))
    currency = None
    if "$" in text or "USD" in text.upper():
        currency = "USD"
    elif "€" in text or "EUR" in text.upper():
        currency = "EUR"
    elif "£" in text or "GBP" in text.upper():
        currency = "GBP"
    match = re.search(r"(\d[\d.,]*)", text)
    if not match:
        return None, currency
    raw = match.group(1).replace(",", "")
    try:
        return float(raw), currency
    except ValueError:
        return None, currency


def location_details(location: str | None) -> tuple[str | None, str | None, str]:
    if not location:
        return None, None, "unknown"
    text = clean_html(location).strip()
    lowered = text.lower()
    if re.search(r"\b(online|virtual|remote|en línea)\b", lowered):
        return None, None, "online"
    modality = detect_modality(text)
    city = None
    country = None
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if parts:
        city = parts[0]
    if len(parts) >= 2:
        country = country_code_from_name(parts[-1])
    return city, country, modality


def same_domain(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return registrable_domain(a) == registrable_domain(b)


def domain_for(url: str | None) -> str:
    return domain_of(url)


def strip_source_suffix(title: str, source_name: str) -> str:
    pattern = re.compile(r"\s+[|\-–]\s+" + re.escape(source_name) + r"$", re.IGNORECASE)
    return pattern.sub("", title).strip()


def resolve_url(base: str, url: str | None) -> str:
    if not url:
        return base
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"}:
        return url
    from urllib.parse import urljoin

    return urljoin(base, url)
