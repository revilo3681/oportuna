from datetime import UTC, datetime, timedelta

from oportuna.domain.dedup import DedupRecord, compare

UTC = UTC
NOW = datetime(2026, 10, 20, tzinfo=UTC)


def test_same_canonical_url_merges_automatically():
    a = DedupRecord(name="Global AI Hackathon 2026", canonical_url="https://hack.example.com/")
    b = DedupRecord(name="Global AI Hackathon", canonical_url="https://hack.example.com/?utm_source=x")
    result = compare(a, b)
    assert result.score == 1.0
    assert result.auto_merge is True


def test_same_series_url_with_different_dates_stays_separate():
    a = DedupRecord(
        name="Statistics and Data Science Seminar",
        canonical_url="https://calendar.mit.edu/event/seminar",
        event_start=NOW,
        edition_year=2026,
    )
    b = DedupRecord(
        name="Statistics and Data Science Seminar",
        canonical_url="https://calendar.mit.edu/event/seminar",
        event_start=NOW + timedelta(days=2),
        edition_year=2026,
    )
    result = compare(a, b)
    assert result.auto_merge is False
    assert result.review is False
    assert any(reason["code"] == "series" for reason in result.reasons)


def test_different_editions_never_merge():
    a = DedupRecord(
        name="Global AI Hackathon 2025",
        canonical_url="https://hack.example.com/2025",
        edition_year=2025,
        event_start=NOW,
    )
    b = DedupRecord(
        name="Global AI Hackathon 2026",
        canonical_url="https://hack.example.com/2026",
        edition_year=2026,
        event_start=NOW + timedelta(days=365),
    )
    result = compare(a, b)
    assert result.auto_merge is False
    assert result.review is False
    assert any(reason["code"] == "edition" for reason in result.reasons)
    assert result.score < 0.4


def test_ambiguous_similar_event_goes_to_review_not_merge():
    a = DedupRecord(
        name="Lima AI Hackathon",
        organizer="Comunidad IA Perú",
        canonical_url="https://a.example.com/",
        event_start=NOW + timedelta(days=10),
        event_end=NOW + timedelta(days=11),
        city="Lima",
        country="PE",
        modality="presencial",
        description="Construye soluciones de inteligencia artificial en 48 horas.",
        edition_year=2026,
    )
    b = DedupRecord(
        name="Lima AI Hackathon 2026",
        organizer="Comunidad IA Peru",
        canonical_url="https://b.example.com/",
        event_start=NOW + timedelta(days=11),
        event_end=NOW + timedelta(days=12),
        city="Lima",
        country="PE",
        modality="presencial",
        description="Hackathon de inteligencia artificial y datos abiertos.",
        edition_year=2026,
    )
    result = compare(a, b)
    assert result.auto_merge is False
    assert result.review is True
    assert 0.0 < result.score <= 1.0


def test_unrelated_events_are_not_duplicates():
    a = DedupRecord(name="Hackathon de robótica", canonical_url="https://robot.example.com/", edition_year=2026)
    b = DedupRecord(name="Conferencia de diseño gráfico", canonical_url="https://design.example.com/", edition_year=2026)
    result = compare(a, b)
    assert result.auto_merge is False
    assert result.review is False
    assert result.score < 0.4
