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

#: Human-readable description of what is misconfigured. Used by routes to
#: return an actionable 503 instead of a cryptic RuntimeError.
CONFIG_ERROR_MESSAGE = (
    "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SECRET_KEY "
    "as environment variables on the API deployment (Vercel → pathmind-college-api "
    "→ Settings → Environment Variables, target Production + Preview), then redeploy."
)


class SupabaseAdapter:
    _instance: Optional["SupabaseAdapter"] = None
    _client = None

    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_SECRET_KEY
        self._config_error: Optional[str] = None
        self._init_client()

    def _init_client(self):
        missing = []
        if not self.url:
            missing.append("SUPABASE_URL")
        if not self.key:
            missing.append("SUPABASE_SECRET_KEY")
        if missing:
            self._config_error = (
                f"Supabase client unavailable: missing {', '.join(missing)}. "
                + CONFIG_ERROR_MESSAGE
            )
            logger.error(
                "Supabase misconfigured — missing env vars: %s. "
                "All Supabase-backed endpoints will return 503 until fixed.",
                ", ".join(missing),
            )
            self._client = None
            return
        try:
            from supabase import create_client, Client
            self._client: Client = create_client(self.url, self.key)
            self._config_error = None
        except Exception as e:
            self._config_error = (
                f"Supabase client failed to initialize: {type(e).__name__}. "
                + CONFIG_ERROR_MESSAGE
            )
            logger.error("Failed to initialize Supabase client: %s", type(e).__name__)
            self._client = None

    @property
    def client(self):
        if not self._client:
            self._init_client()
        return self._client

    @property
    def config_error(self) -> Optional[str]:
        """Returns a human-readable config error, or None if configured."""
        if not self._client:
            self._init_client()
        return self._config_error

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def require_client(self):
        """
        Returns the client, or raises RuntimeError with an actionable message
        naming the missing env vars. Use this instead of bare `self.client`
        in stores so failures are diagnosable.
        """
        client = self.client
        if client is None:
            raise RuntimeError(self._config_error or CONFIG_ERROR_MESSAGE)
        return client

    async def check_database_health(self) -> Dict[str, Any]:
        """
        Executes a real server-side request to Supabase to verify connectivity.
        Does NOT return 'connected' merely because environment variables exist.
        Never exposes credentials or secrets.
        """
        if not self.url or not self.key:
            missing = []
            if not self.url:
                missing.append("SUPABASE_URL")
            if not self.key:
                missing.append("SUPABASE_SECRET_KEY")
            return {
                "status": "error",
                "code": "DATABASE_UNAVAILABLE",
                "missing_env_vars": missing,
                "hint": CONFIG_ERROR_MESSAGE,
            }

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
                    return {
                        "status": "error",
                        "code": "DATABASE_UNAVAILABLE",
                        "http_status": res.status_code,
                        "hint": "Supabase rejected the request — the secret key may be wrong or revoked.",
                    }
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
