"""Deterministic fallback data for when ``LLM_ENABLED`` is False.

The Bangkok dataset exercises the full pipeline (extract -> persist ->
promote -> render) without requiring an API key.  Every field matches
the ``BrainstormBinItem`` / ``BrainstormItemBase`` schema.
"""
from __future__ import annotations

from typing import Any


BANGKOK_FALLBACK_ITEMS: list[dict[str, Any]] = [
    {
        "title": "Thip Samai Pad Thai",
        "description": "Bangkok's most legendary Pad Thai — fried in lard over charcoal since 1966.",
        "category": "Food & Dining",
        "place_id": "ChIJI8KbGkif4jARJsT1k6LdGEs",
        "lat": 13.7537,
        "lng": 100.5022,
        "address": "313 315 Maha Chai Rd, Samran Rat, Phra Nakhon, Bangkok 10200",
        "photo_url": "https://images.unsplash.com/photo-1559314809-0d155014e29e?w=800",
        "rating": 4.6,
        "price_level": 1,
        "types": ["restaurant", "food"],
        "time_category": "evening",
    },
    {
        "title": "Bangkok National Museum",
        "description": "Thailand's largest museum with royal regalia, Buddha sculptures, and Thai art spanning 1,000 years.",
        "category": "Culture & Arts",
        "place_id": "ChIJ5XvKkWuY4jARlD7K4QdYrMI",
        "lat": 13.7578,
        "lng": 100.4918,
        "address": "Na Phra That Alley, Phra Borom Maha Ratchawang, Phra Nakhon, Bangkok 10200",
        "photo_url": "https://images.unsplash.com/photo-1534430480872-3498386e7856?w=800",
        "rating": 4.4,
        "price_level": 1,
        "types": ["museum", "tourist_attraction"],
        "time_category": "morning",
    },
    {
        "title": "Lumphini Park",
        "description": "Bangkok's central green lung — jogging paths, paddle boats, and monitor lizards.",
        "category": "Nature & Outdoors",
        "place_id": "ChIJhSI5pr2f4jAR_OsuSJZe-w0",
        "lat": 13.7306,
        "lng": 100.5418,
        "address": "192 Wireless Rd, Lumphini, Pathum Wan, Bangkok 10330",
        "photo_url": "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=800",
        "rating": 4.5,
        "price_level": 0,
        "types": ["park", "point_of_interest"],
        "time_category": "early morning",
    },
    {
        "title": "Chatuchak Weekend Market",
        "description": "Sprawling weekend market with 15,000 stalls — clothing, crafts, vintage, and street food.",
        "category": "Shopping",
        "place_id": "ChIJN1lEl7Oe4jARsyWw3PluDDY",
        "lat": 13.7999,
        "lng": 100.5503,
        "address": "587, 10 Kamphaeng Phet 2 Rd, Chatuchak, Bangkok 10900",
        "photo_url": "https://images.unsplash.com/photo-1555272406-2765e2e6d3a0?w=800",
        "rating": 4.4,
        "price_level": 1,
        "types": ["market", "tourist_attraction"],
        "time_category": "midday",
    },
    {
        "title": "Asiatique The Riverfront",
        "description": "Open-air night bazaar on the Chao Phraya River with 1,500 shops, restaurants, and a Ferris wheel.",
        "category": "Entertainment",
        "place_id": "ChIJp_gx4kuf4jARy4qXR9ZFtEk",
        "lat": 13.7006,
        "lng": 100.4996,
        "address": "2194 Charoen Krung Rd, Wat Phraya Krai, Bang Kho Laem, Bangkok 10120",
        "photo_url": "https://images.unsplash.com/photo-1508193638397-1c4234db14d8?w=800",
        "rating": 4.4,
        "price_level": 2,
        "types": ["entertainment", "tourist_attraction"],
        "time_category": "late afternoon",
    },
    {
        "title": "Muay Thai at Rajadamnern Stadium",
        "description": "Live Muay Thai bouts at Bangkok's oldest boxing stadium — an unforgettable sports spectacle.",
        "category": "Sports & Adventure",
        "place_id": "ChIJJfLHukmY4jAR4ZNEqM6vD5s",
        "lat": 13.7622,
        "lng": 100.5056,
        "address": "1 Rajadamnern Nok Ave, Pom Prap Sattru Phai, Bangkok 10100",
        "photo_url": "https://images.unsplash.com/photo-1555597673-b21d5c935865?w=800",
        "rating": 4.5,
        "price_level": 2,
        "types": ["stadium", "sport"],
        "time_category": "afternoon",
    },
    {
        "title": "Wat Pho",
        "description": "Temple of the Reclining Buddha — a 46-metre gold-plated statue and home of traditional Thai massage.",
        "category": "Religious & Spiritual",
        "place_id": "ChIJZ2jJi2uY4jARNMnJbE56pMk",
        "lat": 13.7465,
        "lng": 100.4927,
        "address": "2 Sanam Chai Rd, Phra Borom Maha Ratchawang, Phra Nakhon, Bangkok 10200",
        "photo_url": "https://images.unsplash.com/photo-1563492065599-3520f775eeed?w=800",
        "rating": 4.7,
        "price_level": 1,
        "types": ["temple", "tourist_attraction", "place_of_worship"],
        "time_category": "morning",
    },
    {
        "title": "Sky Bar at Lebua State Tower",
        "description": "Open-air rooftop bar on the 64th floor — immortalised in The Hangover II with sweeping city panoramas.",
        "category": "Nightlife",
        "place_id": "ChIJ_xU0pkuf4jARkiGETjg-bF0",
        "lat": 13.7213,
        "lng": 100.5146,
        "address": "1055 Si Lom, Si Lom, Bang Rak, Bangkok 10500",
        "photo_url": "https://images.unsplash.com/photo-1514214246283-d427a95c5d2f?w=800",
        "rating": 4.3,
        "price_level": 4,
        "types": ["nightlife", "rooftop", "bar"],
        "time_category": "night",
    },
    {
        "title": "Grand Palace",
        "description": "Ornate 18th-century royal complex housing Wat Phra Kaew and Thailand's most sacred Emerald Buddha.",
        "category": "Landmarks & Viewpoints",
        "place_id": "ChIJAZRkDm2Y4jARlEBP0aD8lVs",
        "lat": 13.7500,
        "lng": 100.4913,
        "address": "Na Phra Lan Rd, Phra Borom Maha Ratchawang, Bangkok 10200",
        "photo_url": "https://images.unsplash.com/photo-1563492065599-3520f775eeed?w=800",
        "rating": 4.7,
        "price_level": 2,
        "types": ["landmark", "tourist_attraction", "point_of_interest"],
        "time_category": "late afternoon",
    },
    {
        "title": "Bangkok by Tuk Tuk Food Tour",
        "description": "Guided tuk-tuk street food tour through Chinatown and hidden alley eateries with a local guide.",
        "category": "Activities & Tours",
        "place_id": None,
        "lat": 13.7398,
        "lng": 100.5113,
        "address": "Yaowarat Rd, Samphanthawong, Bangkok 10100",
        "photo_url": "https://images.unsplash.com/photo-1555921015-5532091f6026?w=800",
        "rating": 4.8,
        "price_level": 2,
        "types": ["tour", "activity", "food_tour"],
        "time_category": "afternoon",
    },
]


THAILAND_PLAN_FALLBACK: dict[str, Any] = {
    "trip_name": "Thailand Getaway",
    "start_date": None,
    "duration_days": 3,
    "items": BANGKOK_FALLBACK_ITEMS,
}


CHAT_FALLBACK_REPLY: str = (
    "Here are 10 great experiences in Bangkok — one for every vibe: "
    "Thip Samai Pad Thai (Food & Dining), Bangkok National Museum (Culture & Arts), "
    "Lumphini Park (Nature & Outdoors), Chatuchak Weekend Market (Shopping), "
    "Asiatique The Riverfront (Entertainment), Muay Thai at Rajadamnern Stadium (Sports & Adventure), "
    "Wat Pho (Religious), Sky Bar at Lebua (Nightlife), Grand Palace (Landmarks), "
    "and a Bangkok Tuk Tuk Food Tour (Activities & Tours). "
    "Want me to pull these into your Brainstorm Bin?"
)
