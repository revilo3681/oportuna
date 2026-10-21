from datetime import UTC, datetime, timedelta

from oportuna.domain.dates import (
    deadline_urgency,
    derive_lifecycle,
    effective_deadline,
    parse_date_range,
    parse_deadline,
    parse_stated_deadline,
)

UTC = UTC


def test_devpost_range_parsing_keeps_year():
    start, end, note = parse_date_range("Aug 31 - Oct 23, 2026")
    assert note == ""
    assert start is not None and start.year == 2026 and start.month == 8 and start.day == 31
    assert end is not None and end.month == 10 and end.day == 23


def test_range_without_year_is_rejected_instead_of_guessed():
    start, end, note = parse_date_range("Aug 31 - Oct 23")
    assert start is None and end is None
    assert "año" in note


def test_cross_year_range_infers_next_year_for_end():
    start, end, _ = parse_date_range("Dec 28 - Jan 4, 2026")
    assert start is not None and (start.year, start.month, start.day) == (2025, 12, 28)
    assert end is not None and (end.year, end.month, end.day) == (2026, 1, 4)


def test_stated_deadline_is_parsed_only_with_trigger():
    deadline = parse_stated_deadline("Application Deadline: 22 November 2026", now=datetime(2026, 10, 20, tzinfo=UTC))
    assert deadline is not None
    assert (deadline.year, deadline.month, deadline.day) == (2026, 11, 22)
    assert parse_stated_deadline("Applications are now open in November 2026") is None


def test_deadline_is_end_of_day():
    deadline = parse_deadline("2026-11-22")
    assert deadline is not None
    assert deadline.hour == 23 and deadline.minute == 59


def test_lifecycle_does_not_confuse_link_with_open_registration():
    now = datetime(2026, 10, 20, tzinfo=UTC)
    lifecycle, registration_state = derive_lifecycle(
        event_start=now + timedelta(days=20),
        event_end=now + timedelta(days=22),
        registration_deadline=None,
        now=now,
    )
    assert lifecycle == "open"
    assert registration_state == "unknown"


def test_lifecycle_closes_after_deadline():
    now = datetime(2026, 10, 20, tzinfo=UTC)
    lifecycle, registration_state = derive_lifecycle(
        event_start=now + timedelta(days=20),
        event_end=now + timedelta(days=22),
        registration_deadline=now - timedelta(days=1),
        now=now,
    )
    assert lifecycle == "closed"
    assert registration_state == "closed"


def test_rolling_is_explicitly_open():
    lifecycle, registration_state = derive_lifecycle(
        event_start=None,
        event_end=None,
        registration_deadline=None,
        rolling=True,
    )
    assert lifecycle == "rolling"
    assert registration_state == "open"


def test_effective_deadline_prefers_earliest_stated_date():
    registration = datetime(2026, 11, 1, tzinfo=UTC)
    submission = datetime(2026, 10, 25, tzinfo=UTC)
    assert effective_deadline(registration, submission) == submission


def test_urgency_buckets():
    now = datetime(2026, 10, 20, tzinfo=UTC)
    assert deadline_urgency(now + timedelta(days=1), now) == "imminent"
    assert deadline_urgency(now + timedelta(days=5), now) == "soon"
    assert deadline_urgency(now + timedelta(days=20), now) == "upcoming"
    assert deadline_urgency(now - timedelta(days=1), now) == "expired"
