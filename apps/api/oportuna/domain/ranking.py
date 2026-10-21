"""Personalized ranking with explainable reasons and category diversity.

Weights come from the product spec (30/25/20/15/10) and are configurable so A/B
tests can change them without touching ranking logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from oportuna.domain.dates import deadline_urgency
from oportuna.domain.eligibility import EligibilityResult, assess_eligibility
from oportuna.domain.taxonomy import CATEGORIES, TECH_TAGS

UTC = UTC

DEFAULT_WEIGHTS = {
    "affinity": 0.30,
    "availability": 0.25,
    "eligibility": 0.20,
    "reliability": 0.15,
    "value": 0.10,
}

TIME_CAPACITY_MINUTES = {
    "15m": 15,
    "1h": 60,
    "2-3h": 180,
    "half-day": 330,
    "multi-day": 2880,
}

GOAL_CATEGORY_BOOST = {
    "aprender": ("formacion", "eventos"),
    "crear": ("hackathons",),
    "competir": ("hackathons",),
    "premios": ("hackathons",),
    "networking": ("eventos", "startups"),
    "carrera": ("startups", "formacion"),
}


@dataclass
class RankCandidate:
    id: str
    title: str
    category: str
    tech_tags: list[str] = field(default_factory=list)
    modality: str = "unknown"
    country: str | None = None
    city: str | None = None
    language: str | None = None
    cost_type: str = "unknown"
    cost_amount: float | None = None
    event_start: datetime | None = None
    event_end: datetime | None = None
    registration_deadline: datetime | None = None
    duration_minutes: int | None = None
    prep_time_minutes: int | None = None
    lifecycle: str = "open"
    verification_state: str = "pending"
    confidence: float = 0.0
    eligibility: dict = field(default_factory=dict)
    prizes: list = field(default_factory=list)
    team_min: int | None = None
    team_max: int | None = None
    organizer: str | None = None
    has_certificate: bool = False


@dataclass
class RankedCandidate:
    candidate: RankCandidate
    score: float
    components: dict[str, float]
    reasons: list[dict]
    eligibility: EligibilityResult


def _profile_interests(profile: dict) -> set[str]:
    return {i for i in (profile.get("interests") or []) if isinstance(i, str)}


def _affinity(candidate: RankCandidate, profile: dict | None) -> tuple[float, list[dict]]:
    if not profile:
        return 0.5, []
    interests = _profile_interests(profile)
    goals = profile.get("goals") or []
    reasons: list[dict] = []
    if not interests and not goals:
        return 0.5, []

    matched: list[str] = []
    tag_set = set(candidate.tech_tags)
    for interest in interests:
        if interest in tag_set:
            matched.append(TECH_TAGS.get(interest, {}).get("label", interest))
        elif interest == candidate.category:
            matched.append(CATEGORIES.get(candidate.category, {}).get("label", candidate.category))

    interest_score = 0.0
    if interests:
        interest_score = min(1.0, len(set(matched)) / max(len(interests), 1) * 1.6)
        if matched:
            interest_score = max(interest_score, 0.55)

    goal_match = any(candidate.category in GOAL_CATEGORY_BOOST.get(g, ()) for g in goals)
    goal_score = 1.0 if goal_match else (0.5 if goals else 0.5)

    level = profile.get("level")
    level_score = 0.6
    levels = candidate.eligibility.get("experience_levels") or []
    if level and levels:
        level_score = 1.0 if level in levels else 0.25
    elif level == "principiante" and candidate.category in {"formacion", "eventos"}:
        level_score = 0.8

    score = interest_score * 0.7 + goal_score * 0.2 + level_score * 0.1
    if matched:
        reasons.append(
            {
                "kind": "affinity",
                "label": "Te interesa " + ", ".join(sorted(set(matched))[:3]),
            }
        )
    elif goal_match:
        reasons.append({"kind": "affinity", "label": "Encaja con tus objetivos"})
    return min(max(score, 0.0), 1.0), reasons


def _deadline_score(deadline: datetime | None, lifecycle: str, now: datetime) -> tuple[float, dict | None]:
    if lifecycle in {"closed", "finished", "cancelled"}:
        return 0.05, {"kind": "availability", "label": "La convocatoria ya no está abierta"}
    urgency = deadline_urgency(deadline, now)
    mapping = {"imminent": 0.7, "soon": 0.92, "upcoming": 1.0, "distant": 0.85, "unknown": 0.62, "expired": 0.05}
    score = mapping.get(urgency, 0.62)
    reason = None
    if urgency == "imminent":
        reason = {"kind": "deadline", "label": "La inscripción cierra en menos de 48 h"}
    elif urgency == "soon":
        reason = {"kind": "deadline", "label": "La inscripción cierra esta semana"}
    return score, reason


def _availability(candidate: RankCandidate, profile: dict | None, now: datetime) -> tuple[float, list[dict]]:
    reasons: list[dict] = []
    deadline_score, deadline_reason = _deadline_score(candidate.registration_deadline, candidate.lifecycle, now)
    if deadline_reason:
        reasons.append(deadline_reason)

    modality_score = 0.7
    if profile:
        modalities = profile.get("modalities") or []
        if modalities and candidate.modality != "unknown":
            modality_score = 1.0 if candidate.modality in modalities else 0.3
            if candidate.modality in modalities and candidate.modality != "presencial":
                reasons.append({"kind": "modality", "label": "Modalidad " + ("online" if candidate.modality != "presencial" else candidate.modality)})

    time_score = 0.6
    if profile and candidate.duration_minutes:
        buckets = profile.get("time_preferences") or []
        capacities = [TIME_CAPACITY_MINUTES[b] for b in buckets if b in TIME_CAPACITY_MINUTES]
        capacity = max(capacities) if capacities else None
        commitment = candidate.duration_minutes + (candidate.prep_time_minutes or 0)
        if capacity:
            if commitment <= capacity:
                time_score = 1.0
                reasons.append({"kind": "time", "label": "Cabe en tu tiempo disponible"})
            elif commitment <= capacity * 1.6:
                time_score = 0.55
            else:
                time_score = 0.2
                reasons.append({"kind": "time", "label": "Compromiso mayor que tu disponibilidad declarada"})

    budget_score = 0.65
    if profile:
        budget = profile.get("budget")
        if budget == "free":
            budget_score = 1.0 if candidate.cost_type == "free" else (0.25 if candidate.cost_type == "paid" else 0.55)
        elif budget in {"paid", "any"}:
            budget_score = 1.0
        elif budget == "transport":
            budget_score = 1.0 if candidate.cost_type in {"free", "paid"} else 0.6

    score = deadline_score * 0.5 + modality_score * 0.15 + time_score * 0.2 + budget_score * 0.15
    return min(max(score, 0.0), 1.0), reasons


def _value(candidate: RankCandidate) -> tuple[float, list[dict]]:
    reasons: list[dict] = []
    base = {
        "hackathons": 0.72,
        "formacion": 0.78,
        "eventos": 0.62,
        "startups": 0.72,
    }.get(candidate.category, 0.55)
    if candidate.prizes:
        base += 0.12
        reasons.append({"kind": "value", "label": "Tiene premios"})
    if candidate.cost_type == "free":
        base += 0.08
        reasons.append({"kind": "value", "label": "Participación gratuita"})
    if candidate.has_certificate:
        base += 0.05
    if candidate.team_max and candidate.team_max > 1:
        base += 0.03
    return min(base, 1.0), reasons


def rank_candidates(
    candidates: list[RankCandidate],
    profile: dict | None,
    *,
    weights: dict | None = None,
    now: datetime | None = None,
    limit: int = 50,
    diversity: bool = True,
    max_per_category: int = 2,
) -> list[RankedCandidate]:
    weights = weights or DEFAULT_WEIGHTS
    current = now or datetime.now(UTC)
    ranked: list[RankedCandidate] = []

    eligibility_profile = None
    if profile:
        eligibility_profile = {
            "country": profile.get("country"),
            "age": profile.get("age"),
            "level": profile.get("level"),
            "eligibility": profile.get("eligibility") or {},
            "preferences": profile.get("preferences") or {},
        }

    for candidate in candidates:
        affinity, r_affinity = _affinity(candidate, profile)
        availability, r_availability = _availability(candidate, profile, current)
        eligibility = assess_eligibility(candidate.eligibility, eligibility_profile, modality=candidate.modality)
        eligibility_score = {"eligible": 1.0, "likely": 0.8, "unknown": 0.55, "ineligible": 0.05}[eligibility.verdict]
        reliability = min(max(candidate.confidence, 0.0), 1.0)
        value, r_value = _value(candidate)

        components = {
            "affinity": round(affinity, 3),
            "availability": round(availability, 3),
            "eligibility": round(eligibility_score, 3),
            "reliability": round(reliability, 3),
            "value": round(value, 3),
        }
        score = 100 * sum(components[key] * weights[key] for key in DEFAULT_WEIGHTS)
        if candidate.lifecycle in {"closed", "finished", "cancelled"}:
            score *= 0.2

        reasons = list(r_affinity) + list(r_availability)
        if eligibility.verdict == "ineligible":
            reasons.insert(0, {"kind": "eligibility", "label": "Requisitos no cumplidos"})
        elif eligibility.verdict == "unknown":
            reasons.append({"kind": "eligibility", "label": "Elegibilidad por confirmar"})
        elif eligibility.verdict == "likely":
            reasons.append({"kind": "eligibility", "label": "Posiblemente elegible; revisa los requisitos"})
        if candidate.verification_state == "verified":
            reasons.append({"kind": "trust", "label": f"Fuente verificada · confianza {int(candidate.confidence * 100)}%"})
        elif candidate.verification_state == "conflict":
            reasons.append({"kind": "trust", "label": "Información contradictoria"})
        reasons.extend(r_value)
        reasons = reasons[:5]

        ranked.append(
            RankedCandidate(
                candidate=candidate,
                score=round(score, 1),
                components=components,
                reasons=reasons,
                eligibility=eligibility,
            )
        )

    ranked.sort(key=lambda r: r.score, reverse=True)
    if not diversity:
        return ranked[:limit]

    selected: list[RankedCandidate] = []
    per_category: dict[str, int] = {}
    per_organizer: dict[str, int] = {}
    for item in ranked:
        category = item.candidate.category
        organizer = (item.candidate.organizer or "").strip().lower()
        if per_category.get(category, 0) >= max_per_category:
            continue
        if organizer and per_organizer.get(organizer, 0) >= max_per_category:
            continue
        selected.append(item)
        per_category[category] = per_category.get(category, 0) + 1
        if organizer:
            per_organizer[organizer] = per_organizer.get(organizer, 0) + 1
        if len(selected) >= limit:
            return selected

    for item in ranked:
        if len(selected) >= limit:
            break
        if item not in selected:
            selected.append(item)
    return selected


def baseline_quality(confidence: float, value: float, open_now: bool) -> float:
    """Anonymous ranking quality score stored for SQL sorting."""
    return round(confidence * 70 + value * 30 - (0 if open_now else 60), 2)


__all__ = [
    "DEFAULT_WEIGHTS",
    "RankCandidate",
    "RankedCandidate",
    "baseline_quality",
    "rank_candidates",
]
