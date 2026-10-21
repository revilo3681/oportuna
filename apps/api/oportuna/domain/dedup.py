"""Duplicate detection. Exact signals merge; ambiguity always goes to review."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from oportuna.domain.normalize import (
    dice,
    jaccard,
    normalize_url,
    tokenize,
)


@dataclass(frozen=True)
class DedupRecord:
    name: str
    organizer: str | None = None
    canonical_url: str | None = None
    city: str | None = None
    country: str | None = None
    modality: str | None = None
    description: str | None = None
    event_start: datetime | None = None
    event_end: datetime | None = None
    edition_year: int | None = None


@dataclass
class DedupResult:
    score: float
    reasons: list[dict] = field(default_factory=list)
    auto_merge: bool = False
    review: bool = False


def _date_similarity(a: DedupRecord, b: DedupRecord) -> float:
    if not a.event_start or not b.event_start:
        return 0.0
    delta = abs((a.event_start - b.event_start).total_seconds())
    if delta <= 86400:
        return 1.0
    if delta <= 3 * 86400:
        return 0.85
    if delta <= 10 * 86400:
        return 0.5
    return 0.0


def _location_similarity(a: DedupRecord, b: DedupRecord) -> float:
    a_online = (a.modality or "").lower() == "online"
    b_online = (b.modality or "").lower() == "online"
    if a_online and b_online:
        return 1.0
    if a.country and b.country:
        if a.country != b.country:
            return 0.0
        if a.city and b.city:
            return 1.0 if a.city.strip().lower() == b.city.strip().lower() else 0.7
        return 0.8
    if a.city and b.city and a.city.strip().lower() == b.city.strip().lower():
        return 0.9
    return 0.0


def compare(
    a: DedupRecord,
    b: DedupRecord,
    *,
    review_threshold: float = 0.78,
    merge_threshold: float = 0.95,
) -> DedupResult:
    reasons: list[dict] = []
    url_a, url_b = normalize_url(a.canonical_url), normalize_url(b.canonical_url)
    same_url = bool(url_a and url_b and url_a == url_b)

    name_score = dice(tokenize(a.name, drop_generic=True), tokenize(b.name, drop_generic=True))
    if name_score < 0.2:
        name_score = dice(tokenize(a.name), tokenize(b.name))
    org_score = dice(tokenize(a.organizer or ""), tokenize(b.organizer or ""))
    location_score = _location_similarity(a, b)
    date_score = _date_similarity(a, b)
    desc_score = jaccard(tokenize(a.description or ""), tokenize(b.description or ""))

    reasons.append({"code": "url", "label": "URL canónica idéntica" if same_url else "URL distinta", "value": round(float(same_url), 2)})
    reasons.append({"code": "name", "label": "Similitud de nombre", "value": round(name_score, 2)})
    reasons.append({"code": "organizer", "label": "Organizador coincidente", "value": round(org_score, 2)})
    reasons.append({"code": "dates", "label": "Fechas compatibles", "value": round(date_score, 2)})
    reasons.append({"code": "location", "label": "Ubicación/modalidad compatible", "value": round(location_score, 2)})

    # Different editions must never be merged, even with similar titles.
    if a.edition_year and b.edition_year and a.edition_year != b.edition_year:
        reasons.append(
            {
                "code": "edition",
                "label": f"Ediciones distintas ({a.edition_year} vs {b.edition_year})",
                "value": 0.0,
            }
        )
        return DedupResult(score=0.28, reasons=reasons, auto_merge=False, review=False)

    date_gap_days = None
    if a.event_start and b.event_start:
        date_gap_days = abs((a.event_start - b.event_start).total_seconds()) / 86400

    if same_url and date_gap_days is not None and date_gap_days > 1:
        # A calendar series can share one page URL across several occurrences.
        # Same page + clearly different dates means distinct events, not duplicates.
        reasons.append(
            {
                "code": "series",
                "label": "Misma página, fechas distintas: serie recurrente",
                "value": 0.0,
            }
        )
        return DedupResult(score=0.42, reasons=reasons, auto_merge=False, review=False)

    if same_url:
        score = 1.0
    else:
        score = (
            name_score * 0.45
            + org_score * 0.2
            + date_score * 0.15
            + location_score * 0.1
            + desc_score * 0.1
        )

    edition_compatible = not (a.edition_year and b.edition_year) or a.edition_year == b.edition_year
    date_ambiguity = same_url and bool(a.event_start) != bool(b.event_start)
    exact_identity = same_url or (name_score >= 0.92 and org_score >= 0.8)
    auto_merge = bool(
        score >= merge_threshold
        and edition_compatible
        and exact_identity
        and not date_ambiguity
        and not (a.edition_year and b.edition_year and a.edition_year != b.edition_year)
    )
    review = (not auto_merge) and edition_compatible and (score >= review_threshold or date_ambiguity)

    return DedupResult(score=round(score, 3), reasons=reasons, auto_merge=auto_merge, review=review)
