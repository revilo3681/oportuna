"""Grounded assistant: deterministic retrieval plus optional local Ollama."""

from __future__ import annotations

import calendar
import logging
import re
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from oportuna.ai.grounding import (
    SYSTEM_PROMPT,
    build_prompt,
    cited_numbers,
    context_for,
    renumber_citations,
    sanitize_answer,
    semantic_search,
)
from oportuna.ai.local import LocalAIError, LocalAIStatus, get_local_ai
from oportuna.api.deps import optional_user
from oportuna.api.schemas import AskIn, ChatIn
from oportuna.api.serializers import (
    opportunity_card,
    profile_dict,
    rank_candidate,
)
from oportuna.config import get_settings
from oportuna.db.base import get_db
from oportuna.db.models import AssistantQuery, Opportunity, OpportunitySource, User
from oportuna.domain.dates import utcnow
from oportuna.domain.ranking import rank_candidates
from oportuna.domain.taxonomy import (
    CATEGORIES,
    MODALITIES,
    TECH_TAGS,
    country_name,
    extract_tech_tags,
)

logger = logging.getLogger("oportuna.assistant")
router = APIRouter(tags=["assistant"])

NO_MATCH = (
    "No hay coincidencias publicadas con esos filtros en este momento. "
    "Puedes ampliar la búsqueda quitando modalidad, país o precio, o revisar el catálogo completo. "
    "No inventaré una oportunidad para completar la respuesta."
)

CATEGORY_WORDS = {
    "hackathons": ["hackathon", "hackaton", "datathon", "ctf", "competencia", "concurso", "reto"],
    "formacion": ["beca", "scholarship", "fellowship", "curso", "bootcamp", "formacion", "grant"],
    "startups": ["startup", "aceleradora", "accelerator", "incubadora", "founder", "emprender"],
    "eventos": ["conferencia", "charla", "meetup", "webinar", "taller", "workshop", "evento"],
}


def parse_question(question: str) -> dict:
    text = question.lower()
    filters: dict = {"categories": [], "tech": [], "modality": None, "free": False, "days": None, "country": None}

    for category, words in CATEGORY_WORDS.items():
        if any(word in text for word in words):
            filters["categories"].append(category)

    filters["tech"] = extract_tech_tags(question)[:3]

    if re.search(r"\b(online|remoto|virtual|en linea|en línea)\b", text):
        filters["modality"] = "online"
    elif re.search(r"\bpresencial|en persona\b", text):
        filters["modality"] = "presencial"
    elif re.search(r"\bhibrid", text):
        filters["modality"] = "hibrida"

    if re.search(r"\b(gratis|gratuit|free|sin coste|cero presupuesto|presupuesto cero)\b", text):
        filters["free"] = True

    if re.search(r"\bhoy\b", text):
        filters["days"] = 1
    elif re.search(r"\besta semana\b|\b7 dias\b|\b7 días\b", text):
        filters["days"] = 7
    elif re.search(r"\bfin de semana\b", text):
        filters["days"] = 4
    elif re.search(r"\beste mes\b|\bmes\b", text):
        now = utcnow()
        last_day = calendar.monthrange(now.year, now.month)[1]
        filters["days"] = (datetime(now.year, now.month, last_day, tzinfo=UTC) - now).days + 1

    months = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
        "septiembre", "octubre", "noviembre", "diciembre",
    ]
    for index, month in enumerate(months, start=1):
        if month in text:
            now = utcnow()
            year = now.year if index >= now.month else now.year + 1
            start = datetime(year, index, 1, tzinfo=UTC)
            last_day = calendar.monthrange(year, index)[1]
            end = datetime(year, index, last_day, 23, 59, tzinfo=UTC)
            filters["from"] = start.date().isoformat()
            filters["days"] = max((end - now).days + 1, 1)
            break

    if "español" in text or "en espanol" in text:
        filters["language"] = "es"
    elif "inglés" in text or "ingles" in text or "english" in text:
        filters["language"] = "en"

    for word, code in {
        "perú": "PE", "peru": "PE", "méxico": "MX", "mexico": "MX", "colombia": "CO",
        "chile": "CL", "argentina": "AR", "españa": "ES", "espana": "ES", "brasil": "BR",
        "brazil": "BR", "india": "IN", "estados unidos": "US", "usa": "US",
    }.items():
        if re.search(rf"\b{re.escape(word)}\b", text):
            filters["country"] = code
            break

    filters["recognized"] = bool(
        filters["categories"]
        or filters["tech"]
        or filters["modality"]
        or filters["free"]
        or filters["days"]
        or filters["country"]
        or filters["language"]
    )
    filters["country"] = filters["country"] or None
    filters["language"] = filters.get("language")
    return filters




