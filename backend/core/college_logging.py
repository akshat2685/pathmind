"""
Structured observability for the PathMind College MVP (TRD §25).

Tiny, dependency-free event logger: every college service/route emits machine-
readable JSON lines with an event name, the acting user_id, per-stage latency in
milliseconds, and an outcome / error code.

Privacy rule: NEVER pass raw learner content (messages, answers, notes, memory
text) into these events. Log identifiers, counts, and codes only.
"""

import json
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(
    event: str,
    *,
    user_id: Optional[str] = None,
    latency_ms: Optional[float] = None,
    outcome: Optional[str] = None,
    error_code: Optional[str] = None,
    **fields: Any,
) -> None:
    """
    Emit one structured JSON log line to stdout.

    Args:
        event: Stable machine-readable name, e.g. "college.plan.generated".
        user_id: Acting learner id (identifier only, never content).
        latency_ms: Per-stage latency in milliseconds.
        outcome: "ok" | "error" | "skipped" | domain outcome string.
        error_code: Machine-readable error code when outcome is an error.
        **fields: Extra scalar fields (counts, ids, codes). No free text.
    """
    record: dict[str, Any] = {"ts": _utc_now_iso(), "event": event}
    if user_id is not None:
        record["user_id"] = user_id
    if latency_ms is not None:
        record["latency_ms"] = round(latency_ms, 2)
    if outcome is not None:
        record["outcome"] = outcome
    if error_code is not None:
        record["error_code"] = error_code
    for key, value in fields.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            record[key] = value
    print(json.dumps(record), file=sys.stdout, flush=True)


@contextmanager
def timed_stage(
    event: str, *, user_id: Optional[str] = None, **fields: Any
) -> Iterator[None]:
    """
    Context manager that times a pipeline stage and logs its outcome.

    Usage:
        with timed_stage("college.assessment.evaluated", user_id=uid,
                          question_count=len(questions)):
            ...
    """
    start = time.perf_counter()
    try:
        yield
    except Exception as exc:
        log_event(
            event,
            user_id=user_id,
            latency_ms=(time.perf_counter() - start) * 1000.0,
            outcome="error",
            error_code=type(exc).__name__,
            **fields,
        )
        raise
    log_event(
        event,
        user_id=user_id,
        latency_ms=(time.perf_counter() - start) * 1000.0,
        outcome="ok",
        **fields,
    )
