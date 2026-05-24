"""Frozen NYC tutorial fixtures.

All data here is captured-at-write-time (real place IDs, photo URLs, polyline
strings collected from prior Maps responses). Nothing in this module makes a
network call. The tutorial seeder copies these structures verbatim into a
new tutorial trip so the canned UX is fully reproducible offline.
"""
from __future__ import annotations

from typing import Any

TRIP_NAME = "New York and its Skylines"
TRIP_TIMEZONE = "America/New_York"
DESTINATION_CITY = "New York"
COUNTRY_CODE = "US"
DESTINATION_LAT = 40.7580
DESTINATION_LNG = -73.9855


def _place(
    title: str,
    *,
    description: str,
    category: str,
    place_id: str,
    lat: float,
    lng: float,
    address: str,
    photo_url: str,
    rating: float | None = None,
    price_level: int | None = None,
    time_category: str = "midday",
    types: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "description": description,
        "category": category,
        "place_id": place_id,
        "lat": lat,
        "lng": lng,
        "address": address,
        "photo_url": photo_url,
        "rating": rating,
        "price_level": price_level,
        "types": types or ["point_of_interest"],
        "time_category": time_category,
        "added_by": "AI",
    }


# Day-1 timeline (Times Square + MoMA), Day-2 (Central Park + Brooklyn Bridge),
# Day-3 (Joe's Pizza wrap-up). Times are wall-clock TIME values (no date).
TIMELINE_EVENTS: list[dict[str, Any]] = [
    {
        **_place(
            "Times Square",
            description="Neon-lit crossroads of Broadway — start the trip with classic NYC energy.",
            category="landmark",
            place_id="ChIJmQJIxlVYwokRLgeuocVOGVU",
            lat=40.7580, lng=-73.9855,
            address="Manhattan, NY 10036",
            photo_url="https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=800",
            rating=4.7, time_category="morning",
            types=["tourist_attraction", "landmark"],
        ),
        "day_index": 0, "start": "10:00:00", "end": "11:30:00",
    },
    {
        **_place(
            "Museum of Modern Art",
            description="MoMA — six floors of modern and contemporary masterpieces.",
            category="museum",
            place_id="ChIJKxDbe_lYwokRVf__s8CPn-o",
            lat=40.7614, lng=-73.9776,
            address="11 W 53rd St, New York, NY 10019",
            photo_url="https://images.unsplash.com/photo-1554907984-15263bfd63bd?w=800",
            rating=4.6, price_level=2, time_category="afternoon",
            types=["museum"],
        ),
        "day_index": 0, "start": "14:00:00", "end": "16:30:00",
    },
    {
        **_place(
            "Central Park Picnic",
            description="Picnic on Sheep Meadow with a skyline view.",
            category="park",
            place_id="ChIJ4zGFAZpYwokRGUGph3Mf37k",
            lat=40.7829, lng=-73.9654,
            address="Central Park, New York, NY",
            photo_url="https://images.unsplash.com/photo-1534270804882-6b5048b1c1fc?w=800",
            rating=4.8, time_category="midday",
            types=["park"],
        ),
        "day_index": 1, "start": "12:00:00", "end": "14:00:00",
    },
    {
        **_place(
            "Brooklyn Bridge Sunset Walk",
            description="Cross the bridge from Manhattan toward DUMBO as the sun drops.",
            category="landmark",
            place_id="ChIJK3vOQyNawokRXEa9errBq0U",
            lat=40.7061, lng=-73.9969,
            address="Brooklyn Bridge, New York, NY",
            photo_url="https://images.unsplash.com/photo-1543716091-a840c05249ec?w=800",
            rating=4.8, time_category="evening",
            types=["landmark"],
        ),
        "day_index": 1, "start": "18:30:00", "end": "20:00:00",
    },
    {
        **_place(
            "Joe's Pizza",
            description="Greenwich Village slice institution — the perfect last bite.",
            category="restaurant",
            place_id="ChIJ-fkPNJlZwokR_PtjQqGw3eA",
            lat=40.7305, lng=-74.0024,
            address="7 Carmine St, New York, NY 10014",
            photo_url="https://images.unsplash.com/photo-1601924582970-9238bcb495d9?w=800",
            rating=4.5, price_level=1, time_category="midday",
            types=["restaurant"],
        ),
        "day_index": 2, "start": "13:00:00", "end": "13:45:00",
    },
]


