"""Normalization helpers used by deduplication, provenance and search."""

from __future__ import annotations

import html
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from oportuna.domain.taxonomy import COUNTRY_NAMES, strip_accents

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "referrer", "source", "mc_cid", "mc_eid", "igshid",
}

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "at", "by", "with",
    "el", "la", "los", "las", "de", "del", "y", "o", "para", "con", "en", "por", "un",
    "una", "2024", "2025", "2026", "2027", "2028",
}

GENERIC_EVENT_WORDS = {
    "hackathon", "hackaton", "conference", "summit", "meetup", "workshop", "event",
    "events", "challenge", "competition", "program", "global", "international",
    "annual", "edition", "online", "virtual", "the", "and",
}

COUNTRY_ALIASES: dict[str, str] = {
    **{name.lower(): code for code, name in COUNTRY_NAMES.items()},
    "usa": "US", "united states": "US", "u.s.": "US", "u.s.a.": "US", "america": "US",
    "uk": "GB", "united kingdom": "GB", "england": "GB", "scotland": "GB",
    "mexico": "MX", "méxico": "MX", "peru": "PE", "perú": "PE", "colombia": "CO",
    "brasil": "BR", "brazil": "BR", "espana": "ES", "españa": "ES", "spain": "ES",
    "deutschland": "DE", "germany": "DE", "india": "IN", "japan": "JP", "canada": "CA",
}


def normalize_text(value: str) -> str:
    if not value:
        return ""
    text = strip_accents(html.unescape(value)).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(value: str, drop_generic: bool = False) -> set[str]:
    tokens = {t for t in normalize_text(value).split() if t not in STOPWORDS and len(t) > 2}
    if drop_generic:
        tokens -= GENERIC_EVENT_WORDS
    return tokens


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dice(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


def normalize_url(url: str | None) -> str:
    """Canonical form for duplicate detection. Keeps meaningful query params only."""
    if not url:
        return ""
    candidate = url.strip()
    if candidate.startswith("//"):
        candidate = "https:" + candidate
    if not re.match(r"^https?://", candidate, re.IGNORECASE):
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    host = parsed.netloc.lower()
    host = re.sub(r"^www\.", "", host)
    host = re.sub(r":(80|443)$", "", host)
    path = re.sub(r"/+$", "", parsed.path) or "/"
    query = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")
    ]
    query.sort()
    return urlunparse(("https", host, path, "", urlencode(query), ""))


def domain_of(url: str | None) -> str:
    if not url:
        return ""
    try:
        return re.sub(r"^www\.", "", urlparse(url).netloc.lower())
    except ValueError:
        return ""


def registrable_domain(url: str | None) -> str:
    """Small heuristic; enough for official-domain checks without a PSL dependency."""
    host = domain_of(url)
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    if parts[-2] in {"co", "com", "org", "net", "gov", "edu", "ac"} and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def slugify(value: str, max_length: int = 90) -> str:
    text = normalize_text(value)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:max_length].strip("-") or "oportunidad"


def extract_year(*texts: str) -> int | None:
    blob = " ".join(t for t in texts if t)
    matches = re.findall(r"\b(20[2-3][0-9])\b", blob)
    if not matches:
        return None
    # Prefer the most frequent year; ties resolved by the first occurrence.
    return max(sorted(set(matches)), key=lambda y: (matches.count(y), -matches.index(y)))


def clean_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", value)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p\s*>", "\n\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate(value: str, length: int = 280) -> str:
    text = re.sub(r"\s+", " ", (value or "")).strip()
    if len(text) <= length:
        return text
    cut = text[:length].rsplit(" ", 1)[0]
    return f"{cut}…"


def guess_country(*texts: str) -> str | None:
    blob = " ".join(t for t in texts if t).lower()
    for alias, code in sorted(COUNTRY_ALIASES.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{re.escape(alias)}\b", blob):
            return code
    return None


def country_code_from_name(value: str | None) -> str | None:
    """Resolve a country name or ISO code to alpha-2 (used by schema.org data)."""
    if not value:
        return None
    raw = value.strip()
    try:
        import pycountry

        if len(raw) == 2:
            match = pycountry.countries.get(alpha_2=raw.upper())
            if match:
                return match.alpha_2
        if len(raw) == 3:
            match = pycountry.countries.get(alpha_3=raw.upper())
            if match:
                return match.alpha_2
        direct = pycountry.countries.get(name=raw)
        if direct:
            return direct.alpha_2
        normalized = normalize_text(raw)
        for country in pycountry.countries:
            if normalize_text(country.name) == normalized:
                return country.alpha_2
        try:
            fuzzy = pycountry.countries.search_fuzzy(raw)
            if fuzzy:
                return fuzzy[0].alpha_2
        except LookupError:
            pass
    except Exception:  # pragma: no cover - defensive
        pass
    return guess_country(raw)


def country_name_from_code(code: str | None) -> str | None:
    if not code:
        return None
    if code.upper() in COUNTRY_NAMES:
        return COUNTRY_NAMES[code.upper()]
    try:
        import pycountry

        match = pycountry.countries.get(alpha_2=code.upper())
        return match.name if match else code.upper()
    except Exception:  # pragma: no cover
        return code.upper()


def search_blob(*values: str | None) -> str:
    return normalize_text(" ".join(v for v in values if v))
