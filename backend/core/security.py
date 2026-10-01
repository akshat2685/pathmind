import concurrent.futures
import re
import time
import uuid
import ipaddress
import urllib.parse
from typing import Optional, Dict, List, Tuple
from fastapi import Header, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from backend.services.supabase_adapter import get_supabase_adapter
import httpx

# Valid person_id regex: 3-64 chars, alphanumeric with hyphens, underscores, dots
PERSON_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]{3,64}$")

# Upper bound for one Supabase auth round-trip (auth.get_user). The supabase-py
# sync auth client exposes no per-call timeout, so get_authenticated_person
# runs it on a worker thread and caps the wait (see below). On Python 3.11+
# concurrent.futures.TimeoutError is an alias of builtin TimeoutError, so the
# infra-error tuple in get_authenticated_person covers it.
AUTH_VERIFY_TIMEOUT_SECONDS = 10
# Transient infra failures (timeouts, connect errors) get a bounded retry: a
# single slow Supabase response must not become a user-facing 503. Attempts
# are capped so worst case stays well inside the serverless window.
AUTH_VERIFY_MAX_ATTEMPTS = 3
AUTH_VERIFY_BACKOFF_SECONDS = 0.5
# A successful verification is cached briefly per token: the dashboard fires
# many authenticated calls per page load and each one otherwise pays a full
# Supabase Auth round-trip. Entries expire with the token or after this TTL,
# whichever comes first. This does not weaken revocation semantics: Supabase
# access tokens are not revoked server-side on sign-out either.
AUTH_VERIFY_CACHE_TTL_SECONDS = 120
_INFRA_ERRORS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    ConnectionError,
    TimeoutError,
)

# Module-level pool for bounding auth.get_user(): a bounded worker pool means
# timed-out calls can't leak threads unboundedly. NOTE: a genuinely hung
# socket still occupies one worker until it returns; on serverless hosts the
# container is recycled between invocations so this cannot accumulate.
_auth_verify_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# Short-lived cache of successful verifications, keyed by a hash of the token
# (never the raw token). token -> (user_id, monotonic expiry).
_auth_verify_cache: Dict[str, Tuple[str, float]] = {}


def _token_expiry_seconds(token: str) -> Optional[float]:
    """Best-effort read of the JWT `exp` claim (no signature check — the
    signature is still verified by Supabase on a cache miss). Returns seconds
    until expiry, or None when the claim cannot be read."""
    try:
        import base64
        import json

        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp")
        if not isinstance(exp, (int, float)):
            return None
        return float(exp) - time.time()
    except Exception:
        return None


def _auth_cache_get(token: str) -> Optional[str]:
    import hashlib

    key = hashlib.sha256(token.encode()).hexdigest()
    entry = _auth_verify_cache.get(key)
    if entry is None:
        return None
    user_id, expires_at = entry
    if time.monotonic() >= expires_at:
        _auth_verify_cache.pop(key, None)
        return None
    return user_id


def _auth_cache_put(token: str, user_id: str) -> None:
    import hashlib

    remaining = _token_expiry_seconds(token)
    ttl = AUTH_VERIFY_CACHE_TTL_SECONDS
    if remaining is not None:
        ttl = min(ttl, max(0.0, remaining - 5))
    if ttl <= 0:
        return
    if len(_auth_verify_cache) > 512:  # bound memory on long-lived containers
        _auth_verify_cache.clear()
    _auth_verify_cache[hashlib.sha256(token.encode()).hexdigest()] = (
        user_id,
        time.monotonic() + ttl,
    )

def validate_person_id_format(person_id: str) -> bool:
    if not person_id or not isinstance(person_id, str):
        return False
    # Reject path traversal, null bytes, script tags, SQL injection tokens
    if any(ch in person_id for ch in ["/", "\\", "\0", "<", ">", ";", "'", '"', ".."]):
        return False
    return bool(PERSON_ID_PATTERN.match(person_id))