IDEA_BIN_ITEMS: list[dict[str, Any]] = [
    _place(
        "The High Line",
        description="Elevated park built on a former rail line — great for an unhurried walk.",
        category="park",
        place_id="ChIJ5wWyk8VYwokR_4ZyZ0BkY9Y",
        lat=40.7480, lng=-74.0048,
        address="New York, NY",
        photo_url="https://images.unsplash.com/photo-1485871981521-5b1fd3805eee?w=800",
        rating=4.7, time_category="afternoon",
        types=["park"],
    ),
    _place(
        "Statue of Liberty",
        description="Ferry from Battery Park — book ahead for the crown.",
        category="landmark",
        place_id="ChIJPTacEpBQwokRKwIlDXelxkA",
        lat=40.6892, lng=-74.0445,
        address="Liberty Island, NY",
        photo_url="https://images.unsplash.com/photo-1564981797816-1043664bf78d?w=800",
        rating=4.7, time_category="morning",
        types=["landmark"],
    ),
    _place(
        "Top of the Rock",
        description="Observation deck with the best skyline view of the Empire State Building.",
        category="landmark",
        place_id="ChIJ-3QXl_xYwokRJ8L_C1m5jHE",
        lat=40.7587, lng=-73.9787,
        address="30 Rockefeller Plaza, New York, NY",
        photo_url="https://images.unsplash.com/photo-1485738422979-f5c462d49f74?w=800",
        rating=4.8, price_level=2, time_category="evening",
        types=["landmark"],
    ),
    _place(
        "Katz's Delicatessen",
        description="Lower East Side institution — pastrami on rye, no compromises.",
        category="restaurant",
        place_id="ChIJSeitvc1ZwokRsxd9pBC9c1Q",
        lat=40.7223, lng=-73.9874,
        address="205 E Houston St, New York, NY",
        photo_url="https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800",
        rating=4.5, price_level=2, time_category="midday",
        types=["restaurant"],
    ),
]


BRAINSTORM_BIN_ITEMS: list[dict[str, Any]] = [
    _place(
        "Chelsea Market",
        description="Indoor food hall with everything from tacos to lobster rolls.",
        category="food_market",
        place_id="ChIJ8fSrxulZwokRfXIFsUuYUOY",
        lat=40.7421, lng=-74.0061,
        address="75 9th Ave, New York, NY",
        photo_url="https://images.unsplash.com/photo-1555992336-fb0d29498b13?w=800",
        rating=4.6, price_level=2, time_category="midday",
    ),
    _place(
        "9/11 Memorial & Museum",
        description="Reflecting pools where the towers stood; museum below.",
        category="memorial",
        place_id="ChIJq6DDxe9YwokRwoSEXdSr-d8",
        lat=40.7115, lng=-74.0134,
        address="180 Greenwich St, New York, NY",
        photo_url="https://images.unsplash.com/photo-1605130284535-11dd9eedc58a?w=800",
        rating=4.8, time_category="morning",
    ),
    _place(
        "The Met (Metropolitan Museum)",
        description="One of the largest art museums in the world — give it half a day.",
        category="museum",
        place_id="ChIJb8Jg9pZYwokR-qHGtJKzGEo",
        lat=40.7794, lng=-73.9632,
        address="1000 5th Ave, New York, NY",
        photo_url="https://images.unsplash.com/photo-1554907984-15263bfd63bd?w=800",
        rating=4.8, price_level=2, time_category="afternoon",
    ),
    _place(
        "Coney Island Boardwalk",
        description="Old-school boardwalk, Nathan's hot dogs, the Cyclone.",
        category="boardwalk",
        place_id="ChIJ_yqo6wlEwokRrjAcrJrJcYI",
        lat=40.5755, lng=-73.9707,
        address="Coney Island, Brooklyn, NY",
        photo_url="https://images.unsplash.com/photo-1518416927073-a25f3b3a3a14?w=800",
        rating=4.5, time_category="afternoon",
    ),
    _place(
        "Williamsburg Smorgasburg",
        description="Outdoor food market on weekends — Brooklyn's best bite-sized tour.",
        category="food_market",
        place_id="ChIJqaJBu4tbwokRXFmgU3xKtwo",
        lat=40.7224, lng=-73.9606,
        address="90 Kent Ave, Brooklyn, NY",
        photo_url="https://images.unsplash.com/photo-1555992336-03a23c7b20ee?w=800",
        rating=4.6, time_category="midday",
    ),
    _place(
        "Lincoln Center",
        description="Opera, ballet, the Philharmonic — check what's on the night you're there.",
        category="performing_arts",
        place_id="ChIJsxqUNplYwokRl5KSj9p0qbI",
        lat=40.7725, lng=-73.9835,
        address="10 Lincoln Center Plaza, New York, NY",
        photo_url="https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?w=800",
        rating=4.7, price_level=3, time_category="evening",
    ),
]


