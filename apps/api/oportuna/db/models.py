"""SQLAlchemy models for Oportuna.

Design rules encoded here:
- event dates and application deadlines are distinct nullable fields (never inferred);
- every material field can carry its own provenance row;
- verification state and confidence are stored, explainable and auditable;
- publication is gated separately from ingestion (review_state).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oportuna.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


JSONType = JSON().with_variant(JSONB(), "postgresql")
Timestamp = DateTime(timezone=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(20), default="user")  # user | admin
    locale: Mapped[str] = mapped_column(String(8), default="es")
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(Timestamp)
    deleted_at: Mapped[datetime | None] = mapped_column(Timestamp)

    profile: Mapped[Profile | None] = relationship(back_populates="user", uselist=False)
    saved: Mapped[list[SavedOpportunity]] = relationship(back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    interests: Mapped[list] = mapped_column(JSONType, default=list)
    level: Mapped[str | None] = mapped_column(String(24))  # principiante | intermedio | avanzado
    goals: Mapped[list] = mapped_column(JSONType, default=list)
    country: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(120))
    travel_radius_km: Mapped[int | None] = mapped_column(Integer)
    modalities: Mapped[list] = mapped_column(JSONType, default=list)  # online | presencial | hibrida
    languages: Mapped[list] = mapped_column(JSONType, default=list)
    availability: Mapped[dict] = mapped_column(JSONType, default=dict)
    time_preferences: Mapped[list] = mapped_column(JSONType, default=list)  # 15m | 1h | 2-3h | half-day | multi-day
    budget: Mapped[str | None] = mapped_column(String(24))  # free | transport | paid | any
    eligibility: Mapped[dict] = mapped_column(JSONType, default=dict)
    preferences: Mapped[dict] = mapped_column(JSONType, default=dict)
    onboarded_at: Mapped[datetime | None] = mapped_column(Timestamp)
    updated_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="profile")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(24))  # devpost | ics | rss | jsonld | github | manual
    homepage_url: Mapped[str] = mapped_column(String(500))
    endpoint: Mapped[str] = mapped_column(String(1000))
    region: Mapped[str] = mapped_column(String(40), default="Global")
    languages: Mapped[list] = mapped_column(JSONType, default=list)
    config: Mapped[dict] = mapped_column(JSONType, default=dict)
    authority: Mapped[int] = mapped_column(Integer, default=60)  # 0..100 source reputation signal
    access_notes: Mapped[str] = mapped_column(Text, default="")
    terms_url: Mapped[str | None] = mapped_column(String(500))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    frequency_minutes: Mapped[int] = mapped_column(Integer, default=360)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    last_run_at: Mapped[datetime | None] = mapped_column(Timestamp)
    last_status: Mapped[str | None] = mapped_column(String(24))
    last_error: Mapped[str | None] = mapped_column(Text)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    disabled_reason: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, onupdate=utcnow)

    opportunities: Mapped[list[OpportunitySource]] = relationship(back_populates="source")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(400))
    summary: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")

    category: Mapped[str] = mapped_column(String(40), index=True)
    subcategory: Mapped[str | None] = mapped_column(String(60))
    tech_tags: Mapped[list] = mapped_column(JSONType, default=list)
    tech_tags_text: Mapped[str] = mapped_column(String(500), default="", index=True)
    modality: Mapped[str] = mapped_column(String(20), default="unknown")  # online | presencial | hibrida | unknown
    country: Mapped[str | None] = mapped_column(String(2), index=True)
    city: Mapped[str | None] = mapped_column(String(120))
    timezone: Mapped[str | None] = mapped_column(String(64))
    language: Mapped[str | None] = mapped_column(String(8))
    organizer: Mapped[str | None] = mapped_column(String(200))
    organizer_url: Mapped[str | None] = mapped_column(String(600))

    official_url: Mapped[str] = mapped_column(String(1000))
    registration_url: Mapped[str | None] = mapped_column(String(1000))
    canonical_url: Mapped[str] = mapped_column(String(1000), index=True)
    edition_year: Mapped[int | None] = mapped_column(Integer, index=True)

    event_start: Mapped[datetime | None] = mapped_column(Timestamp, index=True)
    event_end: Mapped[datetime | None] = mapped_column(Timestamp)
    registration_open_at: Mapped[datetime | None] = mapped_column(Timestamp)
    registration_deadline: Mapped[datetime | None] = mapped_column(Timestamp, index=True)
    submission_deadline: Mapped[datetime | None] = mapped_column(Timestamp)
    results_at: Mapped[datetime | None] = mapped_column(Timestamp)
    phases: Mapped[list] = mapped_column(JSONType, default=list)
    rolling: Mapped[bool] = mapped_column(Boolean, default=False)

    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    prep_time_minutes: Mapped[int | None] = mapped_column(Integer)
    commitment_note: Mapped[str | None] = mapped_column(Text)

    cost_type: Mapped[str] = mapped_column(String(20), default="unknown")  # free | paid | unknown
    cost_amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(3))
    prizes: Mapped[list] = mapped_column(JSONType, default=list)
    eligibility: Mapped[dict] = mapped_column(JSONType, default=dict)
    team_min: Mapped[int | None] = mapped_column(Integer)
    team_max: Mapped[int | None] = mapped_column(Integer)

    lifecycle: Mapped[str] = mapped_column(String(20), default="open", index=True)
    # open | closed | cancelled | finished | rolling | unknown
    registration_state: Mapped[str] = mapped_column(String(20), default="unknown")
    registration_state_source: Mapped[str | None] = mapped_column(String(120))

    verification_state: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    # verified | pending | conflict | closed
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_reasons: Mapped[list] = mapped_column(JSONType, default=list)
    conflict_count: Mapped[int] = mapped_column(Integer, default=0)
    review_state: Mapped[str] = mapped_column(String(24), default="needs_review", index=True)
    # published | needs_review | hidden | approved
    review_reason: Mapped[str | None] = mapped_column(Text)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(Timestamp)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    first_seen_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    last_checked_at: Mapped[datetime | None] = mapped_column(Timestamp)
    last_verified_at: Mapped[datetime | None] = mapped_column(Timestamp)
    last_changed_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    search_text: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, onupdate=utcnow)

    sources: Mapped[list[OpportunitySource]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )
    provenance: Mapped[list[FieldProvenance]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )
    changes: Mapped[list[OpportunityChange]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_opportunities_published_lifecycle", "published", "lifecycle"),
        Index("ix_opportunities_public_feed", "published", "is_demo", "registration_deadline"),
    )


class OpportunitySource(Base):
    __tablename__ = "opportunity_sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )
    source_url: Mapped[str] = mapped_column(String(1000))
    external_id: Mapped[str | None] = mapped_column(String(200))
    retrieved_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    raw_excerpt: Mapped[str] = mapped_column(Text, default="")
    authority: Mapped[int] = mapped_column(Integer, default=60)

    opportunity: Mapped[Opportunity] = relationship(back_populates="sources")
    source: Mapped[Source] = relationship(back_populates="opportunities")

    __table_args__ = (
        UniqueConstraint("opportunity_id", "source_id", "source_url", name="uq_opp_source_url"),
    )


class FieldProvenance(Base):
    __tablename__ = "field_provenance"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    field: Mapped[str] = mapped_column(String(64), index=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="SET NULL")
    )
    value: Mapped[dict] = mapped_column(JSONType, default=dict)
    observed_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    method: Mapped[str] = mapped_column(String(32), default="ingest")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text)

    opportunity: Mapped[Opportunity] = relationship(back_populates="provenance")

    __table_args__ = (Index("ix_provenance_opp_field", "opportunity_id", "field"),)


class OpportunityChange(Base):
    __tablename__ = "opportunity_changes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    field: Mapped[str] = mapped_column(String(64))
    old_value: Mapped[dict | None] = mapped_column(JSONType)
    new_value: Mapped[dict | None] = mapped_column(JSONType)
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("sources.id"))
    actor: Mapped[str] = mapped_column(String(24), default="system")
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, index=True)

    opportunity: Mapped[Opportunity] = relationship(back_populates="changes")


class VerificationCheck(Base):
    __tablename__ = "verification_checks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    checked_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, index=True)
    outcome: Mapped[str] = mapped_column(String(24))  # confirmed | reachable | unreachable | conflict
    http_status: Mapped[int | None] = mapped_column(Integer)
    evidence: Mapped[dict] = mapped_column(JSONType, default=dict)
    notes: Mapped[str | None] = mapped_column(Text)


class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    left_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    right_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list] = mapped_column(JSONType, default=list)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(Timestamp)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))

    __table_args__ = (
        UniqueConstraint("left_id", "right_id", name="uq_duplicate_pair"),
    )


class SavedOpportunity(Base):
    __tablename__ = "saved_opportunities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    state: Mapped[str] = mapped_column(String(20), default="saved")
    # saved | following | applied | accepted | rejected | attended | dismissed
    useful: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="saved")
    opportunity: Mapped[Opportunity] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "opportunity_id", name="uq_saved_user_opp"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(32))  # new_match | deadline_soon | changed | digest
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    scheduled_for: Mapped[datetime | None] = mapped_column(Timestamp)
    sent_at: Mapped[datetime | None] = mapped_column(Timestamp)
    read_at: Mapped[datetime | None] = mapped_column(Timestamp)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="SET NULL"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(Timestamp)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running | ok | error
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    items_created: Mapped[int] = mapped_column(Integer, default=0)
    items_updated: Mapped[int] = mapped_column(Integer, default=0)
    items_duplicated: Mapped[int] = mapped_column(Integer, default=0)
    items_published: Mapped[int] = mapped_column(Integer, default=0)
    items_review: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[dict] = mapped_column(JSONType, default=dict)
    error_detail: Mapped[str | None] = mapped_column(Text)


class AssistantQuery(Base):
    __tablename__ = "assistant_queries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    question: Mapped[str] = mapped_column(Text)
    filters: Mapped[dict] = mapped_column(JSONType, default=dict)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
