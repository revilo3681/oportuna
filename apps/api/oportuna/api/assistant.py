"""Deterministic, catalog-grounded assistant.

No LLM is involved: the question is parsed into explicit filters, the verified
catalog is queried, and the answer cites each opportunity. When nothing matches,
it says so instead of inventing a result.
"""

from __future__ import annotations

import calendar
import re
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from oportuna.api.deps import optional_user
from oportuna.api.schemas import AskIn
from oportuna.api.serializers import (
    opportunity_card,
    profile_dict,
    rank_candidate,
)
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

router = APIRouter(tags=["assistant"])

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


@router.post("/assistant/ask")
def ask(
    payload: AskIn,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(optional_user),
):
    filters = parse_question(payload.question)
    now = utcnow()

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

    rows = db.scalars(
        select(Opportunity)
        .where(*conditions)
        .options(selectinload(Opportunity.sources).joinedload(OpportunitySource.source))
        .order_by(Opportunity.quality_score.desc())
        .limit(60)
    ).all()

    profile = None
    if viewer is not None:
        profile_data = profile_dict(viewer)
        if profile_data["interests"]:
            profile = profile_data

    ranked = rank_candidates([rank_candidate(row) for row in rows], profile, limit=6, diversity=True)
    by_id = {str(row.id): row for row in rows}
    items = []
    for item in ranked:
        opportunity = by_id.get(item.candidate.id)
        if opportunity is None:
            continue
        items.append(opportunity_card(opportunity, reasons=item.reasons))

    if items:
        described = ", ".join(
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
        lines = []
        for index, item in enumerate(items, start=1):
            deadline = item["deadline"]["label"] if item["deadline"]["effective"] else "Sin fecha límite publicada"
            lines.append(
                f"{index}. {item['title']} — {item['category']['label']} · "
                f"{item['modality']['label']} · {deadline}."
            )
        answer = (
            f"Encontré {len(items)} oportunidades abiertas y publicadas"
            + (f" para {described}" if described else "")
            + ":\n\n"
            + "\n".join(lines)
            + "\n\nTodas proceden del catálogo verificado y conservan su fuente y última comprobación. "
            "No afirmo que cumplas los requisitos de elegibilidad: revisa la ficha y la web oficial antes de inscribirte."
        )
    else:
        answer = (
            "No hay coincidencias publicadas con esos filtros en este momento. "
            "Puedes ampliar la búsqueda quitando modalidad, país o precio, o revisar el catálogo completo. "
            "No inventaré una oportunidad para completar la respuesta."
        )

    db.add(
        AssistantQuery(
            user_id=viewer.id if viewer else None,
            question=payload.question,
            filters={k: v for k, v in filters.items() if v},
            result_count=len(items),
        )
    )
    db.commit()

    return {
        "answer": answer,
        "items": items,
        "filters": {k: v for k, v in filters.items() if v and k != "recognized"},
        "citations": [
            {
                "slug": item["slug"],
                "title": item["title"],
                "official_url": item["official_url"],
                "source": (item.get("source") or {}).get("name"),
                "path": f"/oportunidades/{item['slug']}",
            }
            for item in items
        ],
        "grounding": {
            "mode": "catálogo verificado + reglas explícitas",
            "uses_llm": False,
            "published_only": True,
            "note": "Si no hay datos que respondan, el asistente lo dice en lugar de inventar.",
        },
    }
