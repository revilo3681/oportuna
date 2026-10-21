"""Authentication, progressive profile, saved opportunities and personal calendar."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from oportuna.api.deps import (
    clear_session_cookie,
    current_user,
    optional_user,
    set_session_cookie,
)
from oportuna.api.schemas import LoginIn, ProfileIn, RegisterIn, SavedIn, SavedPatchIn
from oportuna.api.serializers import opportunity_card, profile_dict, public_user
from oportuna.db.base import get_db
from oportuna.db.models import Opportunity, OpportunitySource, Profile, SavedOpportunity, User
from oportuna.domain.dates import (
    deadline_label,
    effective_deadline,
    ensure_utc,
    utcnow,
)
from oportuna.domain.ics import build_calendar
from oportuna.security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["account"])

LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_ATTEMPTS = 8
_login_attempts: dict[str, list[float]] = {}


def _rate_limited(key: str) -> bool:
    now = time.time()
    attempts = [t for t in _login_attempts.get(key, []) if now - t < LOGIN_WINDOW_SECONDS]
    _login_attempts[key] = attempts
    return len(attempts) >= LOGIN_MAX_ATTEMPTS


def _register_failure(key: str) -> None:
    _login_attempts.setdefault(key, []).append(time.time())


def _auth_response(response: Response, user: User) -> dict:
    token = create_access_token(str(user.id), user.role)
    set_session_cookie(response, token)
    return {"token": token, "user": public_user(user)}


@router.post("/auth/register")
def register(payload: RegisterIn, response: Response, db: Session = Depends(get_db)):
    existing = db.scalars(select(User).where(User.email == payload.email)).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email.")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or payload.email.split("@")[0],
        role="user",
    )
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id))
    db.commit()
    db.refresh(user)
    return _auth_response(response, user)


@router.post("/auth/login")
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    key = payload.email
    if _rate_limited(key):
        raise HTTPException(
            status_code=429, detail="Demasiados intentos. Espera unos minutos antes de reintentar."
        )
    user = db.scalars(select(User).where(User.email == payload.email)).first()
    if user is None or user.deleted_at is not None or not verify_password(
        payload.password, user.password_hash
    ):
        _register_failure(key)
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos.")
    user.last_login_at = utcnow()
    db.commit()
    _login_attempts.pop(key, None)
    return _auth_response(response, user)


@router.post("/auth/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/auth/me")
def me(user: User = Depends(optional_user)):
    if user is None:
        return {"user": None}
    return {"user": public_user(user)}


# --------------------------------------------------------------------------- profile


def _profile_or_create(db: Session, user: User) -> Profile:
    profile = db.scalars(select(Profile).where(Profile.user_id == user.id)).first()
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.flush()
    return profile


@router.get("/profile")
def get_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    _profile_or_create(db, user)
    db.commit()
    db.refresh(user)
    return {"profile": profile_dict(user)}


@router.put("/profile")
def update_profile(
    payload: ProfileIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_create(db, user)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(profile, key, value)
    core_ready = bool(
        profile.interests
        and profile.modalities
        and (profile.availability or {}).get("days")
    )
    if core_ready and profile.onboarded_at is None:
        profile.onboarded_at = utcnow()
    profile.updated_at = utcnow()
    db.commit()
    db.refresh(user)
    return {"profile": profile_dict(user)}


@router.delete("/profile")
def delete_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = _profile_or_create(db, user)
    profile.interests = []
    profile.level = None
    profile.goals = []
    profile.country = None
    profile.city = None
    profile.travel_radius_km = None
    profile.modalities = []
    profile.languages = []
    profile.availability = {}
    profile.time_preferences = []
    profile.budget = None
    profile.eligibility = {}
    profile.preferences = {}
    profile.onboarded_at = None
    profile.updated_at = utcnow()
    db.commit()
    db.refresh(user)
    return {"ok": True, "profile": profile_dict(user)}


@router.delete("/account")
def delete_account(
    response: Response,
    confirm: str = Query(default=""),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if confirm != "eliminar":
        raise HTTPException(
            status_code=400,
            detail='Para eliminar la cuenta envía confirm=eliminar. La acción es irreversible.',
        )
    profile = _profile_or_create(db, user)
    for field_name in (
        "interests",
        "goals",
        "modalities",
        "languages",
        "time_preferences",
    ):
        setattr(profile, field_name, [])
    profile.availability = {}
    profile.eligibility = {}
    profile.preferences = {}
    profile.country = None
    profile.city = None
    profile.level = None
    profile.budget = None
    profile.onboarded_at = None
    user.email = f"eliminada-{uuid.uuid4()}@oportuna.invalid"
    user.display_name = "Cuenta eliminada"
    user.password_hash = hash_password(uuid.uuid4().hex + uuid.uuid4().hex)
    user.deleted_at = utcnow()
    for saved in db.scalars(select(SavedOpportunity).where(SavedOpportunity.user_id == user.id)).all():
        db.delete(saved)
    db.commit()
    clear_session_cookie(response)
    return {"ok": True}


# --------------------------------------------------------------------------- saved


def _saved_row(db: Session, user: User, opportunity_id) -> SavedOpportunity | None:
    return db.scalars(
        select(SavedOpportunity).where(
            SavedOpportunity.user_id == user.id,
            SavedOpportunity.opportunity_id == opportunity_id,
        )
    ).first()


def _find_opportunity(db: Session, slug: str) -> Opportunity:
    opportunity = db.scalars(
        select(Opportunity)
        .where(Opportunity.slug == slug, Opportunity.published.is_(True), Opportunity.is_demo.is_(False))
        .options(selectinload(Opportunity.sources).joinedload(OpportunitySource.source))
    ).first()
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    return opportunity


@router.get("/saved")
def list_saved(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(SavedOpportunity)
        .where(SavedOpportunity.user_id == user.id)
        .options(
            joinedload(SavedOpportunity.opportunity)
            .selectinload(Opportunity.sources)
            .joinedload(OpportunitySource.source)
        )
        .order_by(SavedOpportunity.updated_at.desc())
    ).all()
    items = []
    for row in rows:
        card = opportunity_card(row.opportunity)
        card["tracking"] = {
            "state": row.state,
            "notes": row.notes,
            "useful": row.useful,
            "updated_at": ensure_utc(row.updated_at).isoformat(),
        }
        items.append(card)
    return {"items": items, "total": len(items)}


@router.put("/saved/{slug}")
def save_opportunity(
    slug: str,
    payload: SavedIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    opportunity = _find_opportunity(db, slug)
    row = _saved_row(db, user, opportunity.id)
    if row is None:
        row = SavedOpportunity(user_id=user.id, opportunity_id=opportunity.id)
        db.add(row)
    row.state = payload.state
    if payload.notes is not None:
        row.notes = payload.notes
    if payload.useful is not None:
        row.useful = payload.useful
    db.commit()
    db.refresh(row)
    return {
        "ok": True,
        "tracking": {
            "state": row.state,
            "notes": row.notes,
            "useful": row.useful,
        },
    }


@router.patch("/saved/{slug}")
def patch_saved(
    slug: str,
    payload: SavedPatchIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    opportunity = _find_opportunity(db, slug)
    row = _saved_row(db, user, opportunity.id)
    if row is None:
        raise HTTPException(status_code=404, detail="No tienes esta oportunidad guardada")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    return {
        "ok": True,
        "tracking": {"state": row.state, "notes": row.notes, "useful": row.useful},
    }


@router.delete("/saved/{slug}")
def unsave_opportunity(
    slug: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    opportunity = _find_opportunity(db, slug)
    row = _saved_row(db, user, opportunity.id)
    if row is not None:
        db.delete(row)
        db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- calendar


def _calendar_items(db: Session, user: User, start: datetime, end: datetime) -> list[dict]:
    rows = db.scalars(
        select(SavedOpportunity)
        .where(SavedOpportunity.user_id == user.id, SavedOpportunity.state != "dismissed")
        .options(joinedload(SavedOpportunity.opportunity))
    ).all()
    items: list[dict] = []
    for row in rows:
        opportunity = row.opportunity
        deadline = effective_deadline(
            opportunity.registration_deadline, opportunity.submission_deadline
        )
        if deadline and start <= ensure_utc(deadline) <= end:
            items.append(
                {
                    "uid": opportunity.slug,
                    "slug": opportunity.slug,
                    "title": opportunity.title,
                    "date": ensure_utc(deadline).isoformat(),
                    "kind": "deadline",
                    "label": deadline_label(deadline),
                    "url": opportunity.official_url,
                    "tracking": row.state,
                }
            )
        if opportunity.event_start and start <= ensure_utc(opportunity.event_start) <= end:
            items.append(
                {
                    "uid": opportunity.slug,
                    "slug": opportunity.slug,
                    "title": opportunity.title,
                    "date": ensure_utc(opportunity.event_start).isoformat(),
                    "end": ensure_utc(opportunity.event_end).isoformat()
                    if opportunity.event_end
                    else None,
                    "kind": "event",
                    "label": opportunity.city or "Evento",
                    "url": opportunity.official_url,
                    "tracking": row.state,
                }
            )
    items.sort(key=lambda item: item["date"])
    return items


@router.get("/calendar")
def calendar(
    start: datetime | None = None,
    end: datetime | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    now = utcnow()
    start = ensure_utc(start) if start else now - timedelta(days=14)
    end = ensure_utc(end) if end else now + timedelta(days=180)
    if end <= start:
        raise HTTPException(status_code=400, detail="El rango de fechas no es válido")
    return {
        "items": _calendar_items(db, user, start, end),
        "range": {"start": start.isoformat(), "end": end.isoformat()},
    }


@router.get("/calendar.ics")
def calendar_ics(
    start: datetime | None = None,
    end: datetime | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    now = utcnow()
    start = ensure_utc(start) if start else now - timedelta(days=14)
    end = ensure_utc(end) if end else now + timedelta(days=180)
    items = _calendar_items(db, user, start, end)
    payload = build_calendar(
        [
            {
                "uid": f"{item['uid']}-{item['kind']}",
                "title": item["title"],
                "date": datetime.fromisoformat(item["date"]),
                "end": datetime.fromisoformat(item["end"]) if item.get("end") else None,
                "kind": item["kind"],
                "description": item["label"],
                "url": item["url"],
            }
            for item in items
        ],
        name="Oportuna — mi calendario",
    )
    return Response(
        content=payload,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="oportuna.ics"'},
    )


# --------------------------------------------------------------------------- alerts


@router.get("/alerts")
def alerts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    from oportuna.db.models import Alert

    rows = db.scalars(
        select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at.desc()).limit(50)
    ).all()
    return {
        "items": [
            {
                "id": str(row.id),
                "kind": row.kind,
                "title": row.title,
                "body": row.body,
                "payload": row.payload,
                "read": row.read_at is not None,
                "created_at": ensure_utc(row.created_at).isoformat(),
            }
            for row in rows
        ],
        "unread": sum(1 for row in rows if row.read_at is None),
    }