# Round-robin canned brainstorm assistant replies. Keyed by current message
# count in the trip; we pick replies[count % len(replies)].
CANNED_BRAINSTORM_REPLIES: list[str] = [
    "Great pick! For Day 1 in NYC, I'd anchor mornings around iconic Midtown spots — Times Square, then a museum like MoMA when the heat hits. Want me to suggest restaurants near each?",
    "Love that direction. NYC after dark is unbeatable — Brooklyn Bridge at sunset, a slice at Joe's, and live jazz in the Village. Should I drop a few jazz clubs into your bin?",
    "If you've got a half-day free, the High Line + Chelsea Market combo is hard to beat. Easy walking, lots of food, photogenic the whole way.",
    "Good call thinking ahead. For rainy NYC days, I'd bookmark the Met and the Tenement Museum — both are big enough to spend hours indoors and not feel rushed.",
]

# The tour's "Send a sample message" asks about a rainy-day plan, so we pin its
# reply rather than relying on the round-robin counter landing here.
TUTORIAL_RAINY_DAY_REPLY: str = CANNED_BRAINSTORM_REPLIES[3]


# Seeded user/assistant pairs forming the initial chat history.
INITIAL_BRAINSTORM_HISTORY: list[dict[str, str]] = [
    {"role": "user", "content": "First time in NYC, 3 days. What should I absolutely not miss?"},
    {"role": "assistant", "content": "Welcome! Three days is enough for the highlights. I'd anchor Day 1 in Midtown (Times Square + MoMA), Day 2 in Central Park + Brooklyn Bridge at sunset, and Day 3 around the Village with a Joe's Pizza stop. Want me to dig into food spots near each?"},
    {"role": "user", "content": "Yes please — and a quirky one I wouldn't find on a normal list."},
    {"role": "assistant", "content": "For food, Joe's slice in Greenwich Village is non-negotiable. For quirky: the Mmuseumm in Tribeca — a museum inside an old freight elevator showing tiny, weird artifacts. Five-minute visit, very NYC."},
    {"role": "user", "content": "What about something for the evening?"},
    {"role": "assistant", "content": "Top of the Rock at golden hour beats the Empire State Building (because you can see the Empire State Building from it). Or grab dinner in DUMBO after walking the Brooklyn Bridge — the view back at Manhattan is the postcard shot."},
    {"role": "user", "content": "Any food markets worth a stop?"},
    {"role": "assistant", "content": "Chelsea Market for everyday — about 30 vendors, indoors, great if the weather turns. Weekends, Smorgasburg in Williamsburg is the move — open-air, ~50 vendors, mostly small Brooklyn operators."},
]


# Canned concierge intro chat.
INITIAL_CONCIERGE_HISTORY: list[dict[str, str]] = [
    {"role": "user", "content": "What's the move tonight?"},
    {"role": "assistant", "content": "Brooklyn Bridge at sunset is on your timeline for tonight (18:30). Walk from the Manhattan side — DUMBO has Juliana's Pizza right at the bridge exit if you want dinner after. Want me to add it to tomorrow's timeline?"},
]


CANNED_CONCIERGE_REPLIES: list[str] = [
    "Got it. Based on your timeline, you're free between 16:00 and 18:00 — that's a great window for a quick walk along the High Line. Want me to pencil it in?",
    "I'd swap MoMA to the morning when it's less crowded, and put Central Park in the afternoon. Lower crowds, better light for photos. Want me to apply that?",
    "For dinner near Brooklyn Bridge, Juliana's is the classic move. Walk-in only, expect a 20-min wait around 19:00. Reserve a backup?",
    "Looks like you've got Joe's Pizza on Day 3 — perfect spot. Also: if it rains, the Tenement Museum is two blocks from your hotel.",
]


# Pre-computed day routes (one per day). Polylines here are short
# placeholders — the tutorial overlay calls these "demo routes" so visual
# fidelity is what matters, not navigational accuracy.
DAY_ROUTES: list[dict[str, Any]] = [
    {
        "day_index": 0,
        "encoded_polyline": "_p~iF~ps|U_ulLnnqC_mqNvxq`@",
        "legs": [{"distance_m": 1450, "duration_s": 540, "from": "Times Square", "to": "MoMA"}],
        "total_distance_m": 1450,
        "total_duration_s": 540,
    },
    {
        "day_index": 1,
        "encoded_polyline": "_p~iF~ps|U_ulLnnqC_mqNvxq`@hgkOnvslE",
        "legs": [{"distance_m": 7200, "duration_s": 1800, "from": "Central Park", "to": "Brooklyn Bridge"}],
        "total_distance_m": 7200,
        "total_duration_s": 1800,
    },
    {
        "day_index": 2,
        "encoded_polyline": "_p~iF~ps|U_ulLnnqC",
        "legs": [{"distance_m": 800, "duration_s": 360, "from": "Hotel", "to": "Joe's Pizza"}],
        "total_distance_m": 800,
        "total_duration_s": 360,
    },
]
