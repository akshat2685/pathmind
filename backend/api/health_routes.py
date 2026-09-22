from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from backend.services.supabase_adapter import get_supabase_adapter

router = APIRouter(prefix="/api/health", tags=["Health & Connectivity"])

@router.get("", status_code=status.HTTP_200_OK)
async def backend_health():
    """
    Verifies that FastAPI itself is running.
    Does NOT require Supabase.
    """
    return {
        "status": "ok",
        "service": "pathmind-api"
    }

@router.get("/database")
async def database_health():
    """
    Makes a real server-side request to verify Supabase PostgreSQL connectivity.
    Returns HTTP 200 on success, or HTTP 503 on DATABASE_UNAVAILABLE.
    Never exposes credentials or internal connection strings.
    """
    adapter = get_supabase_adapter()
    result = await adapter.check_database_health()
    if result.get("status") == "ok":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok", "database": "supabase"}
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "code": "DATABASE_UNAVAILABLE"}
        )
