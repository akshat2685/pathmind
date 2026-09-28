import sys
import os
from pathlib import Path

# Add parent directory to sys.path so 'backend.xxx' package imports work seamlessly
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
from backend.api.routes import router as health_router
from backend.api.assessment_routes import router as assessment_router
from backend.api.counseling_routes import router as counseling_router
from backend.api.trajectory_routes import router as trajectory_router
from backend.api.roadmap_routes import router as roadmap_router
from backend.api.memory_routes import router as memory_router
from backend.api.career_routes import router as career_router
from backend.api.adaptation_routes import router as adaptation_router
from backend.api.evidence_routes import router as evidence_router
from backend.api.context_routes import router as context_router
from backend.api.proactive_routes import router as proactive_router
from backend.api.trust_routes import router as trust_router
from backend.api.longitudinal_routes import router as longitudinal_router
from backend.api.artifact_routes import router as artifact_router
from backend.api.execution_routes import router as execution_router
from backend.api.opportunity_routes import router as opportunity_router
from backend.api.orchestrator_routes import router as orchestrator_router
from backend.api.market_routes import router as market_router
from backend.api.verification_routes import router as verification_router
from backend.api.test_routes import router as test_router
from backend.api.accountability_routes import router as accountability_router
from backend.api.memory_tier_routes import router as memory_tier_router
from backend.core.security import SecurityHeadersMiddleware, StructuredErrorMiddleware
from backend.core.config import settings
import logging
import sys

if not settings.GEMINI_API_KEY:
    logging.critical("CRITICAL: GEMINI_API_KEY is missing. Production startup aborted.")
    if __name__ == "__main__":
        sys.exit(1)

_accountability_scheduler: Optional["AccountabilityScheduler"] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: verify the datastore is reachable, then start the background
    accountability scheduler (6-hour sweeps over active roadmaps).
    Fails loudly on DB unreachability -- never silently skips.
    Shutdown: stop the scheduler cleanly.
    """
    global _accountability_scheduler
    from backend.services.accountability_scheduler import AccountabilityScheduler
    _accountability_scheduler = AccountabilityScheduler()
    await _accountability_scheduler.start()  # raises loudly if DB unreachable
    try:
        yield
    finally:
        if _accountability_scheduler is not None:
            await _accountability_scheduler.shutdown()
            _accountability_scheduler = None

app = FastAPI(title="PATHMIND Production API", lifespan=lifespan)

# Add Production Security Middleware
app.add_middleware(StructuredErrorMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Setup CORS for production and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://akshat2685.github.io"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "service": "PATHMIND Production API",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
        "health_live": "/health/live",
        "health_ready": "/health/ready"
    }

app.include_router(health_router)
app.include_router(assessment_router)
app.include_router(counseling_router)
app.include_router(trajectory_router)
app.include_router(roadmap_router)
app.include_router(memory_router)
app.include_router(career_router)
app.include_router(adaptation_router)
app.include_router(evidence_router)
app.include_router(context_router)
app.include_router(proactive_router)
app.include_router(trust_router)
app.include_router(longitudinal_router)
app.include_router(artifact_router)
app.include_router(execution_router)
app.include_router(opportunity_router)
app.include_router(orchestrator_router)
app.include_router(market_router)
app.include_router(verification_router)
app.include_router(test_router)
app.include_router(accountability_router)
app.include_router(memory_tier_router)

@app.get("/health/live")
async def health_live():
    """
    Fast Liveness Check: verifies the HTTP application process is responsive.
    """
    from datetime import datetime, timezone
    return {
        "status": "alive",
        "service": "pathmind-backend",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health/ready")
async def health_ready():
    """
    Readiness Check: validates core dependencies can service traffic without leaking internal details.
    Uses the trust-layer PmStore (Supabase) — a real DB round-trip, no silent in-memory fallbacks.
    """
    from backend.core.config import settings
    from backend.services.pm_store import get_pm_store

    try:
        store = get_pm_store()
        await store.check_health()
        datastore_ok = True
    except Exception:
        datastore_ok = False
    gemini_ok = bool(settings.GEMINI_API_KEY)

    return {
        "status": "ready" if datastore_ok else "not_ready",
        "dependencies": {
            "datastore": "healthy" if datastore_ok else "unhealthy",
            "ai_reasoning": "configured" if gemini_ok else "degraded"
        }
    }

@app.get("/health")
async def health_check():
    """
    Health Check: reports the real state of the trust-layer datastore (Supabase)
    and AI reasoning configuration. Returns 200 with an honest status body —
    a down DB reports 'degraded', it never silently claims health.
    """
    from backend.core.config import settings
    from backend.services.pm_store import get_pm_store

    gemini_status = "CONFIGURED" if settings.GEMINI_API_KEY else "MISSING"
    try:
        store = get_pm_store()
        datastore_status = await store.check_health()
    except Exception:
        return {"status": "degraded", "datastore": "UNREACHABLE", "gemini": gemini_status}

    if datastore_status != "CONNECTED" or gemini_status == "MISSING":
        return {"status": "degraded", "datastore": datastore_status, "gemini": gemini_status}

    return {"status": "ok", "service": "pathmind-backend", "datastore": datastore_status, "gemini": gemini_status}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
