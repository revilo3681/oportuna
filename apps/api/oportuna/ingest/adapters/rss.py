"""RSS adapter for discovery leads.

RSS posts are not official event pages. They can surface a new opportunity, but
``confirmed`` stays False, which keeps the record out of the public catalog until
a human reviews it or an official page confirms it.
"""

from __future__ import annotations

import feedparser

from oportuna.domain.dates import parse_stated_deadline, utcnow
from oportuna.domain.normalize import clean_html, extract_year, truncate
from oportuna.domain.taxonomy import (
    classify_category,
    extract_tech_tags,
    looks_like_opportunity,
    looks_tech,
)
from oportuna.ingest.adapters.base import allowed_domains_for
from oportuna.ingest.http import Fetcher, FetchError
from oportuna.ingest.types import RawOpportunity


class RssAdapter:
    kind = "rss"

    async def fetch(self, source, fetcher: Fetcher) -> list[RawOpportunity]:
        config = source.config or {}
        result = await fetcher.fetch_text(
            source.endpoint,
            allowed_domains=allowed_domains_for(source),
            respect_robots=bool(config.get("respect_robots", True)),
        )
        parsed = feedparser.parse(result.content)
        if parsed.bozo and not parsed.entries:
            raise FetchError("Feed RSS no interpretable", url=source.endpoint)

        now = utcnow()
        max_items = int(config.get("max_items", 40))
        require_tech = bool(config.get("require_tech", True))
        records: list[RawOpportunity] = []
        for entry in parsed.entries[:max_items]:
            record = self._map(entry, source, require_tech, now)
            if record:
                records.append(record)
        return records

    def _map(self, entry, source, require_tech: bool, now) -> RawOpportunity | None:
        title = clean_html(entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link:
            return None

        summary_html = entry.get("summary") or entry.get("description") or ""
        summary = clean_html(summary_html)
        text = f"{title} {summary}"
        if not looks_like_opportunity(title, summary):
            return None
        if require_tech and not looks_tech(text):
            return None

        category = classify_category(title, summary)
        if not category:
            return None

        deadline = parse_stated_deadline(summary, now=now)
        tags = extract_tech_tags(text)
        year = extract_year(title, summary)

        return RawOpportunity(
            external_id=str(entry.get("id") or link),
            title=title,
            official_url=link,
            source_url=link,
            summary=truncate(summary, 320),
            description=summary,
            category=category,
            subcategory=None,
            tech_tags=tags,
            modality="online",
            language="en",
            registration_deadline=deadline,
            confirmed=False,
            confirmation_note=(
                "Detectado en un medio/agregador; requiere confirmación en la web oficial."
            ),
            raw_excerpt=truncate(summary, 240),
            extra={
                "feed": source.slug,
                "published": entry.get("published"),
                "year": year,
                "fetched_at": now.isoformat(),
            },
        )
