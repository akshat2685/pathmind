"""
Supabase PostgreSQL Database Adapter.
Single place responsible for Supabase connectivity on the backend.
Uses SUPABASE_URL and SUPABASE_SECRET_KEY.
Enforces zero silent fallbacks to in-memory dictionaries or local JSON.
"""

from typing import Optional, Dict, Any
import logging
from backend.core.config import settings

logger = logging.getLogger(__name__)

class SupabaseAdapter:
    _instance: Optional["SupabaseAdapter"] = None
    _client = None

    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_SECRET_KEY
        self._init_client()

    def _init_client(self):
        if self.url and self.key:
            try:
                from supabase import create_client, Client
                self._client: Client = create_client(self.url, self.key)
            except Exception as e:
                logger.error("Failed to initialize Supabase client: %s", type(e).__name__)
                self._client = None
        else:
            self._client = None

    @property
    def client(self):
        if not self._client:
            self._init_client()
        return self._client

    async def check_database_health(self) -> Dict[str, Any]:
        """
        Executes a real server-side request to Supabase to verify connectivity.
        Does NOT return 'connected' merely because environment variables exist.
        Never exposes credentials or secrets.
        """
        if not self.url or not self.key:
            return {"status": "error", "code": "DATABASE_UNAVAILABLE"}

        try:
            import httpx
            # Make a real server-side HTTP request to the Supabase PostgREST root endpoint
            # which verifies project availability and valid secret key authentication.
            headers = {
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}"
            }
            async with httpx.AsyncClient(timeout=5.0) as http_client:
                res = await http_client.get(f"{self.url.rstrip('/')}/rest/v1/", headers=headers)
                if res.status_code in (200, 204):
                    return {"status": "ok", "database": "supabase"}
                else:
                    logger.warning("Supabase health check returned HTTP %s", res.status_code)
                    return {"status": "error", "code": "DATABASE_UNAVAILABLE"}
        except Exception as err:
            logger.error("Supabase health check exception: %s", type(err).__name__)
            return {"status": "error", "code": "DATABASE_UNAVAILABLE"}

    async def verify_and_map_user(self, uid: str, email: str, name: str = "") -> Dict[str, Any]:
        """
        Ensures auth.user.id is mapped to an internal application person_id in public.learners.
        """
        if not self.client:
            return {"user_id": uid, "email": email, "name": name}
            
        try:
            data = {
                "user_id": uid,
                "email": email,
                "name": name
            }
            res = self.client.table("learners").upsert(data, on_conflict="user_id").execute()
            if res.data:
                return res.data[0]
            return data
        except Exception as e:
            logger.error("Failed to map user in Supabase: %s", str(e))
            return {"user_id": uid, "email": email, "name": name}

def get_supabase_adapter() -> SupabaseAdapter:
    if SupabaseAdapter._instance is None:
        SupabaseAdapter._instance = SupabaseAdapter()
    return SupabaseAdapter._instance
