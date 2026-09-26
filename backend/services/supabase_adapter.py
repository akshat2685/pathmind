"""
Supabase adapter for the PATHMIND main product.

Single place responsible for Supabase connectivity on the main-product backend.
Uses SUPABASE_URL and SUPABASE_SECRET_KEY (same project as College MVP).

Safety: this adapter only verifies JWTs via Supabase Auth and connects to the
shared project. It never creates, alters, or drops tables. Main-product tables
are additive and namespaced; college tables are never touched.
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
            except Exception:
                logger.error("Failed to initialize Supabase client: %s", type(Exception).__name__)
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
        Real server-side connectivity check. Never returns 'ok' merely because
        env vars exist. Never exposes credentials.
        """
        if not self.url or not self.key:
            return {"status": "error", "code": "DATABASE_UNAVAILABLE"}

        try:
            import httpx
            headers = {
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}"
            }
            async with httpx.AsyncClient(timeout=5.0) as http_client:
                res = await http_client.get(f"{self.url.rstrip('/')}/rest/v1/", headers=headers)
                if res.status_code in (200, 204):
                    return {"status": "ok", "database": "supabase"}
                logger.warning("Supabase health check returned HTTP %s", res.status_code)
                return {"status": "error", "code": "DATABASE_UNAVAILABLE"}
        except Exception as err:
            logger.error("Supabase health check exception: %s", type(err).__name__)
            return {"status": "error", "code": "DATABASE_UNAVAILABLE"}

    def verify_jwt(self, token: str) -> str:
        """
        Verifies a Supabase Auth JWT and returns the authenticated user id.
        Raises on any failure — never returns an unverified identity.
        """
        if not self.client:
            raise RuntimeError("DATABASE_UNAVAILABLE: Supabase client not initialized.")
        user_resp = self.client.auth.get_user(token)
        if not user_resp or not user_resp.user:
            raise ValueError("No user found for token")
        return user_resp.user.id


def get_supabase_adapter() -> SupabaseAdapter:
    if SupabaseAdapter._instance is None:
        SupabaseAdapter._instance = SupabaseAdapter()
    return SupabaseAdapter._instance
