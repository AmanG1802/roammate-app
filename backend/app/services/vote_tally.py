"""Single-query vote tallies.

Reading vote counts as three separate aggregates (COUNT up, COUNT down, my
vote) costs three round-trips per call — and historically per item — so listing
50 events fired 150 queries (docs/[31] D4). This computes up / down / my_vote
for a batch of targets in one conditional-aggregation query that compiles on
both Postgres and SQLite.
"""
from __future__ import annotations

from typing import Dict, Sequence, Tuple

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def tally_votes(
    db: AsyncSession,
    vote_model: type,
    target_col,
    target_ids: Sequence[int],
    user_id: int,
) -> Dict[int, Tuple[int, int, int]]:
    """Return ``{target_id: (up, down, my_vote)}`` for *target_ids*.

    ``my_vote`` is 0 when the user has not voted. Targets with no votes are
    absent from the result (callers default to ``(0, 0, 0)``).
    """
    if not target_ids:
        return {}
    stmt = (
        select(
            target_col.label("target_id"),
            func.sum(case((vote_model.value == 1, 1), else_=0)).label("up"),
            func.sum(case((vote_model.value == -1, 1), else_=0)).label("down"),
            func.max(
                case((vote_model.user_id == user_id, vote_model.value), else_=None)
            ).label("mine"),
        )
        .where(target_col.in_(list(target_ids)))
        .group_by(target_col)
    )
    rows = (await db.execute(stmt)).all()
    return {
        r.target_id: (int(r.up or 0), int(r.down or 0), int(r.mine or 0))
        for r in rows
    }
