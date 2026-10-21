from __future__ import annotations

import pytest

from oportuna.ai.grounding import renumber_citations, sanitize_answer
from oportuna.ai.local import LocalAIStatus


def test_sanitize_answer_removes_urls_markdown_and_invalid_citations():
    raw = (
        "Mira **esto** en https://fake.example.com y también [1, 2, 3].\n"
        "* primer punto [1]\n* segundo punto [2]"
    )
    cleaned = sanitize_answer(raw)
    assert "https://" not in cleaned
    assert "**" not in cleaned
    assert "[1, 2, 3]" not in cleaned
    assert "• primer punto [1]" in cleaned
    assert "• segundo punto [2]" in cleaned


def test_renumber_citations_matches_display_order():
    answer, mapping = renumber_citations("Usa [3] y [5]. No [9].", [3, 5])
    assert mapping == {3: 1, 5: 2}
    assert answer == "Usa [1] y [2]. No [9]."


@pytest.mark.asyncio
async def test_chat_falls_back_to_rules_when_local_ai_is_unavailable(
    client, session_factory, monkeypatch
):
    from tests.conftest import create_opportunity

    session = session_factory()
    create_opportunity(session, slug="ai-fallback", title="AI Fallback Hackathon", tags=["ai"])
    session.close()

    class UnavailableAI:
        async def status(self, force: bool = False) -> LocalAIStatus:
            return LocalAIStatus(False, True, "http://127.0.0.1:11434", None, None, (), "sin modelo")

        async def generate(self, **kwargs):  # pragma: no cover - must not be called
            raise AssertionError("generate should not be called when unavailable")

    monkeypatch.setattr("oportuna.api.assistant.get_local_ai", lambda: UnavailableAI())

    response = client.post(
        "/api/assistant/chat",
        json={"question": "¿Qué hackathons de IA puedo hacer?", "use_ai": True},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["grounding"]["uses_llm"] is False
    assert payload["grounding"]["mode"] == "rules"
    assert payload["grounding"]["model"] is None
    assert payload["items"]
    assert "La IA local no está disponible" in payload["grounding"]["note"] or "sin modelo" in payload["grounding"]["note"]
