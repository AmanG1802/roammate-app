"""Zero-LLM pre-processor that extracts structured signals from free-form text.

Runs before every LLM call in RoammateServiceV1 so the model receives a
compact JSON context block instead of parsing raw prose — saves ~30-40%
input tokens on typical travel queries.

All extraction is regex / keyword / dateutil — no LLM calls.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


# ── City / Country lookup ────────────────────────────────────────────────────
# Curated list of top travel cities.  Kept intentionally short for startup;
# expand to ~5K entries via CSV when needed.

_CITY_COUNTRY: dict[str, str] = {
    "tokyo": "Japan", "kyoto": "Japan", "osaka": "Japan", "nara": "Japan",
    "bangkok": "Thailand", "chiang mai": "Thailand", "phuket": "Thailand",
    "pattaya": "Thailand", "krabi": "Thailand", "koh samui": "Thailand",
    "paris": "France", "nice": "France", "lyon": "France", "marseille": "France",
    "london": "United Kingdom", "edinburgh": "United Kingdom", "manchester": "United Kingdom",
    "rome": "Italy", "florence": "Italy", "venice": "Italy", "milan": "Italy",
    "naples": "Italy", "amalfi": "Italy",
    "barcelona": "Spain", "madrid": "Spain", "seville": "Spain", "valencia": "Spain",
    "new york": "United States", "los angeles": "United States", "san francisco": "United States",
    "miami": "United States", "chicago": "United States", "las vegas": "United States",
    "new orleans": "United States", "hawaii": "United States", "seattle": "United States",
    "berlin": "Germany", "munich": "Germany", "hamburg": "Germany",
    "amsterdam": "Netherlands", "lisbon": "Portugal", "porto": "Portugal",
    "prague": "Czech Republic", "vienna": "Austria", "zurich": "Switzerland",
    "istanbul": "Turkey", "cappadocia": "Turkey", "antalya": "Turkey",
    "dubai": "United Arab Emirates", "abu dhabi": "United Arab Emirates",
    "singapore": "Singapore", "kuala lumpur": "Malaysia", "penang": "Malaysia",
    "bali": "Indonesia", "jakarta": "Indonesia",
    "hanoi": "Vietnam", "ho chi minh": "Vietnam", "da nang": "Vietnam",
    "seoul": "South Korea", "busan": "South Korea",
    "taipei": "Taiwan", "hong kong": "China", "shanghai": "China", "beijing": "China",
    "delhi": "India", "mumbai": "India", "jaipur": "India", "goa": "India",
    "sydney": "Australia", "melbourne": "Australia",
    "cairo": "Egypt", "marrakech": "Morocco",
    "cape town": "South Africa", "nairobi": "Kenya",
    "rio de janeiro": "Brazil", "buenos aires": "Argentina",
    "cancun": "Mexico", "mexico city": "Mexico", "tulum": "Mexico",
    "athens": "Greece", "santorini": "Greece", "mykonos": "Greece",
    "dubrovnik": "Croatia", "split": "Croatia",
    "reykjavik": "Iceland", "copenhagen": "Denmark", "stockholm": "Sweden",
    "oslo": "Norway", "helsinki": "Finland",
}

_CITY_NAMES_SORTED = sorted(_CITY_COUNTRY.keys(), key=len, reverse=True)


# ── Duration patterns ────────────────────────────────────────────────────────

_DURATION_RE = re.compile(
    r"(?:^|\s)(\d{1,2})\s*(?:day|days|night|nights)\b",
    re.IGNORECASE,
)
_WEEK_RE = re.compile(
    r"(?:^|\s)(?:a|one|1)\s*week\b",
    re.IGNORECASE,
)
_TWO_WEEK_RE = re.compile(
    r"(?:^|\s)(?:two|2)\s*weeks?\b",
    re.IGNORECASE,
)

# ── Group size ───────────────────────────────────────────────────────────────

_GROUP_RE = re.compile(
    r"(?:for|with)\s+(\d{1,2})\s*(?:people|ppl|persons?|of us|friends?|travell?ers?)",
    re.IGNORECASE,
)
_COUPLE_RE = re.compile(r"\b(?:couple|two of us|just us|partner and (?:me|i))\b", re.IGNORECASE)
_SOLO_RE = re.compile(r"\b(?:solo|alone|just me|by myself)\b", re.IGNORECASE)
_FAMILY_RE = re.compile(r"\b(?:family)\b", re.IGNORECASE)

# ── Budget tier ──────────────────────────────────────────────────────────────

_BUDGET_KEYWORDS: dict[str, list[str]] = {
    "budget":  ["budget", "cheap", "backpack", "hostel", "frugal", "low cost", "affordable"],
    "mid":     ["mid-range", "mid range", "moderate", "reasonable", "comfortable"],
    "luxury":  ["luxury", "luxurious", "high-end", "premium", "splurge", "5-star", "five star", "bougie"],
}

# ── Vibe / preference keywords ───────────────────────────────────────────────

_VIBE_KEYWORDS: dict[str, list[str]] = {
    "food":       ["food", "eat", "dining", "restaurant", "street food", "cafe", "culinary", "foodie"],
    "culture":    ["culture", "museum", "art", "gallery", "history", "heritage", "temple", "shrine"],
    "nature":     ["nature", "outdoor", "hike", "hiking", "trek", "beach", "mountain", "park", "garden"],
    "shopping":   ["shopping", "market", "mall", "boutique", "souvenir"],
    "nightlife":  ["nightlife", "bar", "club", "pub", "rooftop", "cocktail", "party"],
    "adventure":  ["adventure", "sport", "surf", "dive", "diving", "snorkel", "kayak", "climbing", "bungee"],
    "relaxation": ["relax", "spa", "wellness", "chill", "unwind", "peaceful", "quiet"],
    "family":     ["family", "kid", "kids", "children", "family-friendly"],
    "romantic":   ["romantic", "honeymoon", "couple", "anniversary"],
    "photography":["photo", "photography", "instagram", "scenic", "viewpoint"],
}

# ── Time hint extraction (reused from idea_bin.py) ───────────────────────────

_TIME_RE = re.compile(
    r"(?:at\s+|@\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d{2}:\d{2})",
    re.IGNORECASE,
)

# ── Date extraction via dateutil (lazy import) ───────────────────────────────

_DATE_RANGE_RE = re.compile(
    r"(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*"
    r"\s+\d{1,2})\s*[-–to]+\s*(\d{1,2}(?:\s*,?\s*\d{4})?)\b",
    re.IGNORECASE,
)

_SINGLE_DATE_RE = re.compile(
    r"\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*"
    r"(?:\s+\d{4})?)\b"
    r"|"
    r"\b((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}"
    r"(?:\s*,?\s*\d{4})?)\b",
    re.IGNORECASE,
)

# ── Explicit place names (quoted or title-case sequences) ────────────────────

_QUOTED_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')
_TITLE_PLACE_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+(?:of|the|de|del|di|le|la|el|al))?"
    r"(?:\s+[A-Z][a-z]+){1,4})\b"
)


@dataclass
class PreExtracted:
    """Structured signals extracted from raw user text, zero-LLM."""

    raw_text: str
    city: Optional[str] = None
    country: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    num_days: Optional[int] = None
    group_size: Optional[int] = None
    budget_tier: Optional[str] = None
    vibes: list[str] = field(default_factory=list)
    time_hints: list[str] = field(default_factory=list)
    explicit_places: list[str] = field(default_factory=list)
    residual_text: str = ""

    def to_context_block(self) -> str:
        """Compact string injected into the system prompt."""
        parts: list[str] = []
        if self.city:
            loc = self.city
            if self.country:
                loc += f", {self.country}"
            parts.append(f"dest={loc}")
        if self.num_days:
            parts.append(f"days={self.num_days}")
        if self.start_date:
            parts.append(f"from={self.start_date.isoformat()}")
        if self.end_date:
            parts.append(f"to={self.end_date.isoformat()}")
        if self.group_size:
            parts.append(f"group={self.group_size}")
        if self.budget_tier:
            parts.append(f"budget={self.budget_tier}")
        if self.vibes:
            parts.append(f"vibes={','.join(self.vibes)}")
        if self.explicit_places:
            parts.append(f"places={';'.join(self.explicit_places[:5])}")
        return " | ".join(parts) if parts else ""


def _parse_date_safe(text: str) -> Optional[date]:
    """Best-effort date parse using dateutil; returns None on failure."""
    try:
        from dateutil import parser as dateutil_parser
        dt = dateutil_parser.parse(text, fuzzy=True)
        return dt.date()
    except Exception:
        return None


def _extract_dates(text: str) -> tuple[Optional[date], Optional[date]]:
    """Extract start_date and optional end_date from text."""
    m = _DATE_RANGE_RE.search(text)
    if m:
        start_text = m.group(1)
        end_text = m.group(2)
        start = _parse_date_safe(start_text)
        if start:
            end_text_full = start_text.rsplit(None, 1)[0] + " " + end_text
            end = _parse_date_safe(end_text_full)
            return start, end
    m = _SINGLE_DATE_RE.search(text)
    if m:
        date_text = m.group(1) or m.group(2)
        return _parse_date_safe(date_text), None
    return None, None


def _extract_city(text: str) -> tuple[Optional[str], Optional[str]]:
    """Match city from curated lookup; return (city_title, country) or (None, None)."""
    lower = text.lower()
    for city in _CITY_NAMES_SORTED:
        if re.search(r"\b" + re.escape(city) + r"\b", lower):
            return city.title(), _CITY_COUNTRY[city]
    return None, None


def _extract_duration(text: str) -> Optional[int]:
    if _TWO_WEEK_RE.search(text):
        return 14
    if _WEEK_RE.search(text):
        return 7
    m = _DURATION_RE.search(text)
    if m:
        return int(m.group(1))
    return None


def _extract_group_size(text: str) -> Optional[int]:
    m = _GROUP_RE.search(text)
    if m:
        return int(m.group(1))
    if _COUPLE_RE.search(text):
        return 2
    if _SOLO_RE.search(text):
        return 1
    if _FAMILY_RE.search(text):
        return 4
    return None


def _extract_budget(text: str) -> Optional[str]:
    lower = text.lower()
    for tier, keywords in _BUDGET_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return tier
    return None


def _extract_vibes(text: str) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for vibe, keywords in _VIBE_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                found.append(vibe)
                break
    return found


def _extract_time_hints(text: str) -> list[str]:
    return [m.group(1).strip() for m in _TIME_RE.finditer(text)]


def _extract_explicit_places(text: str) -> list[str]:
    places: list[str] = []
    for m in _QUOTED_RE.finditer(text):
        places.append(m.group(1) or m.group(2))
    for m in _TITLE_PLACE_RE.finditer(text):
        candidate = m.group(1)
        skip = {"I", "We", "My", "The", "This", "That", "Please", "Want",
                "Need", "Find", "Show", "Plan", "Day", "Night", "Good",
                "Best", "Great", "Nice", "Also", "Maybe", "Something"}
        if candidate.split()[0] not in skip:
            places.append(candidate)
    return list(dict.fromkeys(places))[:10]


def _build_residual(text: str, extracted: PreExtracted) -> str:
    """Strip recognised tokens to produce the residual the LLM should focus on."""
    residual = text
    if extracted.city:
        residual = re.sub(re.escape(extracted.city), "", residual, flags=re.IGNORECASE)
    if extracted.country:
        residual = re.sub(re.escape(extracted.country), "", residual, flags=re.IGNORECASE)
    residual = _DURATION_RE.sub("", residual)
    residual = _WEEK_RE.sub("", residual)
    residual = _GROUP_RE.sub("", residual)
    for keywords in _BUDGET_KEYWORDS.values():
        for kw in keywords:
            residual = re.sub(r"\b" + re.escape(kw) + r"\b", "", residual, flags=re.IGNORECASE)
    residual = re.sub(r"\s{2,}", " ", residual).strip()
    return residual


def pre_extract(text: str) -> PreExtracted:
    """Run all extractors on *text* and return a PreExtracted bundle."""
    city, country = _extract_city(text)
    start_date, end_date = _extract_dates(text)
    num_days = _extract_duration(text)
    if start_date and end_date and num_days is None:
        num_days = (end_date - start_date).days + 1

    result = PreExtracted(
        raw_text=text,
        city=city,
        country=country,
        start_date=start_date,
        end_date=end_date,
        num_days=num_days,
        group_size=_extract_group_size(text),
        budget_tier=_extract_budget(text),
        vibes=_extract_vibes(text),
        time_hints=_extract_time_hints(text),
        explicit_places=_extract_explicit_places(text),
    )
    result.residual_text = _build_residual(text, result)
    return result