def _conditions(filters: dict, now) -> list:
    conditions = [
        Opportunity.published.is_(True),
        Opportunity.is_demo.is_(False),
        Opportunity.lifecycle.in_(["open", "rolling"]),
    ]
    if filters["categories"]:
        conditions.append(Opportunity.category.in_(filters["categories"]))
    for tag in filters["tech"]:
        conditions.append(Opportunity.tech_tags_text.contains(f"|{tag}|"))
    if filters["modality"]:
        conditions.append(Opportunity.modality == filters["modality"])
    if filters["free"]:
        conditions.append(Opportunity.cost_type == "free")
    if filters["country"]:
        conditions.append(Opportunity.country == filters["country"])
    if filters.get("language"):
        conditions.append(Opportunity.language == filters["language"])

    effective = func.coalesce(Opportunity.registration_deadline, Opportunity.submission_deadline)
    if filters["days"]:
        limit_date = now + timedelta(days=int(filters["days"]))
        conditions.append(
            or_(
                effective.between(now, limit_date),
                Opportunity.event_start.between(now, limit_date),
            )
        )
    return conditions


def _query_rows(db: Session, filters: dict, limit: int = 60) -> list[Opportunity]:
    now = utcnow()
    return list(
        db.scalars(
            select(Opportunity)
            .where(*_conditions(filters, now))
            .options(selectinload(Opportunity.sources).joinedload(OpportunitySource.source))
            .order_by(Opportunity.quality_score.desc())
            .limit(limit)
        ).all()
    )


def _profile_for(viewer: User | None) -> dict | None:
    if viewer is None:
        return None
    profile_data = profile_dict(viewer)
    return profile_data if profile_data["interests"] else None


def _serialize_ranked(rows: list[Opportunity], viewer: User | None, *, limit: int = 6) -> list[dict]:
    if not rows:
        return []
    profile = _profile_for(viewer)
    ranked = rank_candidates([rank_candidate(row) for row in rows], profile, limit=limit, diversity=True)
    by_id = {str(row.id): row for row in rows}
    items = []
    for item in ranked:
        opportunity = by_id.get(item.candidate.id)
        if opportunity is not None:
            items.append(opportunity_card(opportunity, reasons=item.reasons))
    return items


def _serialize_in_order(rows: list[Opportunity], viewer: User | None, *, limit: int = 8) -> list[dict]:
    if not rows:
        return []
    profile = _profile_for(viewer)
    ranked = rank_candidates([rank_candidate(row) for row in rows], profile, limit=len(rows), diversity=False)
    reasons = {item.candidate.id: item.reasons for item in ranked}
    return [
        opportunity_card(row, reasons=reasons.get(str(row.id), []))
        for row in rows[:limit]
    ]


def _describe_filters(filters: dict) -> str:
    return ", ".join(
        label
        for label in [
            ", ".join(CATEGORIES.get(c, {}).get("label", c) for c in filters["categories"]),
            ", ".join(TECH_TAGS.get(t, {}).get("label", t) for t in filters["tech"]),
            MODALITIES.get(filters["modality"], "") if filters["modality"] else "",
            "gratis" if filters["free"] else "",
            f"en {filters['days']} días" if filters["days"] else "",
            f"en {country_name(filters['country'])}" if filters["country"] else "",
        ]
        if label
    )


