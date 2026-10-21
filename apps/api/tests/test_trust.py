from datetime import UTC, datetime, timedelta

from oportuna.domain.trust import TrustSignals, compute_confidence, publication_decision

UTC = UTC
NOW = datetime(2026, 10, 20, tzinfo=UTC)


def signals(**overrides) -> TrustSignals:
    base = dict(
        source_authority=85,
        confirmed=True,
        official_domain_match=True,
        platform_of_record=False,
        has_official_url=True,
        has_registration_url=True,
        has_event_dates=True,
        dates_coherent=True,
        contradictions=0,
        provenance_fields=8,
        last_checked_at=NOW,
        now=NOW,
    )
    base.update(overrides)
    return TrustSignals(**base)


def test_confidence_is_explainable_and_bounded():
    result = compute_confidence(signals())
    assert 0.0 < result.score <= 0.98
    assert result.verification_state == "verified"
    assert result.reasons
    assert all({"code", "label", "impact"} <= set(reason) for reason in result.reasons)


def test_contradiction_forces_conflict_state():
    result = compute_confidence(signals(contradictions=2))
    assert result.verification_state == "conflict"
    assert result.score < compute_confidence(signals()).score
    assert any(reason["code"] == "conflicts" for reason in result.reasons)


def test_unconfirmed_source_cannot_be_verified():
    result = compute_confidence(signals(confirmed=False, official_domain_match=True, source_authority=45))
    assert result.verification_state == "pending"


def test_strict_publication_gate_accepts_verified_fresh_record():
    decision = publication_decision(
        verification_state="verified",
        confidence=0.85,
        lifecycle="open",
        official_url="https://example.com/",
        last_checked_at=NOW,
        contradictions=0,
        has_actionable_date=True,
        now=NOW,
    )
    assert decision.publish is True
    assert decision.review_state == "published"


def test_publication_rejects_low_confidence_and_stale():
    decision = publication_decision(
        verification_state="verified",
        confidence=0.4,
        lifecycle="open",
        official_url="https://example.com/",
        last_checked_at=NOW - timedelta(days=90),
        contradictions=0,
        has_actionable_date=True,
        now=NOW,
    )
    assert decision.publish is False
    assert decision.review_state == "needs_review"
    assert "confianza" in decision.reason and "comprobación" in decision.reason


def test_publication_rejects_dateless_record():
    decision = publication_decision(
        verification_state="verified",
        confidence=0.9,
        lifecycle="open",
        official_url="https://example.com/",
        last_checked_at=NOW,
        contradictions=0,
        has_actionable_date=False,
        now=NOW,
    )
    assert decision.publish is False
    assert "fecha" in decision.reason


def test_closed_lifecycle_is_never_published_as_open():
    decision = publication_decision(
        verification_state="closed",
        confidence=0.9,
        lifecycle="finished",
        official_url="https://example.com/",
        last_checked_at=NOW,
        contradictions=0,
        has_actionable_date=True,
        now=NOW,
    )
    assert decision.publish is False
