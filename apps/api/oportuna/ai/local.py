"""Local AI client for Ollama.

The model runs on the user's machine. Nothing is sent to a third-party API.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import lru_cache

import httpx

from oportuna.config import Settings, get_settings

logger = logging.getLogger("oportuna.ai")


class LocalAIError(RuntimeError):
    pass


@dataclass(frozen=True)
class LocalAIStatus:
    available: bool
    enabled: bool
    base_url: str
    model: str | None
    embed_model: str | None
    models: tuple[str, ...]
    detail: str | None = None


_status_cache: tuple[float, LocalAIStatus] | None = None
_STATUS_TTL_SECONDS = 20


class LocalAI:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def base_url(self) -> str:
        return self.settings.llm_base_url.rstrip("/")

    async def status(self, *, force: bool = False) -> LocalAIStatus:
        global _status_cache
        if not self.settings.llm_enabled:
            return LocalAIStatus(False, False, self.base_url, None, None, (), "IA local desactivada")
        now = time.monotonic()
        if not force and _status_cache and now - _status_cache[0] < _STATUS_TTL_SECONDS:
            return _status_cache[1]
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001
            status = LocalAIStatus(
                False,
                True,
                self.base_url,
                None,
                None,
                (),
                f"No se pudo conectar con Ollama: {type(exc).__name__}",
            )
            _status_cache = (now, status)
            return status

        models = payload.get("models") or []
        names = [str(item.get("name")) for item in models if item.get("name")]
        configured = self.settings.llm_model
        model = configured if configured in names else None
        if model is None:
            for item in models:
                name = str(item.get("name") or "")
                capabilities = item.get("capabilities") or []
                if "completion" in capabilities and "embed" not in name:
                    model = name
                    break
        if model is None:
            model = next((name for name in names if "embed" not in name), None)

        configured_embed = self.settings.llm_embed_model
        embed_model = configured_embed if configured_embed in names else next(
            (name for name in names if "embed" in name), None
        )
        available = bool(model)
        status = LocalAIStatus(
            available=available,
            enabled=True,
            base_url=self.base_url,
            model=model,
            embed_model=embed_model,
            models=tuple(names),
            detail=None if available else "Ollama responde, pero no hay modelos de chat instalados",
        )
        _status_cache = (now, status)
        return status

    async def generate(self, *, system: str, prompt: str) -> str:
        status = await self.status()
        if not status.available or not status.model:
            raise LocalAIError(status.detail or "IA local no disponible")
        payload = {
            "model": status.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "keep_alive": "30m",
            "options": {
                "temperature": self.settings.llm_temperature,
                "num_ctx": 8192,
                "num_predict": min(self.settings.llm_max_output_tokens, 350),
            },
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise LocalAIError("El modelo local tardó demasiado en responder") from exc
        except Exception as exc:  # noqa: BLE001
            raise LocalAIError(f"Error del modelo local: {type(exc).__name__}") from exc
        text = str(data.get("response") or "").strip()
        if not text:
            raise LocalAIError("El modelo local devolvió una respuesta vacía")
        return text

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        status = await self.status()
        if not status.embed_model:
            raise LocalAIError("No hay modelo de embeddings local disponible")
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": status.embed_model, "input": texts},
                )
                response.raise_for_status()
                data = response.json()
                embeddings = data.get("embeddings")
                if embeddings:
                    return embeddings
        except Exception:  # noqa: BLE001
            pass

        # Older Ollama versions expose /api/embeddings one input at a time.
        vectors: list[list[float]] = []
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                for text in texts:
                    response = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": status.embed_model, "prompt": text},
                    )
                    response.raise_for_status()
                    vectors.append(response.json()["embedding"])
        except Exception as exc:  # noqa: BLE001
            raise LocalAIError(f"Embeddings locales no disponibles: {type(exc).__name__}") from exc
        return vectors


@lru_cache
def get_local_ai() -> LocalAI:
    return LocalAI()


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