def _rule_answer(items: list[dict], filters: dict) -> str:
    if not items:
        return NO_MATCH
    described = _describe_filters(filters)
    lines = []
    for index, item in enumerate(items, start=1):
        deadline = item["deadline"]["label"] if item["deadline"]["effective"] else "Sin fecha límite publicada"
        lines.append(
            f"{index}. {item['title']} — {item['category']['label']} · "
            f"{item['modality']['label']} · {deadline}."
        )
    return (
        f"Encontré {len(items)} oportunidades abiertas y publicadas"
        + (f" para {described}" if described else "")
        + ":\n\n"
        + "\n".join(lines)
        + "\n\nTodas proceden del catálogo verificado y conservan su fuente y última comprobación. "
        "No afirmo que cumplas los requisitos de elegibilidad: revisa la ficha y la web oficial antes de inscribirte."
    )


def _merge_rows(primary: list[Opportunity], semantic: list[Opportunity], limit: int = 10) -> list[Opportunity]:
    merged: list[Opportunity] = []
    seen: set[str] = set()
    for row in [*semantic, *primary]:
        key = str(row.id)
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
        if len(merged) >= limit:
            break
    return merged


def _finalize(
    db: Session,
    viewer: User | None,
    question: str,
    filters: dict,
    answer: str,
    items: list[dict],
    *,
    mode: str,
    uses_llm: bool,
    status: LocalAIStatus | None,
    latency_ms: int,
    retrieved: int,
    semantic: bool,
    note: str,
    error: str | None = None,
) -> dict:
    citations = [
        {
            "slug": item["slug"],
            "title": item["title"],
            "official_url": item["official_url"],
            "source": (item.get("source") or {}).get("name"),
            "path": f"/oportunidades/{item['slug']}",
        }
        for item in items
    ]
    logged_filters = {key: value for key, value in filters.items() if value and key != "recognized"}
    logged_filters.update({"mode": mode, "uses_llm": uses_llm, "retrieved": retrieved})
    db.add(
        AssistantQuery(
            user_id=viewer.id if viewer else None,
            question=question,
            filters=logged_filters,
            result_count=len(items),
        )
    )
    db.commit()
    return {
        "answer": answer,
        "items": items,
        "filters": {key: value for key, value in filters.items() if value and key != "recognized"},
        "citations": citations,
        "grounding": {
            "mode": mode,
            "uses_llm": uses_llm,
            "published_only": True,
            "note": note,
            "model": status.model if status else None,
            "embed_model": status.embed_model if status else None,
            "latency_ms": latency_ms,
            "retrieved": retrieved,
            "semantic_search": semantic,
            "error": error,
        },
        "ai": {
            "available": bool(status and status.available),
            "enabled": bool(status and status.enabled),
            "model": status.model if status else None,
            "embed_model": status.embed_model if status else None,
            "detail": status.detail if status else None,
        },
    }


@router.get("/assistant/status")
async def assistant_status():
    status = await get_local_ai().status(force=True)
    return {
        "available": status.available,
        "enabled": status.enabled,
        "provider": "ollama",
        "model": status.model,
        "embed_model": status.embed_model,
        "models": list(status.models),
        "base_url": status.base_url,
        "detail": status.detail,
    }


@router.post("/assistant/ask")
def ask(
    payload: AskIn,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(optional_user),
):
    filters = parse_question(payload.question)
    rows = _query_rows(db, filters)
    items = _serialize_ranked(rows, viewer, limit=6)
    answer = _rule_answer(items, filters)
    return _finalize(
        db,
        viewer,
        payload.question,
        filters,
        answer,
        items,
        mode="catálogo verificado + reglas explícitas",
        uses_llm=False,
        status=None,
        latency_ms=0,
        retrieved=len(rows),
        semantic=False,
        note="Si no hay datos que respondan, el asistente lo dice en lugar de inventar.",
    )


