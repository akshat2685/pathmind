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
from backend.api.college_routes import router as college_router
from backend.api.health_routes import router as connectivity_health_router
from backend.core.security import SecurityHeadersMiddleware, StructuredErrorMiddleware
from backend.core.config import settings
import logging
import sys

if not settings.GEMINI_API_KEY:
    logging.critical("CRITICAL: GEMINI_API_KEY is missing. Production startup aborted.")
    if __name__ == "__main__":
        sys.exit(1)
app = FastAPI(title="PATHMIND Production API")

# Add Production Security Middleware
app.add_middleware(StructuredErrorMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Setup CORS using configurable FRONTEND_ORIGIN with development fallbacks
allowed_origins = [settings.FRONTEND_ORIGIN]
for dev_origin in ["http://localhost:3000", "http://127.0.0.1:3000"]:
    if dev_origin not in allowed_origins:
        allowed_origins.append(dev_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # Allow every Vercel preview deployment (*.vercel.app): each redeploy mints
    # a new preview URL, and a single hardcoded origin would break the web app's
    # API calls (the browser blocks them as CORS failures, surfacing as
    # "Failed to fetch") after every deploy. Auth uses Bearer tokens, not
    # cookies, so a foreign site cannot act without the user's token.
    allow_origin_regex=r"https://([a-z0-9-]+\.)*vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
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
app.include_router(college_router)
app.include_router(connectivity_health_router)

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
    """
    from backend.core.config import settings
    from backend.services.store import FirestoreStore
    
    store = FirestoreStore()
    firestore_status = await store.check_health()
    gemini_status = "CONFIGURED" if settings.GEMINI_API_KEY else "MISSING"
    is_ready = firestore_status == "CONNECTED"

    from fastapi.responses import JSONResponse
    body = {
        "status": "ready" if is_ready else "not_ready",
        "dependencies": {
            "datastore": "healthy" if is_ready else "unhealthy",
            "ai_reasoning": "configured" if gemini_status == "CONFIGURED" else "degraded"
        }
    }
    return JSONResponse(status_code=200 if is_ready else 503, content=body)

@app.get("/health")
async def health_check():
    from backend.core.config import settings
    from backend.services.store import FirestoreStore
    
    store = FirestoreStore()
    firestore_status = await store.check_health()
    gemini_status = "CONFIGURED" if settings.GEMINI_API_KEY else "MISSING"
    
    if firestore_status != "CONNECTED" or gemini_status == "MISSING":
        return {"status": "degraded", "firestore": firestore_status, "gemini": gemini_status}
        
    return {"status": "ok", "service": "pathmind-backend", "firestore": firestore_status, "gemini": gemini_status}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
