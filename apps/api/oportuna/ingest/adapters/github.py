"""GitHub discovery adapter.

Repositories tagged as hackathons are *leads*, not confirmed opportunities. They
never carry event dates, so they are routed to the review queue rather than the
public catalog. Disabled by default in the source registry.
"""

from __future__ import annotations

import json
from urllib.parse import urlencode

from oportuna.domain.normalize import clean_html, truncate
from oportuna.domain.taxonomy import extract_tech_tags
from oportuna.ingest.adapters.base import allowed_domains_for
from oportuna.ingest.http import Fetcher, FetchError
from oportuna.ingest.types import RawOpportunity


class GitHubAdapter:
    kind = "github"

    async def fetch(self, source, fetcher: Fetcher) -> list[RawOpportunity]:
        config = source.config or {}
        query = config.get("query", "topic:hackathon")
        params = urlencode(
            {"q": query, "sort": "updated", "order": "desc", "per_page": min(int(config.get("per_page", 20)), 50)}
        )
        url = f"{source.endpoint}?{params}"
        result = await fetcher.fetch_text(
            url,
            allowed_domains=allowed_domains_for(source),
            respect_robots=False,
            headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
        )
        try:
            payload = json.loads(result.content)
        except json.JSONDecodeError as exc:
            raise FetchError("Respuesta de GitHub no es JSON válido", url=url) from exc
        if "items" not in payload:
            message = payload.get("message", "respuesta inesperada")
            raise FetchError(f"GitHub: {message}", url=url)

        records: list[RawOpportunity] = []
        for item in payload["items"][: int(config.get("max_items", 20))]:
            record = self._map(item, source)
            if record:
                records.append(record)
        return records

    def _map(self, item: dict, source) -> RawOpportunity | None:
        name = item.get("full_name") or ""
        url = item.get("html_url") or ""
        if not name or not url or item.get("archived"):
            return None
        topics = item.get("topics") or []
        if "hackathon" not in topics:
            return None

        description = clean_html(item.get("description") or "")
        summary = truncate(
            (description + " " if description else "")
            + "Repositorio etiquetado como hackathon en GitHub; convocatoria pendiente de confirmar.",
            300,
        )
        return RawOpportunity(
            external_id=str(item.get("id") or url),
            title=name,
            official_url=url,
            source_url=url,
            summary=summary,
            description=description,
            category="hackathons",
            subcategory="open-source",
            tech_tags=extract_tech_tags(name, description, " ".join(topics)),
            modality="online",
            language="en",
            organizer=(item.get("owner") or {}).get("login"),
            confirmed=False,
            confirmation_note="Repositorio de GitHub; no es una convocatoria confirmada.",
            raw_excerpt=truncate(description, 240),
            extra={
                "stars": item.get("stargazers_count"),
                "topics": topics,
                "pushed_at": item.get("pushed_at"),
                "source": source.slug,
            },
        )
