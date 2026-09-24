"""
Test-only in-memory stand-in for the Supabase PostgREST client.

Implements the small chainable query surface the backend actually uses:
select / eq / in_ / ilike / order / limit / insert / upsert / update / delete
with execute() returning a FakeResponse exposing .data.

No network, no credentials, no real writes: per-test state that is wiped by
resetting the client between tests. Only used from test fixtures; never
imported by application code.
"""

import re
import uuid
import copy


class FakeResponse:
    def __init__(self, data):
        self.data = data


def _like_to_regex(pattern: str) -> str:
    # Convert a SQL LIKE pattern (% wildcards) to a full-match regex.
    out = []
    for ch in pattern:
        if ch == "%":
            out.append(".*")
        elif ch == "_":
            out.append(".")
        else:
            out.append(re.escape(ch))
    return "^" + "".join(out) + "$"


class FakeQuery:
    def __init__(self, table, op="select", payload=None):
        self._table = table
        self._op = op
        self._payload = payload
        self._filters = []          # list of (kind, col, value)
        self._order_col = None
        self._order_desc = False
        self._limit = None
        self._select_cols = None

    # ---- chainable builders ----
    def select(self, cols):
        self._op = "select"
        self._select_cols = cols
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def in_(self, col, vals):
        self._filters.append(("in", col, list(vals)))
        return self

    def ilike(self, col, pattern):
        self._filters.append(("ilike", col, pattern))
        return self

    def order(self, col, desc=False):
        self._order_col = col
        self._order_desc = bool(desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def insert(self, data):
        self._op = "insert"
        self._payload = data
        return self

    def upsert(self, data, on_conflict=None):
        self._op = "upsert"
        self._payload = data
        self._on_conflict = on_conflict
        return self

    def update(self, data):
        self._op = "update"
        self._payload = data
        return self

    def delete(self):
        self._op = "delete"
        return self

    # ---- execution ----
    def _matches(self, row):
        for kind, col, val in self._filters:
            rv = row.get(col)
            if kind == "eq":
                if rv != val:
                    return False
            elif kind == "in":
                if rv not in val:
                    return False
            elif kind == "ilike":
                if rv is None or not re.match(
                        _like_to_regex(val), str(rv), re.IGNORECASE):
                    return False
        return True

    def execute(self):
        rows = self._table._rows
        if self._op == "select":
            data = [copy.deepcopy(r) for r in rows if self._matches(r)]
            if self._order_col:
                data.sort(key=lambda r: (r.get(self._order_col) is None,
                                         r.get(self._order_col)),
                          reverse=self._order_desc)
            if self._limit is not None:
                data = data[:self._limit]
            return FakeResponse(data)
        if self._op == "insert":
            items = self._payload if isinstance(self._payload, list) else [self._payload]
            inserted = []
            for item in items:
                row = copy.deepcopy(item)
                rows.append(row)
                inserted.append(copy.deepcopy(row))
            return FakeResponse(inserted)
        if self._op == "upsert":
            items = self._payload if isinstance(self._payload, list) else [self._payload]
            out = []
            conflict = getattr(self, "_on_conflict", None)
            for item in items:
                row = copy.deepcopy(item)
                target = None
                if conflict:
                    for existing in rows:
                        if existing.get(conflict) == row.get(conflict):
                            target = existing
                            break
                if target is not None:
                    target.update(row)
                    out.append(copy.deepcopy(target))
                else:
                    rows.append(row)
                    out.append(copy.deepcopy(row))
            return FakeResponse(out)
        if self._op == "update":
            updated = []
            for row in rows:
                if self._matches(row):
                    row.update(copy.deepcopy(self._payload))
                    updated.append(copy.deepcopy(row))
            return FakeResponse(updated)
        if self._op == "delete":
            removed = [r for r in rows if self._matches(r)]
            self._table._rows = [r for r in rows if not self._matches(r)]
            return FakeResponse([copy.deepcopy(r) for r in removed])
        raise AssertionError(f"unknown op {self._op}")


class FakeTable:
    def __init__(self):
        self._rows = []

    def select(self, cols="*"):
        return FakeQuery(self, op="select").select(cols)

    def insert(self, data):
        return FakeQuery(self, op="insert", payload=data)

    def upsert(self, data, on_conflict=None):
        q = FakeQuery(self, op="upsert", payload=data)
        q._on_conflict = on_conflict
        return q

    def update(self, data):
        return FakeQuery(self, op="update", payload=data)

    def delete(self):
        return FakeQuery(self, op="delete")


class _FakeUser:
    def __init__(self, uid):
        self.id = uid


class _FakeUserResponse:
    def __init__(self, uid):
        self.user = _FakeUser(uid)


class _FakeAdmin:
    def __init__(self, auth):
        self._auth = auth

    def create_user(self, payload):
        uid = str(uuid.uuid4())
        self._auth._users[uid] = payload if isinstance(payload, dict) else {}
        return _FakeUserResponse(uid)

    def delete_user(self, uid):
        self._auth._users.pop(uid, None)
        return None


class _FakeAuth:
    def __init__(self, token_map):
        self._token_map = token_map      # token -> uid
        self._users = {}
        self.admin = _FakeAdmin(self)

    def get_user(self, token):
        uid = self._token_map.get(token)
        if uid is None:
            raise ValueError("Invalid token")
        return _FakeUserResponse(uid)


class FakeSupabaseClient:
    """Mimics the supabase-py client surface used by the backend."""

    def __init__(self):
        self._tables = {}
        self.auth = _FakeAuth({
            "alice-token": "11111111-1111-4111-8111-111111111111",
            "bob-token": "22222222-2222-4222-8222-222222222222",
        })

    def table(self, name):
        if name not in self._tables:
            self._tables[name] = FakeTable()
        return self._tables[name]

    def reset(self):
        self._tables = {}
        self.auth._users = {}


class FakeSupabaseAdapter:
    """Drop-in replacement for SupabaseAdapter in tests."""

    def __init__(self):
        self.client = FakeSupabaseClient()
        self.url = "fake://supabase.test"
        self.key = "fake-key"

    async def check_database_health(self):
        return {"status": "ok", "database": "supabase"}
