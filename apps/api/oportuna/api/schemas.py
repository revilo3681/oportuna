"""Pydantic request schemas with taxonomy validation."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from oportuna.domain.taxonomy import (
    BUDGETS,
    CATEGORIES,
    GOALS,
    LEVELS,
    MODALITIES,
    TECH_TAGS,
    TIME_BUCKETS,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


class RegisterIn(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=120)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.match(value):
            raise ValueError("Email no válido")
        return value

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()


class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return value.strip().lower()


class ProfileIn(BaseModel):
    interests: list[str] | None = None
    level: str | None = None
    goals: list[str] | None = None
    country: str | None = None
    city: str | None = None
    travel_radius_km: int | None = Field(default=None, ge=0, le=20000)
    modalities: list[str] | None = None
    languages: list[str] | None = None
    availability: dict | None = None
    time_preferences: list[str] | None = None
    budget: str | None = None
    eligibility: dict | None = None
    preferences: dict | None = None

    @field_validator("interests")
    @classmethod
    def valid_interests(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        allowed = set(TECH_TAGS) | set(CATEGORIES)
        unknown = [item for item in value if item not in allowed]
        if unknown:
            raise ValueError(f"Intereses no reconocidos: {', '.join(unknown)}")
        return list(dict.fromkeys(value))

    @field_validator("level")
    @classmethod
    def valid_level(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        if value not in LEVELS:
            raise ValueError("Nivel no válido")
        return value

    @field_validator("goals")
    @classmethod
    def valid_goals(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        unknown = [item for item in value if item not in GOALS]
        if unknown:
            raise ValueError(f"Objetivos no reconocidos: {', '.join(unknown)}")
        return list(dict.fromkeys(value))

    @field_validator("country")
    @classmethod
    def valid_country(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise ValueError("Usa un código de país ISO de dos letras")
        return value

    @field_validator("modalities")
    @classmethod
    def valid_modalities(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        allowed = set(MODALITIES) - {"unknown"}
        unknown = [item for item in value if item not in allowed]
        if unknown:
            raise ValueError(f"Modalidades no válidas: {', '.join(unknown)}")
        return list(dict.fromkeys(value))

    @field_validator("time_preferences")
    @classmethod
    def valid_time_preferences(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        unknown = [item for item in value if item not in TIME_BUCKETS]
        if unknown:
            raise ValueError(f"Bloques de tiempo no válidos: {', '.join(unknown)}")
        return list(dict.fromkeys(value))

    @field_validator("budget")
    @classmethod
    def valid_budget(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        if value not in BUDGETS:
            raise ValueError("Presupuesto no válido")
        return value

    @field_validator("availability")
    @classmethod
    def valid_availability(cls, value: dict | None) -> dict | None:
        if value is None:
            return value
        days = value.get("days", []) or []
        slots = value.get("slots", []) or []
        allowed_days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
        allowed_slots = {"morning", "afternoon", "evening"}
        if any(day not in allowed_days for day in days):
            raise ValueError("Días de disponibilidad no válidos")
        if any(slot not in allowed_slots for slot in slots):
            raise ValueError("Franjas horarias no válidas")
        return {"days": days, "slots": slots}

    @field_validator("eligibility")
    @classmethod
    def valid_eligibility(cls, value: dict | None) -> dict | None:
        if value is None:
            return value
        age = value.get("age")
        if age is not None and (not isinstance(age, int) or age < 13 or age > 120):
            raise ValueError("Edad no válida")
        return value


class SavedIn(BaseModel):
    state: Literal[
        "saved", "following", "applied", "accepted", "rejected", "attended", "dismissed"
    ] = "saved"
    notes: str | None = Field(default=None, max_length=2000)
    useful: bool | None = None


class SavedPatchIn(BaseModel):
    state: Literal[
        "saved", "following", "applied", "accepted", "rejected", "attended", "dismissed"
    ] | None = None
    notes: str | None = Field(default=None, max_length=2000)
    useful: bool | None = None


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class ChatIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    use_ai: bool = True


class SourceIn(BaseModel):
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=2, max_length=160)
    kind: Literal["ics", "rss", "jsonld", "devpost", "github"]
    homepage_url: str = Field(min_length=8, max_length=500)
    endpoint: str = Field(min_length=8, max_length=1000)
    region: str = "global"
    languages: list[str] = Field(default_factory=list)
    authority: int = Field(default=60, ge=0, le=100)
    frequency_minutes: int = Field(default=720, ge=60, le=10080)
    enabled: bool = False
    config: dict = Field(default_factory=dict)
    access_notes: str = Field(default="", max_length=2000)
    terms_url: str | None = None

    @field_validator("homepage_url", "endpoint")
    @classmethod
    def valid_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("Debe ser una URL http(s)")
        return value


class SourcePatchIn(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    endpoint: str | None = None
    homepage_url: str | None = None
    region: str | None = None
    languages: list[str] | None = None
    authority: int | None = Field(default=None, ge=0, le=100)
    frequency_minutes: int | None = Field(default=None, ge=60, le=10080)
    enabled: bool | None = None
    config: dict | None = None
    access_notes: str | None = Field(default=None, max_length=2000)
    terms_url: str | None = None
    disabled_reason: str | None = None

    @field_validator("endpoint", "homepage_url")
    @classmethod
    def validate_urls(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.startswith(("http://", "https://")):
            raise ValueError("Debe ser una URL http(s)")
        return value


class OpportunityPatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=400)
    summary: str | None = Field(default=None, max_length=600)
    description: str | None = Field(default=None, max_length=20000)
    category: Literal["hackathons", "eventos", "formacion", "startups"] | None = None
    tech_tags: list[str] | None = None
    modality: Literal["online", "presencial", "hibrida", "unknown"] | None = None
    country: str | None = None
    city: str | None = None
    language: str | None = None
    organizer: str | None = None
    official_url: str | None = None
    registration_url: str | None = None
    event_start: datetime | None = None
    event_end: datetime | None = None
    registration_deadline: datetime | None = None
    submission_deadline: datetime | None = None
    cost_type: Literal["free", "paid", "unknown"] | None = None
    eligibility: dict | None = None
    prizes: list | None = None
    lifecycle: Literal["open", "closed", "cancelled", "finished", "rolling", "unknown"] | None = None

    @field_validator("tech_tags")
    @classmethod
    def valid_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        unknown = [tag for tag in value if tag not in TECH_TAGS]
        if unknown:
            raise ValueError(f"Etiquetas no reconocidas: {', '.join(unknown)}")
        return list(dict.fromkeys(value))

    @field_validator("country")
    @classmethod
    def country_code(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        value = value.upper()
        if len(value) != 2:
            raise ValueError("Código de país ISO de dos letras")
        return value


class ReviewNoteIn(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class ResolveDuplicateIn(BaseModel):
    action: Literal["merge", "reject"]
    note: str | None = Field(default=None, max_length=1000)


class IngestIn(BaseModel):
    slugs: list[str] | None = None
