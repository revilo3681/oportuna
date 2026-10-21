"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from oportuna.api import accounts, admin, assistant, catalog
from oportuna.config import get_settings
from oportuna.db.base import Base, get_engine, get_session_factory
from oportuna.seed import seed_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("oportuna")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.is_production and settings.jwt_secret.startswith("dev-only"):
        raise RuntimeError(
            "JWT_SECRET inseguro en producción. Configura OPORTUNA_JWT_SECRET antes de arrancar."
        )
    if os.getenv("OPORTUNA_AUTO_CREATE", "0") == "1":
        Base.metadata.create_all(bind=get_engine())
        session = get_session_factory()()
        try:
            result = seed_all(session)
            logger.info("auto-create/seed: %s", result)
        finally:
            session.close()
    logger.info(
        "Oportuna API iniciada (entorno=%s, publicación mínima=%.2f)",
        settings.environment,
        settings.auto_publish_min_confidence,
    )
    yield


app = FastAPI(
    title="Oportuna API",
    description=(
        "Inteligencia global de oportunidades tecnológicas. Datos con procedencia, "
        "verificación explicable y recomendaciones basadas en intereses y tiempo disponible."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
    return response


@app.get("/api", tags=["meta"])
def api_index():
    return {
        "name": "Oportuna API",
        "version": "0.1.0",
        "docs": "/api/docs",
        "principles": [
            "fuente y última comprobación visibles",
            "sin fechas inferidas presentadas como confirmadas",
            "publicación automática solo tras validación estricta",
        ],
    }


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "oportuna-api"}


@app.get("/api/ready", tags=["meta"])
def ready():
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "detail": type(exc).__name__},
        )
    return {"status": "ready"}


app.include_router(catalog.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")
