"""Polite HTTP fetching for ingestion.

Rules enforced here:
- explicit domain allowlist per source;
- robots.txt respected unless a source is a documented public API;
- per-domain rate limiting and a hard size cap;
- bounded retries with backoff, no CAPTCHA/anti-bot circumvention of any kind;
- identifiable user agent with a contact URL.
"""

from __future__ import annotations

import asyncio
import time
import urllib.robotparser
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

from oportuna.domain.normalize import registrable_domain

ALLOWED_CONTENT_TYPES = (
    "text/html",
    "text/plain",
    "application/json",
    "application/ld+json",
    "application/xml",
    "text/xml",
    "application/rss+xml",
    "application/atom+xml",
    "text/calendar",
    "application/calendar+json",
    "application/octet-stream",  # some calendars mislabel .ics
)


class FetchError(Exception):
    def __init__(self, message: str, *, url: str = "", status: int | None = None) -> None:
        super().__init__(message)
        self.url = url
        self.status = status


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    content: str
    content_type: str
    fetched_at: datetime


class Fetcher:
    def __init__(
        self,
        *,
        timeout_seconds: float = 20,
        user_agent: str,
        max_bytes: int = 4_000_000,
        min_interval_seconds: float = 1.0,
        max_retries: int = 2,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.max_bytes = max_bytes
        self.min_interval_seconds = min_interval_seconds
        self.max_retries = max_retries
        self._domain_locks: dict[str, asyncio.Lock] = {}
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self.request_count = 0

    def _check_domain(self, url: str, allowed_domains: list[str] | None) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise FetchError("Esquema no permitido", url=url)
        host = registrable_domain(url)
        if allowed_domains:
            allowed = {d.lower().lstrip(".") for d in allowed_domains if d}
            if host not in allowed:
                raise FetchError(f"Dominio no incluido en la allowlist: {host}", url=url)
        return host

    async def _robots_allows(self, client: httpx.AsyncClient, url: str) -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._robots.get(base)
        if parser is None:
            robots_url = f"{base}/robots.txt"
            try:
                response = await client.get(robots_url)
                if response.status_code == 200:
                    parser = urllib.robotparser.RobotFileParser()
                    parser.parse(response.text.splitlines())
                else:
                    parser = urllib.robotparser.RobotFileParser()
                    parser.parse([])
            except httpx.HTTPError:
                parser = urllib.robotparser.RobotFileParser()
                parser.parse([])
            self._robots[base] = parser
        return parser.can_fetch(self.user_agent, url)

    async def _throttle(self, host: str) -> None:
        lock = self._domain_locks.setdefault(host, asyncio.Lock())
        async with lock:
            elapsed = time.monotonic() - self._last_request.get(host, 0.0)
            if elapsed < self.min_interval_seconds:
                await asyncio.sleep(self.min_interval_seconds - elapsed)
            self._last_request[host] = time.monotonic()

    async def fetch_text(
        self,
        url: str,
        *,
        allowed_domains: list[str] | None = None,
        respect_robots: bool = True,
        headers: dict[str, str] | None = None,
    ) -> FetchResult:
        host = self._check_domain(url, allowed_domains)
        request_headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/json,application/xml,text/calendar,application/rss+xml;q=0.9,*/*;q=0.5",
            "Accept-Language": "es,en;q=0.8",
            **(headers or {}),
        }
        last_error: Exception | None = None
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers=request_headers,
        ) as client:
            if respect_robots and not await self._robots_allows(client, url):
                raise FetchError("El archivo robots.txt no permite esta consulta", url=url)
            for attempt in range(self.max_retries + 1):
                await self._throttle(host)
                try:
                    response = await client.get(url)
                    self.request_count += 1
                except httpx.HTTPError as exc:
                    last_error = exc
                    if attempt < self.max_retries:
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    raise FetchError(f"Error de red: {exc}", url=url) from exc

                if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    retry_after = response.headers.get("Retry-After", "")
                    delay = 2.0 * (attempt + 1)
                    if retry_after.isdigit():
                        delay = min(float(retry_after), 10.0)
                    await asyncio.sleep(delay)
                    continue
                if response.status_code >= 400:
                    raise FetchError(
                        f"HTTP {response.status_code}", url=url, status=response.status_code
                    )

                content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if content_type and not any(content_type.startswith(t) for t in ALLOWED_CONTENT_TYPES):
                    raise FetchError(f"Tipo de contenido no admitido: {content_type}", url=url)

                raw = response.content
                if len(raw) > self.max_bytes:
                    raise FetchError("Respuesta demasiado grande", url=url)
                content = response.text
                if not content.strip():
                    raise FetchError("Respuesta vacía", url=url)

                return FetchResult(
                    url=url,
                    final_url=str(response.url),
                    status=response.status_code,
                    content=content,
                    content_type=content_type,
                    fetched_at=datetime.now(UTC),
                )

        raise FetchError(f"No se pudo completar la petición: {last_error}", url=url)