def get_authenticated_person(
    authorization: Optional[str] = Header(None)
) -> str:
    """
    Extracts and strictly verifies the authenticated person identity using Supabase Auth.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="MISSING_AUTHORIZATION: Bearer token is required."
        )

    token = authorization[7:].strip()

    cached_user_id = _auth_cache_get(token)
    if cached_user_id is not None:
        return cached_user_id

    adapter = get_supabase_adapter()
    if not adapter.client:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_UNAVAILABLE: Unable to connect to Supabase for authentication."
        )

    last_infra_exc: Optional[BaseException] = None
    for attempt in range(AUTH_VERIFY_MAX_ATTEMPTS):
        try:
            # Bound the auth round-trip: supabase-py's sync auth client offers
            # no per-call timeout (only a client-wide httpx_client override at
            # construction, which would touch the shared adapter), so run
            # auth.get_user on a pool thread and cap the wait. A hung
            # connection can no longer eat into the 60s serverless timeout.
            user_resp = _auth_verify_pool.submit(
                adapter.client.auth.get_user, token
            ).result(timeout=AUTH_VERIFY_TIMEOUT_SECONDS)
            if not user_resp or not user_resp.user:
                raise ValueError("No user found")
            user_id = user_resp.user.id
            _auth_cache_put(token, user_id)
            return user_id
        except _INFRA_ERRORS as infra_exc:
            # Network / timeout / connectivity failures are INFRA, not bad
            # tokens — returning 401 here masks outages as invalid
            # credentials. Retry a bounded number of times: these failures
            # are transient by nature and a single slow response must not
            # surface to the learner as a hard error.
            last_infra_exc = infra_exc
            if attempt + 1 < AUTH_VERIFY_MAX_ATTEMPTS:
                time.sleep(AUTH_VERIFY_BACKOFF_SECONDS * (attempt + 1))
        except Exception:
            raise HTTPException(
                status_code=401,
                detail="INVALID_TOKEN: Supabase JWT verification failed."
            )
    raise HTTPException(
        status_code=503,
        detail=(
            "AUTH_SERVICE_UNAVAILABLE: authentication service unavailable "
            f"({type(last_infra_exc).__name__})."
        ),
    )

def enforce_person_ownership(authenticated_id: str, target_person_id: str) -> None:
    """
    IDOR Protection: Enforces that authenticated user matches the target resource owner.
    """
    if authenticated_id != target_person_id:
        raise HTTPException(
            status_code=403,
            detail="FORBIDDEN_CROSS_PERSON_ACCESS: You do not have permission to access or modify this person's resources."
        )

# Private / Loopback / Cloud Metadata IP Networks to block for SSRF protection
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # Private RFC 1918
    ipaddress.ip_network("172.16.0.0/12"),     # Private RFC 1918
    ipaddress.ip_network("192.168.0.0/16"),    # Private RFC 1918
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud Metadata
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 private
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
    "169.254.169.254",
    "100.100.100.200"
}

def validate_safe_url(url: str) -> bool:
    """
    SSRF Defense: Validates that an external URL is safe to query.
    Blocks private IP spaces, cloud metadata endpoints, loopbacks, and non-http(s) schemes.
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() not in ["http", "https"]:
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        hostname_clean = hostname.strip().lower()

        # Check blocked hostname list
        if hostname_clean in BLOCKED_HOSTNAMES or hostname_clean.endswith(".internal"):
            return False

        # Disallow credentials in URL (user:pass@host)
        if parsed.username or parsed.password:
            return False

        # Attempt IP resolution check if it's an IP literal
        try:
            ip = ipaddress.ip_address(hostname_clean)
            for blocked_net in BLOCKED_IP_NETWORKS:
                if ip in blocked_net:
                    return False
        except ValueError:
            # Not an IP literal; domain name
            pass

        return True
    except Exception:
        return False

def sanitize_external_content(content: str, max_chars: int = 15000) -> str:
    """
    Prompt Injection & Context Poisoning Defense:
    Limits maximum text size and neutralizes instruction-override keywords.
    """
    if not content:
        return ""

    # Truncate oversized text to prevent token-bombing
    bounded_text = content[:max_chars]

    # Neutralize common prompt injection phrases
    bounded_text = re.sub(r"(?i)ignore previous instructions", "[neutralized_instruction]", bounded_text)
    bounded_text = re.sub(r"(?i)system prompt", "[data_content]", bounded_text)
    bounded_text = re.sub(r"(?i)you are now", "[neutralized_role]", bounded_text)
    bounded_text = re.sub(r"(?i)<\|im_start\|>", "[neutralized_token]", bounded_text)
    bounded_text = re.sub(r"(?i)<\|im_end\|>", "[neutralized_token]", bounded_text)
    bounded_text = re.sub(r"(?i)admin override", "[neutralized_command]", bounded_text)

    return f"[DATA_UNTRUSTED_CONTENT]\n{bounded_text}\n[/DATA_UNTRUSTED_CONTENT]"

class SecurityRateLimiter:
    """
    Sliding-window in-memory rate limiter per key.
    """
    def __init__(self):
        self._history: Dict[str, List[float]] = {}

    def check_rate_limit(self, key: str, limit: int = 60, window_seconds: int = 60) -> Tuple[bool, int]:
        now = time.time()
        cutoff = now - window_seconds

        timestamps = self._history.setdefault(key, [])
        # Evict old timestamps
        self._history[key] = [t for t in timestamps if t > cutoff]

        if len(self._history[key]) >= limit:
            oldest = self._history[key][0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            return False, retry_after

        self._history[key].append(now)
        return True, 0

global_rate_limiter = SecurityRateLimiter()

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects production HTTP security headers and request correlation ID.
    """
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:10]}"

        response: Response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        return response

class StructuredErrorMiddleware(BaseHTTPMiddleware):
    """
    Catches unhandled server exceptions, prevents internal stack trace leakage,
    and returns standardized JSON errors.
    """
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException:
            # Let FastAPI handle explicit HTTPExceptions
            raise
        except Exception as exc:
            request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:10]}"
            # Internal error logging
            print(f"[ERROR] Request {request_id} unhandled exception on {request.method} {request.url.path}: {str(exc)}")

            return JSONResponse(
                status_code=500,
                content={
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred. Please reference the request ID for assistance.",
                    "request_id": request_id,
                    "retryable": True
                },
                headers={
                    "X-Request-ID": request_id,
                    "X-Content-Type-Options": "nosniff"
                }
            )
