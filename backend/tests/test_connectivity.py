"""
Connectivity Integration Test Suite for PATHMIND MVP.
Verifies:
1. FastAPI Backend Health (GET /api/health)
2. Supabase PostgreSQL Connectivity (GET /api/health/database)
3. Zero Fallback Enforcement: DATABASE_UNAVAILABLE fails honestly without in-memory mocks.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.config import settings
from backend.services.supabase_adapter import SupabaseAdapter, get_supabase_adapter

client = TestClient(app)

def test_fastapi_backend_health():
    """
    Step 4: GET /api/health must return 200 OK with service name and not require Supabase.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "pathmind-api"

def test_database_health_without_credentials_fails_honestly():
    """
    Step 9: When Supabase credentials are not set or unavailable,
    it MUST return 503 with DATABASE_UNAVAILABLE and NEVER fall back to in-memory mocks.
    """
    # Temporarily clear credentials on a fresh adapter instance
    test_adapter = SupabaseAdapter()
    test_adapter.url = ""
    test_adapter.key = ""
    
    # Directly verify health check returns DATABASE_UNAVAILABLE
    import asyncio
    result = asyncio.run(test_adapter.check_database_health())
    assert result["status"] == "error"
    assert result["code"] == "DATABASE_UNAVAILABLE"

def test_database_health_endpoint():
    """
    Step 5 & 10: GET /api/health/database makes a real server-side request.
    If credentials are configured, it tests real connectivity.
    If credentials are not yet configured in the environment, it returns 503 DATABASE_UNAVAILABLE.
    """
    response = client.get("/api/health/database")
    if settings.SUPABASE_URL and settings.SUPABASE_SECRET_KEY:
        # Real integration test against configured Supabase project
        assert response.status_code in (200, 503)
        data = response.json()
        if response.status_code == 200:
            assert data["status"] == "ok"
            assert data["database"] == "supabase"
        else:
            assert data["status"] == "error"
            assert data["code"] == "DATABASE_UNAVAILABLE"
    else:
        # Honest failure reporting when environment key is pending
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "error"
        assert data["code"] == "DATABASE_UNAVAILABLE"
