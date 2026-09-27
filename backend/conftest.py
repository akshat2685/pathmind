import sys
import os
from pathlib import Path

# Tests must run without real credentials. The persistence layer fail-fasts
# at import time when SUPABASE_URL / SUPABASE_SECRET_KEY are missing, so
# provide dummy values here. supabase-py's create_client is lazy — no network
# traffic happens at construction. Tests that need a live database use the
# requires_live_db fixture below and skip honestly on dummy credentials.
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJyb2xlIjogInNlcnZpY2Vfcm9sZSIsICJpc3MiOiAic3VwYWJhc2UiLCAicmVmIjogInRlc3QifQ.ImR1bW15LXNpZ25hdHVyZSI")

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest

USING_DUMMY_DB = os.environ.get("SUPABASE_URL") == "https://test.supabase.co"


@pytest.fixture
def requires_live_db():
    """Skip DB-backed tests when running on dummy credentials."""
    if USING_DUMMY_DB:
        pytest.skip("needs a live Supabase test database (dummy credentials in use)")
