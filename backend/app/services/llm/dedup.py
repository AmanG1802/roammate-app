"""Deduplication for brainstorm items before DB insert.

Two-pass strategy:
1. Exact match by ``place_id`` (post-enrichment) against existing trip items.
2. Fuzzy match by normalised title (Levenshtein distance ≤ 3 or exact
   lowercase match) against existing items.

Items that match an existing item on either pass are filtered out.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Sequence


def _normalise(title: str) -> str:
    """Lowercase, strip accents, collapse whitespace, remove punctuation."""
    text = unicodedata.normalize("NFKD", title)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _levenshtein(a: str, b: str) -> int:
    """Basic Levenshtein distance (O(n*m) DP). Sufficient for short titles."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def deduplicate(
    new_items: list[dict[str, Any]],
    existing_items: Sequence[Any],
    *,
    distance_threshold: int = 3,
) -> list[dict[str, Any]]:
    """Return only items from *new_items* that are NOT duplicates of *existing_items*.

    Parameters
    ----------
    new_items:
        Dicts with at least ``title`` and optionally ``place_id``.
    existing_items:
        ORM rows (or dicts) with ``.title`` / ``["title"]`` and
        ``.place_id`` / ``["place_id"]``.
    distance_threshold:
        Max Levenshtein distance to consider a fuzzy title match.
    """
    existing_place_ids: set[str] = set()
    existing_titles: list[str] = []

    for item in existing_items:
        pid = getattr(item, "place_id", None) or (item.get("place_id") if isinstance(item, dict) else None)
        if pid:
            existing_place_ids.add(pid)
        title = getattr(item, "title", None) or (item.get("title", "") if isinstance(item, dict) else "")
        if title:
            existing_titles.append(_normalise(title))

    unique: list[dict[str, Any]] = []
    seen_titles: set[str] = set()

    for item in new_items:
        pid = item.get("place_id")
        if pid and pid in existing_place_ids:
            continue

        norm_title = _normalise(item.get("title", ""))
        if not norm_title:
            unique.append(item)
            continue

        if norm_title in seen_titles:
            continue

        is_dup = False
        for existing_norm in existing_titles:
            if norm_title == existing_norm:
                is_dup = True
                break
            if abs(len(norm_title) - len(existing_norm)) <= distance_threshold:
                if _levenshtein(norm_title, existing_norm) <= distance_threshold:
                    is_dup = True
                    break

        if not is_dup:
            unique.append(item)
            seen_titles.add(norm_title)

    return unique
