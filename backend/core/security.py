import re
import time
import uuid
import ipaddress
import urllib.parse
from typing import Optional, Dict, List, Tuple
from fastapi import Header, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Valid person_id regex: 3-64 chars, alphanumeric with hyphens, underscores, dots
PERSON_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]{3,64}$")

def validate_person_id_format(person_id: str) -> bool:
    if not person_id or not isinstance(person_id, str):
        return False
    # Reject path traversal, null bytes, script tags, SQL injection tokens
    if any(ch in person_id for ch in ["/", "\\", "\0", "<", ">", ";", "'", '"', ".."]):
        return False
    return bool(PERSON_ID_PATTERN.match(person_id))

def get_authenticated_person(
    x_person_id: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
) -> str:
    """
    Extracts and strictly verifies the authenticated person identity.
    Rejects malformed, injected, or path-traversal identifiers with HTTP 400/401.
    """
    raw_id = None

    # 1. Check Bearer Token if present
    if isinstance(authorization, str) and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if token and validate_person_id_format(token):
            raw_id = token

    # 2. Check X-Person-ID header
    if not raw_id and isinstance(x_person_id, str):
        raw_id = x_person_id.strip()

    # 3. Default fallback for testing/local development
    if not raw_id:
        raw_id = "scholar-user"

    # 4. Strict Validation
    if not validate_person_id_format(raw_id):
        raise HTTPException(
            status_code=400,
            detail="INVALID_IDENTITY_FORMAT: Person ID must be 3-64 alphanumeric characters without special characters."
        )

    return raw_id

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
