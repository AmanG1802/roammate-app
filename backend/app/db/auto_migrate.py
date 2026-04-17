"""
Automatic schema sync: diffs SQLAlchemy metadata against the live PostgreSQL
catalog and emits DDL for anything missing.

Handles:
  - New tables        → created by create_all (already called before this)
  - New columns       → ALTER TABLE … ADD COLUMN IF NOT EXISTS
  - New indexes       → CREATE INDEX IF NOT EXISTS
  - New unique constr → CREATE UNIQUE INDEX IF NOT EXISTS

Does NOT handle (by design — use Alembic if you need these):
  - Column type changes / renames
  - Column drops
  - Table drops
  - Foreign-key constraint changes on existing columns
"""

from __future__ import annotations

import logging
from sqlalchemy import text, MetaData, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.schema import Column

logger = logging.getLogger("app.auto_migrate")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


def _pg_col_type(col: Column) -> str:
    """Render a PostgreSQL column type + inline constraints from a SA Column."""
    from sqlalchemy.dialects.postgresql import dialect as pg_dialect

    compiler = col.type.compile(dialect=pg_dialect())
    parts = [compiler]

    if col.server_default is not None:
        parts.append(f"DEFAULT {col.server_default.arg}")

    if not col.nullable and not col.primary_key:
        parts.append("NOT NULL")

    for fk in col.foreign_keys:
        ref_table = fk.column.table.name
        ref_col = fk.column.name
        on_delete = f" ON DELETE {fk.ondelete}" if fk.ondelete else ""
        parts.append(f'REFERENCES "{ref_table}"("{ref_col}"){on_delete}')

    return " ".join(parts)


async def _get_existing_columns(conn: AsyncConnection) -> set[tuple[str, str]]:
    """Return {(table_name, column_name)} for all columns in the public schema."""
    rows = await conn.execute(text(
        "SELECT table_name, column_name "
        "FROM information_schema.columns "
        "WHERE table_schema = 'public'"
    ))
    return {(r[0], r[1]) for r in rows}


async def _get_existing_indexes(conn: AsyncConnection) -> set[str]:
    """Return {index_name} for all indexes in the public schema."""
    rows = await conn.execute(text(
        "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
    ))
    return {r[0] for r in rows}


async def _get_existing_constraints(conn: AsyncConnection) -> set[str]:
    """Return {constraint_name} for all constraints in the public schema."""
    rows = await conn.execute(text(
        "SELECT conname FROM pg_constraint "
        "JOIN pg_namespace ON pg_namespace.oid = connamespace "
        "WHERE nspname = 'public'"
    ))
    return {r[0] for r in rows}


async def sync_schema(conn: AsyncConnection, metadata: MetaData) -> None:
    """Compare metadata against the live DB and add missing columns/indexes."""
    existing_cols = await _get_existing_columns(conn)
    existing_indexes = await _get_existing_indexes(conn)
    existing_constraints = await _get_existing_constraints(conn)
    added = 0

    for table in metadata.sorted_tables:
        tname = table.name

        # ── missing columns ──────────────────────────────────────────
        for col in table.columns:
            if (tname, col.name) in existing_cols:
                continue
            if col.primary_key:
                continue

            col_sql = _pg_col_type(col)
            stmt = f'ALTER TABLE "{tname}" ADD COLUMN IF NOT EXISTS "{col.name}" {col_sql}'
            try:
                await conn.execute(text(stmt))
                logger.info("added column  %s.%s", tname, col.name)
                added += 1
            except Exception as exc:
                logger.warning("skip column %s.%s: %s", tname, col.name, exc)

        # ── missing indexes (explicit Index objects in __table_args__) ──
        for idx in table.indexes:
            if idx.name in existing_indexes:
                continue
            cols = ", ".join(f'"{c.name}"' for c in idx.columns)
            unique = "UNIQUE " if idx.unique else ""
            stmt = f'CREATE {unique}INDEX IF NOT EXISTS "{idx.name}" ON "{tname}" ({cols})'
            try:
                await conn.execute(text(stmt))
                logger.info("added index   %s", idx.name)
                added += 1
            except Exception as exc:
                logger.warning("skip index %s: %s", idx.name, exc)

        # ── missing unique constraints ───────────────────────────────
        for constraint in table.constraints:
            if not isinstance(constraint, UniqueConstraint):
                continue
            if constraint.name is None:
                continue
            if constraint.name in existing_constraints:
                continue
            cols = ", ".join(f'"{c.name}"' for c in constraint.columns)
            stmt = (
                f'ALTER TABLE "{tname}" ADD CONSTRAINT "{constraint.name}" '
                f'UNIQUE ({cols})'
            )
            try:
                await conn.execute(text(stmt))
                logger.info("added unique  %s", constraint.name)
                added += 1
            except Exception as exc:
                logger.warning("skip unique %s: %s", constraint.name, exc)

    if added:
        logger.info("auto-migrate: applied %d changes", added)
    else:
        logger.info("auto-migrate: schema is up to date")
