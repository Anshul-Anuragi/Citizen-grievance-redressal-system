import os
import time
import uuid
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings, _INSECURE_DEFAULT_SECRET
from app.core.database import engine, Base, get_db, AsyncSessionLocal
from app.services.complaint_service import ComplaintService
from app.api import (
    auth, complaints, district_admin, officers,
    analytics, ai, notifications, attachments
)

logger = logging.getLogger(__name__)


def _check_production_security() -> None:
    if settings.ENVIRONMENT.lower() == "production":
        if not settings.SECRET_KEY or settings.SECRET_KEY == _INSECURE_DEFAULT_SECRET:
            raise RuntimeError(
                "FATAL: SECRET_KEY is set to the insecure default value in production. "
                "Set a strong, randomly generated SECRET_KEY environment variable."
            )
        if len(settings.SECRET_KEY) < 32:
            raise RuntimeError(
                "FATAL: SECRET_KEY is too short for production use (min 32 characters required)."
            )


async def _periodic_sla_overdue_scanner(interval_seconds: int = 60):
    """
    Decoupled background SLA scanner running inside FastAPI lifespan.
    Periodically checks and updates overdue statuses across all districts.
    """
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            async with AsyncSessionLocal() as session:
                await ComplaintService.update_overdue_statuses(session)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Error in background SLA overdue scanner: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _check_production_security()
    if "sqlite" in str(engine.url):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Start decoupled SLA scanner background task
    scanner_task = asyncio.create_task(_periodic_sla_overdue_scanner())
    yield
    scanner_task.cancel()
    try:
        await scanner_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MPOnline / Madhya Pradesh Civic Digital Grievance Redressal Portal API",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id

    # Structured access log without passwords, tokens, or sensitive headers
    logger.info(
        "HTTP Request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": elapsed_ms,
        }
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_v1_prefix = settings.API_V1_STR
app.include_router(auth.router, prefix=api_v1_prefix)
app.include_router(complaints.router, prefix=api_v1_prefix)
app.include_router(district_admin.router, prefix=api_v1_prefix)
app.include_router(officers.router, prefix=api_v1_prefix)
app.include_router(analytics.router, prefix=api_v1_prefix)
app.include_router(ai.router, prefix=api_v1_prefix)
app.include_router(notifications.router, prefix=api_v1_prefix)
app.include_router(attachments.router, prefix=api_v1_prefix)


@app.get("/health", tags=["Health"])
async def health_check(request: Request):
    db_status = "error"
    db_detail = None
    override = request.app.dependency_overrides.get(get_db)
    target_get_db = override if override is not None else get_db
    try:
        gen = target_get_db()
        session = await anext(gen)
        try:
            if session:
                await session.execute(text("SELECT 1"))
            db_status = "ok"
        finally:
            try:
                await gen.aclose()
            except Exception:
                pass
    except Exception as exc:
        db_detail = str(exc)
        logger.error("Health check database error: %s", exc)

    payload = {
        "status": "healthy" if db_status == "ok" else "unhealthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "ai_enabled": bool(settings.GEMINI_API_KEY),
        "db_status": db_status
    }
    if db_detail:
        payload["db_detail"] = db_detail

    http_status = status.HTTP_200_OK if db_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=payload, status_code=http_status)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled exception [request_id=%s] %s: %s",
        request_id,
        type(exc).__name__,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please contact system support.",
            "request_id": request_id,
        },
    )
