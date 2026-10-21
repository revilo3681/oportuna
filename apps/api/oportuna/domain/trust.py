"""Explainable confidence and strict publication gates.

Confidence is computed from observable signals only. It is never "100% because an
LLM read a page", and a reachable form never proves that registration is open.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

UTC = UTC


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class TrustSignals:
    source_authority: int = 50
    # ``confirmed`` means the adapter saw the opportunity on the organizer's own
    # platform (official listing, platform of record, official calendar). A link
    # that merely shares a domain with a blog is not confirmation.
    confirmed: bool = False
    official_domain_match: bool = False
    platform_of_record: bool = False
    has_official_url: bool = False
    has_registration_url: bool = False
    has_event_dates: bool = False
    dates_coherent: bool = True
    contradictions: int = 0
    provenance_fields: int = 0
    verified_checks: int = 0
    last_checked_at: datetime | None = None
    now: datetime | None = None


@dataclass
class ConfidenceResult:
    score: float
    verification_state: str
    reasons: list[dict] = field(default_factory=list)


def _age_days(checked: datetime | None, now: datetime) -> int | None:
    if checked is None:
        return None
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=UTC)
    return max(int((now - checked).total_seconds() // 86400), 0)


def compute_confidence(signals: TrustSignals) -> ConfidenceResult:
    now = signals.now or _utcnow()
    reasons: list[dict] = []

    authority = max(0.0, min(1.0, signals.source_authority / 100))
    reasons.append(
        {
            "code": "authority",
            "label": f"Autoridad de la fuente: {signals.source_authority}/100",
            "impact": "positive" if authority >= 0.7 else "neutral",
            "weight": round(authority * 0.28, 3),
        }
    )

    official = 1.0 if signals.official_domain_match else (0.65 if signals.platform_of_record else 0.25)
    if signals.official_domain_match:
        reasons.append(
            {"code": "official", "label": "Confirmado en el dominio oficial", "impact": "positive", "weight": 0.22}
        )
    elif signals.platform_of_record:
        reasons.append(
            {
                "code": "platform",
                "label": "Publicado en la plataforma de referencia del evento",
                "impact": "positive",
                "weight": 0.15,
            }
        )
    elif signals.has_official_url:
        reasons.append(
            {"code": "official_link", "label": "Enlace oficial presente, sin confirmar dominio", "impact": "neutral", "weight": 0.0}
        )

    age = _age_days(signals.last_checked_at, now)
    if age is None:
        recency = 0.15
        reasons.append({"code": "recency", "label": "Sin comprobación reciente registrada", "impact": "negative", "weight": 0.0})
    elif age <= 7:
        recency = 1.0
        reasons.append({"code": "recency", "label": f"Comprobado hace {age} d", "impact": "positive", "weight": 0.16})
    elif age <= 21:
        recency = 0.8
        reasons.append({"code": "recency", "label": f"Comprobado hace {age} d", "impact": "positive", "weight": 0.13})
    elif age <= 60:
        recency = 0.5
        reasons.append({"code": "recency", "label": f"Última comprobación hace {age} d", "impact": "neutral", "weight": 0.05})
    else:
        recency = 0.2
        reasons.append({"code": "recency", "label": f"Datos con {age} d sin revisar", "impact": "negative", "weight": 0.0})

    coherent = 1.0 if signals.dates_coherent else 0.3
    if signals.dates_coherent:
        reasons.append({"code": "coherence", "label": "Fechas y datos coherentes", "impact": "positive", "weight": 0.14})
    else:
        reasons.append({"code": "coherence", "label": "Incoherencia entre fechas", "impact": "negative", "weight": 0.0})

    register = 1.0 if signals.has_registration_url else 0.35
    if signals.has_registration_url:
        reasons.append(
            {
                "code": "registration_link",
                "label": "Enlace de registro localizado (no implica inscripción abierta)",
                "impact": "neutral",
                "weight": 0.08,
            }
        )

    completeness = min(
        1.0,
        0.25 * int(signals.has_official_url)
        + 0.35 * int(signals.has_event_dates)
        + 0.2 * int(signals.has_registration_url)
        + 0.2 * min(signals.provenance_fields / 5, 1.0),
    )
    if completeness < 0.6:
        reasons.append({"code": "completeness", "label": "Faltan datos esenciales por confirmar", "impact": "negative", "weight": 0.0})

    raw = (
        authority * 0.28
        + official * 0.22
        + recency * 0.16
        + coherent * 0.14
        + register * 0.08
        + completeness * 0.12
    )
    penalty = min(signals.contradictions, 3) * 0.12
    if signals.contradictions:
        reasons.append(
            {
                "code": "conflicts",
                "label": f"{signals.contradictions} contradicción(es) entre fuentes",
                "impact": "negative",
                "weight": -penalty,
            }
        )
    score = max(0.05, min(0.98, raw - penalty))

    if signals.contradictions > 0:
        state = "conflict"
    elif signals.confirmed and signals.has_event_dates and score >= 0.55:
        state = "verified"
    else:
        state = "pending"

    return ConfidenceResult(round(score, 3), state, reasons)


@dataclass(frozen=True)
class PublishDecision:
    publish: bool
    review_state: str
    reason: str


def publication_decision(
    *,
    verification_state: str,
    confidence: float,
    lifecycle: str,
    official_url: str | None,
    last_checked_at: datetime | None,
    contradictions: int,
    has_actionable_date: bool = True,
    thresholds: dict | None = None,
    now: datetime | None = None,
) -> PublishDecision:
    """Strict auto-publication. Everything ambiguous goes to the review queue.

    This implements the product decision: broad discovery, but only validated
    records reach the public catalog; the rest is visible to administrators.
    """
    thresholds = thresholds or {}
    min_confidence = float(thresholds.get("min_confidence", 0.70))
    max_age_days = int(thresholds.get("max_age_days", 21))
    current = now or _utcnow()

    blockers: list[str] = []
    if lifecycle not in {"open", "rolling"}:
        blockers.append("la convocatoria no está abierta")
    if not official_url:
        blockers.append("falta el enlace oficial")
    if verification_state != "verified":
        blockers.append(f"estado de verificación: {verification_state}")
    if confidence < min_confidence:
        blockers.append(f"confianza {confidence:.2f} < {min_confidence:.2f}")
    if contradictions > 0:
        blockers.append("hay contradicciones sin resolver")
    if not has_actionable_date:
        blockers.append("no hay fecha límite ni fecha de celebración confirmada")
    if last_checked_at is None:
        blockers.append("no hay comprobación registrada")
    else:
        checked = last_checked_at if last_checked_at.tzinfo else last_checked_at.replace(tzinfo=UTC)
        age = int((current - checked).total_seconds() // 86400)
        if age > max_age_days:
            blockers.append(f"última comprobación hace {age} días")

    if blockers:
        return PublishDecision(False, "needs_review", "Revisión requerida: " + "; ".join(blockers))
    return PublishDecision(True, "published", "Validación automática superada")
