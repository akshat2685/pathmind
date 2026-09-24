"""Vercel serverless entrypoint for the PathMind FastAPI backend.

Vercel's Python runtime imports this module and calls ``handler`` for every
request (see vercel.json rewrites). Mangum adapts ASGI <-> API Gateway events.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mangum import Mangum  # noqa: E402

from backend.main import app  # noqa: E402

# lifespan="off": serverless functions must not hold startup/shutdown state.
handler = Mangum(app, lifespan="off")
