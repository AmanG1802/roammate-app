"""Opt-in keyset (cursor) pagination for list endpoints (docs/[31] D3).

Backward compatibility is the hard constraint: the iOS and Web clients consume
the current bare-array / envelope responses, so pagination must not change the
default response shape. Therefore it is **opt-in**:

  * No ``limit`` and no ``cursor`` query param  → endpoint behaves exactly as
    before (returns the full result set).
  * ``limit`` and/or ``cursor`` provided        → the endpoint returns one page
    (keyset-ordered by ``id``) and advertises the next page. Bare-list endpoints
    expose it via the ``X-Next-Cursor`` / ``X-Has-More`` response headers (body
    shape unchanged); envelope endpoints add ``next_cursor`` / ``has_more`` keys.

Keyset (WHERE id </> last_id) is used rather than OFFSET so deep pages stay
cheap and stable under concurrent inserts. ``id`` is monotonic with
``created_at`` (autoincrement PK), so ordering by id matches the existing
created_at ordering.
"""
from __future__ import annotations

import base64
from typing import Optional

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def is_paginated(limit: Optional[int], cursor: Optional[str]) -> bool:
    """True when the caller opted into pagination (so defaults stay unchanged)."""
    return limit is not None or cursor is not None


def clamp_limit(limit: Optional[int]) -> int:
    if limit is None or limit <= 0:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


def encode_cursor(last_id: int) -> str:
    return base64.urlsafe_b64encode(str(last_id).encode()).decode()


def decode_cursor(cursor: Optional[str]) -> Optional[int]:
    if not cursor:
        return None
    try:
        return int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, TypeError):
        return None


def apply_keyset(stmt, id_col, *, cursor: Optional[str], limit: int, descending: bool):
    """Add keyset WHERE + ORDER BY + LIMIT(+1) to *stmt*.

    Fetches ``limit + 1`` rows so the caller can detect ``has_more`` and drop the
    sentinel. The id-based ORDER BY replaces any prior ordering on the paginated
    path only.
    """
    last_id = decode_cursor(cursor)
    if last_id is not None:
        stmt = stmt.where(id_col < last_id) if descending else stmt.where(id_col > last_id)
    stmt = stmt.order_by(id_col.desc() if descending else id_col.asc())
    return stmt.limit(limit + 1)


def page_slice(rows: list, limit: int) -> tuple[list, bool]:
    """Split the ``limit + 1`` fetch into (page, has_more)."""
    has_more = len(rows) > limit
    return (rows[:limit], has_more)


async def paginate_scalars(db, response, stmt, id_col, limit, cursor, *, descending: bool = False):
    """Run a keyset page for a scalar (single-entity) select and set the
    ``X-Next-Cursor`` / ``X-Has-More`` headers on *response*. Returns the page
    list (body shape unchanged for the client)."""
    eff = clamp_limit(limit)
    stmt = apply_keyset(stmt, id_col, cursor=cursor, limit=eff, descending=descending)
    rows = (await db.execute(stmt)).scalars().all()
    page, has_more = page_slice(rows, eff)
    response.headers["X-Has-More"] = "true" if has_more else "false"
    if page and has_more:
        response.headers["X-Next-Cursor"] = encode_cursor(page[-1].id)
    return page
