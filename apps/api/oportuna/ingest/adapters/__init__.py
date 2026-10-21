"""Adapter registry."""

from __future__ import annotations

from oportuna.ingest.adapters import devpost, github, ics_feed, jsonld, rss
from oportuna.ingest.http import Fetcher
from oportuna.ingest.types import RawOpportunity

ADAPTERS = {
    "devpost": devpost.DevpostAdapter,
    "ics": ics_feed.IcsAdapter,
    "jsonld": jsonld.JsonLdAdapter,
    "rss": rss.RssAdapter,
    "github": github.GitHubAdapter,
}


def get_adapter(kind: str):
    try:
        return ADAPTERS[kind]()
    except KeyError as exc:
        raise ValueError(f"Tipo de fuente no soportado: {kind}") from exc


__all__ = ["ADAPTERS", "Fetcher", "RawOpportunity", "get_adapter"]
