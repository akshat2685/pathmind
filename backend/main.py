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

app = FastAPI(title="PATHMIND MVP API")

# Setup CORS for MVP
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
        "service": "PATHMIND MVP API",
        "status": "online",
        "docs": "/docs",
        "health": "/health"
    }

app.include_router(health_router)
app.include_router(assessment_router)
app.include_router(counseling_router)

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
