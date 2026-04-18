"""Thin LLM facade.

While real LLM integration is deferred (Phase 1A), every call short-circuits
to a deterministic Thailand / Bangkok payload when ``settings.LLM_ENABLED``
is False. The return shape matches what the real client will produce so the
entire pipeline (extract → persist → promote → render) exercises real code
paths even before the keys are wired.
"""
from __future__ import annotations

from typing import Any
from app.core.config import settings


_BANGKOK_FALLBACK_ITEMS: list[dict[str, Any]] = [
    {
        "title": "Grand Palace",
        "description": "Ornate 18th-century royal complex and Thailand's most iconic landmark.",
        "category": "sight",
        "place_id": "ChIJAZRkDm2Y4jARlEBP0aD8lVs",
        "lat": 13.7500,
        "lng": 100.4913,
        "address": "Na Phra Lan Rd, Phra Borom Maha Ratchawang, Bangkok 10200",
        "photo_url": "https://images.unsplash.com/photo-1563492065599-3520f775eeed?w=800",
        "rating": 4.7,
        "price_level": 2,
        "types": ["tourist_attraction", "point_of_interest"],
        "opening_hours": {"mon_sun": "8:30–15:30"},
        "phone": "+66 2 623 5500",
        "website": "https://www.royalgrandpalace.th/",
        "time_hint": "morning",
        "url_source": None,
    },
    {
        "title": "Wat Arun",
        "description": "Riverside \"Temple of Dawn\" with a towering porcelain-tiled prang.",
        "category": "sight",
        "place_id": "ChIJnzTgFUKf4jARHkDjCHWmUBc",
        "lat": 13.7437,
        "lng": 100.4888,
        "address": "158 Thanon Wang Doem, Wat Arun, Bangkok 10600",
        "photo_url": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=800",
        "rating": 4.6,
        "price_level": 1,
        "types": ["tourist_attraction", "place_of_worship"],
        "opening_hours": {"mon_sun": "8:00–18:00"},
        "phone": "+66 2 891 2185",
        "website": "https://www.watarun1.com/",
        "time_hint": "late afternoon",
        "url_source": None,
    },
    {
        "title": "Chatuchak Weekend Market",
        "description": "Sprawling weekend market with 15,000 stalls — food, crafts, vintage.",
        "category": "activity",
        "place_id": "ChIJN1lEl7Oe4jARsyWw3PluDDY",
        "lat": 13.7999,
        "lng": 100.5503,
        "address": "587, 10 Kamphaeng Phet 2 Rd, Chatuchak, Bangkok 10900",
        "photo_url": "https://images.unsplash.com/photo-1555272406-2765e2e6d3a0?w=800",
        "rating": 4.4,
        "price_level": 1,
        "types": ["market", "tourist_attraction"],
        "opening_hours": {"sat_sun": "9:00–18:00"},
        "phone": None,
        "website": "https://www.chatuchakmarket.org/",
        "time_hint": "weekend morning",
        "url_source": None,
    },
    {
        "title": "Lumphini Park",
        "description": "Bangkok's central green lung — jogging paths, paddle boats, monitor lizards.",
        "category": "sight",
        "place_id": "ChIJhSI5pr2f4jAR_OsuSJZe-w0",
        "lat": 13.7306,
        "lng": 100.5418,
        "address": "192 Wireless Rd, Lumphini, Pathum Wan, Bangkok 10330",
        "photo_url": "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=800",
        "rating": 4.5,
        "price_level": 0,
        "types": ["park", "point_of_interest"],
        "opening_hours": {"mon_sun": "4:30–21:00"},
        "phone": None,
        "website": None,
        "time_hint": "early morning",
        "url_source": None,
    },
    {
        "title": "Chinatown (Yaowarat)",
        "description": "Neon-lit street-food mecca and Thailand's oldest Chinese district.",
        "category": "neighborhood",
        "place_id": "ChIJWY3W4kOe4jARCkWmuoz8AAQ",
        "lat": 13.7398,
        "lng": 100.5113,
        "address": "Yaowarat Rd, Samphanthawong, Bangkok 10100",
        "photo_url": "https://images.unsplash.com/photo-1555921015-5532091f6026?w=800",
        "rating": 4.6,
        "price_level": 2,
        "types": ["neighborhood", "tourist_attraction"],
        "opening_hours": {"mon_sun": "17:00–00:00"},
        "phone": None,
        "website": None,
        "time_hint": "evening",
        "url_source": None,
    },
    {
        "title": "Jim Thompson House",
        "description": "Teak-house museum built by the American who revived Thai silk.",
        "category": "sight",
        "place_id": "ChIJK4qXI8if4jAR9fRrJ4BIIFQ",
        "lat": 13.7492,
        "lng": 100.5286,
        "address": "6 Kasemsan 2 Alley, Wang Mai, Pathum Wan, Bangkok 10330",
        "photo_url": "https://images.unsplash.com/photo-1528181304800-259b08848526?w=800",
        "rating": 4.5,
        "price_level": 2,
        "types": ["museum", "tourist_attraction"],
        "opening_hours": {"mon_sun": "10:00–18:00"},
        "phone": "+66 2 216 7368",
        "website": "https://www.jimthompsonhouse.com/",
        "time_hint": "midday",
        "url_source": None,
    },
]


_THAILAND_PLAN_FALLBACK: dict[str, Any] = {
    "trip_name": "Thailand Getaway",
    "start_date": None,
    "duration_days": 3,
    "items": _BANGKOK_FALLBACK_ITEMS,
}


_CHAT_FALLBACK_REPLY = (
    "Here are some great spots in Bangkok you might like: Grand Palace, Wat Arun, "
    "Chatuchak Weekend Market, Lumphini Park, Chinatown (Yaowarat), and Jim Thompson House. "
    "Want me to pull these into your Brainstorm Bin?"
)


async def chat(history: list[dict], user_message: str) -> str:
    """Single-turn reply given the running conversation. Returns assistant content."""
    if not settings.LLM_ENABLED:
        return _CHAT_FALLBACK_REPLY
    raise NotImplementedError("Real LLM integration lands in Phase 1A")


async def extract_items(history: list[dict]) -> list[dict[str, Any]]:
    """Turn a chat history into structured brainstorm items."""
    if not settings.LLM_ENABLED:
        return [dict(item) for item in _BANGKOK_FALLBACK_ITEMS]
    raise NotImplementedError("Real LLM integration lands in Phase 1A")


async def plan_trip(prompt: str) -> dict[str, Any]:
    """Turn a single free-form prompt into a trip preview + brainstorm item seed."""
    if not settings.LLM_ENABLED:
        return {
            **_THAILAND_PLAN_FALLBACK,
            "items": [dict(item) for item in _BANGKOK_FALLBACK_ITEMS],
        }
    raise NotImplementedError("Real LLM integration lands in Phase 1A")
