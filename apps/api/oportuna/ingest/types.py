"""Normalized ingestion record shared by every adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawOpportunity:
    external_id: str
    title: str
    official_url: str
    source_url: str
    summary: str = ""
    description: str = ""
    category: str | None = None
    subcategory: str | None = None
    tech_tags: list[str] = field(default_factory=list)
    modality: str = "unknown"
    country: str | None = None
    city: str | None = None
    timezone: str | None = None
    language: str | None = None
    organizer: str | None = None
    organizer_url: str | None = None
    registration_url: str | None = None
    event_start: datetime | None = None
    event_end: datetime | None = None
    registration_open_at: datetime | None = None
    registration_deadline: datetime | None = None
    submission_deadline: datetime | None = None
    results_at: datetime | None = None
    rolling: bool = False
    cancelled: bool = False
    stated_lifecycle: str | None = None
    duration_minutes: int | None = None
    prep_time_minutes: int | None = None
    cost_type: str = "unknown"
    cost_amount: float | None = None
    currency: str | None = None
    prizes: list = field(default_factory=list)
    eligibility: dict = field(default_factory=dict)
    team_min: int | None = None
    team_max: int | None = None
    phases: list = field(default_factory=list)
    confirmed: bool = False
    confirmation_note: str = ""
    raw_excerpt: str = ""
    extra: dict = field(default_factory=dict)

    def has_actionable_date(self) -> bool:
        return bool(
            self.registration_deadline
            or self.submission_deadline
            or self.event_start
            or self.rolling
        )
