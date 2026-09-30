"""
Round-4 regression tests (college MVP):

1. Auth verification survives a transient Supabase Auth read timeout:
   get_authenticated_person retries infra failures and only surfaces
   AUTH_SERVICE_UNAVAILABLE after the bounded attempts are exhausted.
   (Live symptom, 2026-09-30: `AUTH_SERVICE_UNAVAILABLE: authentication
   service unavailable (ReadTimeout)` on onboarding Step 5.)

2. A verified token is verified at most once per short cache window:
   the dashboard fires many authenticated calls per load and every one
   used to pay a live auth round-trip (more chances to hit a timeout).

3. Cached resources saved with legacy video timestamps
   ({"label", "source", "start_seconds"} only — what the research
   pipeline used to write) parse into ResourceRecord instead of being
   silently dropped on read, which made every cached VIDEO invisible
   and every phase show "no video or notes linked".
"""
import httpx
import pytest

import backend.core.security as security
from backend.core.college_schemas import ResourceRecord, VideoTimestamp


class _SlowThenOkAuth:
    """auth.get_user that raises ReadTimeout N times, then succeeds."""

    def __init__(self, failures, uid="11111111-1111-4111-8111-111111111111"):
        self.failures = failures
        self.uid = uid
        self.calls = 0

    def get_user(self, token):
        self.calls += 1
        if self.calls <= self.failures:
            raise httpx.ReadTimeout("read timed out")
        user = type("U", (), {"id": self.uid})()
        return type("R", (), {"user": user})()


class _FakeClient:
    def __init__(self, auth):
        self.auth = auth


class _FakeAdapter:
    def __init__(self, auth):
        self.client = _FakeClient(auth)


@pytest.fixture(autouse=True)
def fast_auth(monkeypatch):
    """Shrink retry/timeout constants and isolate the module cache."""
    monkeypatch.setattr(security, "AUTH_VERIFY_TIMEOUT_SECONDS", 1)
    monkeypatch.setattr(security, "AUTH_VERIFY_BACKOFF_SECONDS", 0.01)
    security._auth_verify_cache.clear()
    yield
    security._auth_verify_cache.clear()


def _install_adapter(monkeypatch, auth):
    adapter = _FakeAdapter(auth)
    monkeypatch.setattr(security, "get_supabase_adapter", lambda: adapter)
    return adapter


def test_auth_retries_transient_read_timeout(monkeypatch):
    auth = _SlowThenOkAuth(failures=1)
    _install_adapter(monkeypatch, auth)
    uid = security.get_authenticated_person("Bearer test-token-retry")
    assert uid == "11111111-1111-4111-8111-111111111111"
    assert auth.calls == 2


def test_auth_cache_avoids_repeat_verification(monkeypatch):
    auth = _SlowThenOkAuth(failures=0)
    _install_adapter(monkeypatch, auth)
    first = security.get_authenticated_person("Bearer test-token-cache")
    second = security.get_authenticated_person("Bearer test-token-cache")
    assert first == second == auth.uid
    assert auth.calls == 1


def test_auth_exhausted_retries_raise_503(monkeypatch):
    auth = _SlowThenOkAuth(failures=99)
    _install_adapter(monkeypatch, auth)
    with pytest.raises(Exception) as excinfo:
        security.get_authenticated_person("Bearer test-token-down")
    assert getattr(excinfo.value, "status_code", None) == 503
    assert auth.calls == security.AUTH_VERIFY_MAX_ATTEMPTS


def test_legacy_video_timestamps_parse_with_defaults():
    ts = VideoTimestamp(**{"label": "full video", "source": "estimated",
                           "start_seconds": 0})
    assert ts.start_seconds == 0
    assert ts.end_seconds == 0
    assert ts.purpose == "full video"


def test_resource_record_accepts_legacy_video_rows():
    row = {
        "resource_id": "res_legacy_video",
        "subject_id": "SUBJ-101",
        "title": "Legacy cached lecture",
        "provider": "YouTube",
        "url": "https://example.edu/video/legacy",
        "resource_type": "VIDEO",
        "source_id": "src_test",
        "source_tier": "A",
        "verified_by": None,
        "verification_status": "VERIFIED",
        "retrieved_at": "2026-09-30T00:00:00Z",
        "last_verified_at": "2026-09-30T00:00:00Z",
        "video_timestamps": [
            {"label": "full video", "source": "estimated", "start_seconds": 0}
        ],
        "document_sections": [],
        "estimated_minutes": 30,
    }
    record = ResourceRecord(**row)
    assert record.resource_type == "VIDEO"
    assert record.video_timestamps[0].purpose == "full video"
    assert record.video_timestamps[0].end_seconds == 0
