from __future__ import annotations

from datetime import UTC

from tests.conftest import create_opportunity, create_user

UTC = UTC


def test_catalog_only_lists_published_open_opportunities(client, session_factory):
    session = session_factory()
    create_opportunity(session, slug="visible-one", title="Visible One")
    create_opportunity(
        session,
        slug="hidden-one",
        title="Hidden One",
        published=False,
        review_state="needs_review",
        verification_state="pending",
    )
    create_opportunity(session, slug="closed-one", title="Closed One", lifecycle="closed")
    session.close()

    response = client.get("/api/opportunities")
    assert response.status_code == 200
    payload = response.json()
    slugs = [item["slug"] for item in payload["items"]]
    assert slugs == ["visible-one"]
    assert payload["total"] == 1
    assert payload["items"][0]["verification"]["state"] == "verified"


def test_catalog_filters_by_tech_modality_and_cost(client, session_factory):
    session = session_factory()
    create_opportunity(session, slug="ai-online", tags=["ai"], modality="online", cost_type="free")
    create_opportunity(
        session,
        slug="robotics-onsite",
        tags=["robotics"],
        modality="presencial",
        cost_type="paid",
        country="US",
    )
    session.close()

    response = client.get("/api/opportunities?tech=ai&modality=online&cost=free")
    payload = response.json()
    assert [item["slug"] for item in payload["items"]] == ["ai-online"]

    response = client.get("/api/opportunities?tech=robotics")
    assert [item["slug"] for item in response.json()["items"]] == ["robotics-onsite"]


def test_detail_returns_provenance_and_hides_unpublished(client, session_factory):
    session = session_factory()
    create_opportunity(session, slug="public-detail")
    create_opportunity(session, slug="private-detail", published=False, review_state="needs_review")
    session.close()

    response = client.get("/api/opportunities/public-detail")
    assert response.status_code == 200
    payload = response.json()
    assert payload["slug"] == "public-detail"
    assert payload["sources"]
    assert payload["provenance"] == []  # no provenance rows in this fixture
    assert payload["next_steps"]

    assert client.get("/api/opportunities/private-detail").status_code == 404


def test_registration_login_profile_and_saved_flow(client):
    register = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "long-enough-password", "display_name": "Nueva"},
    )
    assert register.status_code == 200, register.text
    assert register.json()["user"]["email"] == "new@example.com"
    assert client.get("/api/auth/me").json()["user"]["email"] == "new@example.com"

    profile = client.put(
        "/api/profile",
        json={
            "interests": ["ai", "hackathons"],
            "modalities": ["online"],
            "country": "PE",
            "availability": {"days": ["sat", "sun"], "slots": ["morning"]},
            "time_preferences": ["2-3h"],
            "level": "principiante",
            "goals": ["aprender"],
        },
    )
    assert profile.status_code == 200, profile.text
    body = profile.json()["profile"]
    assert body["completeness"] > 0
    assert body["onboarded_at"] is not None

    reset = client.delete("/api/profile")
    assert reset.status_code == 200
    assert reset.json()["profile"]["interests"] == []


def test_saved_requires_auth_and_roundtrips(client, auth_client, session_factory):
    session = session_factory()
    create_opportunity(session, slug="save-me")
    session.close()

    from fastapi.testclient import TestClient

    from oportuna.main import app

    with TestClient(app) as anonymous_client:
        anonymous = anonymous_client.delete("/api/saved/save-me")
        assert anonymous.status_code == 401

    response = auth_client.put("/api/saved/save-me", json={"state": "following"})
    assert response.status_code == 200, response.text
    assert response.json()["tracking"]["state"] == "following"

    saved = auth_client.get("/api/saved")
    assert saved.status_code == 200
    assert [item["slug"] for item in saved.json()["items"]] == ["save-me"]
    assert saved.json()["items"][0]["tracking"]["state"] == "following"

    calendar = auth_client.get("/api/calendar")
    assert calendar.status_code == 200
    assert calendar.json()["items"]

    ics = auth_client.get("/api/calendar.ics")
    assert ics.status_code == 200
    assert ics.headers["content-type"].startswith("text/calendar")
    assert "BEGIN:VCALENDAR" in ics.text


def test_admin_review_approval_publishes_and_audits(client, admin_client, session_factory):
    session = session_factory()
    create_opportunity(
        session,
        slug="pending-approval",
        title="Pending Approval",
        published=False,
        review_state="needs_review",
        verification_state="pending",
        confidence=0.5,
    )
    create_user(session, email="normal@example.com", password="normal-password-123")
    session.close()

    review = admin_client.get("/api/admin/review")
    assert review.status_code == 200
    ids = [item["id"] for item in review.json()["items"]]
    assert ids

    opportunity_id = ids[0]
    approve = admin_client.post(
        f"/api/admin/opportunities/{opportunity_id}/approve", json={"note": "Revisado a mano"}
    )
    assert approve.status_code == 200, approve.text

    detail = admin_client.get("/api/opportunities/pending-approval")
    assert detail.status_code == 200
    assert detail.json()["verification"]["published"] is True

    audit = admin_client.get("/api/admin/audit")
    assert any(row["field"] == "review_state" for row in audit.json()["items"])


def test_normal_user_cannot_access_admin(client, auth_client, session_factory):
    assert auth_client.get("/api/admin/stats").status_code == 403


def test_admin_stats_requires_admin(client):
    assert client.get("/api/admin/stats").status_code == 401


def test_dashboard_reports_real_counts(client, session_factory):
    session = session_factory()
    create_opportunity(session, slug="dash-one", deadline_days=3)
    create_opportunity(session, slug="dash-two", deadline_days=30)
    session.close()

    response = client.get("/api/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["open_total"] >= 2
    assert payload["summary"]["upcoming"] >= 1
    assert payload["priority"]


def test_assistant_is_grounded_and_refuses_to_invent(client, session_factory):
    session = session_factory()
    create_opportunity(
        session,
        slug="ai-free-online",
        title="AI Free Online Hackathon",
        tags=["ai", "ml"],
        modality="online",
        cost_type="free",
        deadline_days=10,
        country="PE",
    )
    session.close()

    response = client.post(
        "/api/assistant/ask",
        json={"question": "¿Qué hackathons de IA online gratis puedo hacer este mes?"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["grounding"]["uses_llm"] is False
    assert payload["items"]
    assert payload["citations"]
    assert "No inventaré" not in payload["answer"]

    empty = client.post(
        "/api/assistant/ask",
        json={"question": "¿Becas de robótica cuántica en Marte este mes?"},
    )
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert "No hay coincidencias" in empty.json()["answer"]


def test_opportunity_ics_export(client, session_factory):
    session = session_factory()
    create_opportunity(session, slug="ics-export", title="ICS Export Hackathon", deadline_days=5)
    session.close()

    response = client.get("/api/opportunities/ics-export/ics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    assert "ICS Export Hackathon" in response.text
    assert "BEGIN:VEVENT" in response.text