@router.post("/assistant/chat")
async def chat(
    payload: ChatIn,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(optional_user),
):
    started = time.perf_counter()
    filters = parse_question(payload.question)
    rows = _query_rows(db, filters)
    status = await get_local_ai().status()
    used_semantic = False

    if payload.use_ai and status.available and (not filters["recognized"] or len(rows) < 6):
        semantic_rows = await semantic_search(db, payload.question, limit=10)
        if semantic_rows:
            rows = _merge_rows(rows, semantic_rows, limit=10)
            used_semantic = True

    if not rows:
        return _finalize(
            db,
            viewer,
            payload.question,
            filters,
            NO_MATCH,
            [],
            mode="rules" if not payload.use_ai or not status.available else "local-ai",
            uses_llm=False,
            status=status,
            latency_ms=int((time.perf_counter() - started) * 1000),
            retrieved=0,
            semantic=used_semantic,
            note="No se llamó al modelo porque el catálogo no devolvió oportunidades compatibles.",
        )

    if not payload.use_ai or not status.available:
        items = _serialize_ranked(rows, viewer, limit=6)
        answer = _rule_answer(items, filters)
        reason = (
            "IA local desactivada por el usuario; respondí con reglas."
            if not payload.use_ai
            else f"IA local no disponible ({status.detail}); respondí con reglas."
        )
        return _finalize(
            db,
            viewer,
            payload.question,
            filters,
            answer,
            items,
            mode="rules",
            uses_llm=False,
            status=status,
            latency_ms=int((time.perf_counter() - started) * 1000),
            retrieved=len(rows),
            semantic=used_semantic,
            note=reason,
            error=status.detail if not status.available else None,
        )

    context_rows = rows[: get_settings().llm_max_context_items]
    context, used = context_for(context_rows, limit=get_settings().llm_max_context_items)
    try:
        raw = await get_local_ai().generate(
            system=SYSTEM_PROMPT,
            prompt=build_prompt(payload.question, context),
        )
    except LocalAIError as exc:
        items = _serialize_ranked(rows, viewer, limit=6)
        answer = _rule_answer(items, filters) + f"\n\nLa IA local no respondió: {exc}. Respondí con reglas sobre el catálogo."
        return _finalize(
            db,
            viewer,
            payload.question,
            filters,
            answer,
            items,
            mode="rules-fallback",
            uses_llm=False,
            status=status,
            latency_ms=int((time.perf_counter() - started) * 1000),
            retrieved=len(rows),
            semantic=used_semantic,
            note="El modelo local falló; se mantuvo la respuesta determinista y las citas del catálogo.",
            error=str(exc),
        )

    answer = sanitize_answer(raw)
    cited = cited_numbers(answer, len(used))
    if cited:
        selected = [used[index - 1] for index in cited]
        answer, _ = renumber_citations(answer, cited)
        items = _serialize_in_order(selected, viewer, limit=len(selected))
    else:
        items = _serialize_in_order(used[:5], viewer, limit=5)
        answer += "\n\nFuentes consultadas: " + ", ".join(f"[{index}]" for index in range(1, len(items) + 1))

    return _finalize(
        db,
        viewer,
        payload.question,
        filters,
        answer,
        items,
        mode="local-ollama",
        uses_llm=True,
        status=status,
        latency_ms=int((time.perf_counter() - started) * 1000),
        retrieved=len(rows),
        semantic=used_semantic,
        note=(
            "Respuesta generada por un modelo local (Ollama) usando solo el contexto de oportunidades "
            "publicadas. Los enlaces y las fuentes se añaden desde la base de datos, no desde el modelo."
        ),
    )
