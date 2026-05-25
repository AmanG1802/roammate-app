"""Unit tests for app.services.llm.pre_processor — zero-LLM extraction pipeline.

All extraction is regex/keyword/dateutil — pure Python, no network, no DB.
"""
import pytest
from datetime import date

from app.services.llm.pre_processor import (
    pre_extract,
    PreExtracted,
    _extract_city,
    _extract_dates,
    _extract_duration,
    _extract_group_size,
    _extract_budget,
    _extract_vibes,
    _extract_explicit_places,
    _build_residual,
    _parse_date_safe,
)


class TestExtractCity:
    def test_extract_city(self):
        # Test 1a - Single well-known city matched
        city, country, code = _extract_city("I want to visit Tokyo next month")
        assert city == "Tokyo"
        assert country == "Japan"
        assert code == "JP"

        # Test 1b - Multi-word city (New York)
        city, country, code = _extract_city("Planning a trip to New York")
        assert city == "New York"
        assert country == "United States"
        assert code == "US"

        # Test 1c - Case insensitive matching
        city, country, code = _extract_city("let's go to PARIS")
        assert city == "Paris"
        assert country == "France"

        # Test 1d - No city found returns (None, None, None)
        city, country, code = _extract_city("I want to travel somewhere warm")
        assert city is None
        assert country is None
        assert code is None

        # Test 1e - First longest match wins (e.g., "Ho Chi Minh" over "Chi")
        city, country, code = _extract_city("Flying to Ho Chi Minh City")
        assert city == "Ho Chi Minh"
        assert country == "Vietnam"

        # Test 1f - Indian cities
        city, country, code = _extract_city("Weekend trip to Goa")
        assert city == "Goa"
        assert country == "India"
        assert code == "IN"

        # Test 1g - City as part of a larger word is NOT matched (word boundary)
        city, country, code = _extract_city("I'm parisian at heart")
        assert city is None  # "paris" shouldn't match inside "parisian"


class TestExtractDates:
    def test_extract_dates(self):
        # Test 1a - Date range "Jan 15 to 20"
        start, end = _extract_dates("Trip from Jan 15 to 20")
        assert start is not None
        assert start.month == 1
        assert start.day == 15

        # Test 1b - Single date "15 March 2025"
        start, end = _extract_dates("Leaving on 15 March 2025")
        assert start is not None
        assert start == date(2025, 3, 15)
        assert end is None

        # Test 1c - Date with month name "June 5"
        start, end = _extract_dates("Starting June 5")
        assert start is not None
        assert start.month == 6
        assert start.day == 5

        # Test 1d - No dates in text
        start, end = _extract_dates("I want to travel somewhere")
        assert start is None
        assert end is None

        # Test 1e - Month abbreviated
        start, end = _extract_dates("arriving Dec 25, 2025")
        assert start is not None
        assert start.month == 12
        assert start.day == 25


class TestExtractDuration:
    def test_extract_duration(self):
        # Test 1a - "5 days" extracts 5
        assert _extract_duration("Planning a 5 days trip") == 5

        # Test 1b - "3 nights" extracts 3
        assert _extract_duration("3 nights in Bangkok") == 3

        # Test 1c - "a week" extracts 7
        assert _extract_duration("Going for a week") == 7

        # Test 1d - "two weeks" extracts 14
        assert _extract_duration("two weeks in Europe") == 14

        # Test 1e - "2 weeks" extracts 14
        assert _extract_duration("2 weeks adventure") == 14

        # Test 1f - "1 week" extracts 7
        assert _extract_duration("1 week getaway") == 7

        # Test 1g - No duration returns None
        assert _extract_duration("I want to visit Paris") is None

        # Test 1h - "one week" extracts 7
        assert _extract_duration("one week in Bali") == 7

        # Test 1i - Large day count (12 days)
        assert _extract_duration("12 days road trip") == 12


class TestExtractGroupSize:
    def test_extract_group_size(self):
        # Test 1a - "for 4 people"
        assert _extract_group_size("Trip for 4 people") == 4

        # Test 1b - "with 6 friends"
        assert _extract_group_size("Travelling with 6 friends") == 6

        # Test 1c - "couple" returns 2
        assert _extract_group_size("A couple's getaway") == 2

        # Test 1d - "solo" returns 1
        assert _extract_group_size("Solo backpacking") == 1

        # Test 1e - "just me" returns 1
        assert _extract_group_size("Just me exploring") == 1

        # Test 1f - "family" returns 4
        assert _extract_group_size("A family vacation") == 4

        # Test 1g - No group info returns None
        assert _extract_group_size("Trip to Tokyo") is None

        # Test 1h - "for 2 persons"
        assert _extract_group_size("For 2 persons") == 2

        # Test 1i - "two of us"
        assert _extract_group_size("Just the two of us") == 2


class TestExtractBudget:
    def test_extract_budget(self):
        # Test 1a - "budget" keyword
        assert _extract_budget("Looking for budget options") == "budget"

        # Test 1b - "luxury" keyword
        assert _extract_budget("We want a luxury experience") == "luxury"

        # Test 1c - "mid-range"
        assert _extract_budget("Something mid-range would be nice") == "mid"

        # Test 1d - "cheap"
        assert _extract_budget("Cheap hostels and street food") == "budget"

        # Test 1e - "5-star"
        assert _extract_budget("Only 5-star hotels") == "luxury"

        # Test 1f - No budget keywords returns None
        assert _extract_budget("Trip to Paris for a week") is None

        # Test 1g - "backpack" → budget
        assert _extract_budget("Backpack through Southeast Asia") == "budget"

        # Test 1h - "comfortable" → mid
        assert _extract_budget("Something comfortable and nice") == "mid"


class TestExtractVibes:
    def test_extract_vibes(self):
        # Test 1a - Food keyword detected
        vibes = _extract_vibes("I love food and street food tours")
        assert "food" in vibes

        # Test 1b - Multiple vibes detected
        vibes = _extract_vibes("I want hiking, beach, and nightlife")
        assert "nature" in vibes
        assert "nightlife" in vibes

        # Test 1c - No vibes returns empty list
        vibes = _extract_vibes("Going somewhere")
        assert vibes == []

        # Test 1d - Culture keywords
        vibes = _extract_vibes("Visiting museums and art galleries")
        assert "culture" in vibes

        # Test 1e - Adventure keyword
        vibes = _extract_vibes("Diving and snorkeling activities")
        assert "adventure" in vibes

        # Test 1f - Shopping keyword
        vibes = _extract_vibes("Want to explore local markets")
        assert "shopping" in vibes

        # Test 1g - Relaxation keyword
        vibes = _extract_vibes("Looking for spa and wellness retreats")
        assert "relaxation" in vibes

        # Test 1h - Photography keyword
        vibes = _extract_vibes("Best photo spots and viewpoints")
        assert "photography" in vibes


class TestExtractExplicitPlaces:
    def test_extract_explicit_places(self):
        # Test 1a - Quoted places are extracted
        places = _extract_explicit_places('Visit "Eiffel Tower" and "Louvre Museum"')
        assert "Eiffel Tower" in places
        assert "Louvre Museum" in places

        # Test 1b - Title-case sequences are detected
        places = _extract_explicit_places("Check out Marina Bay Sands")
        assert "Marina Bay Sands" in places

        # Test 1c - Single-quoted places
        places = _extract_explicit_places("Want to see 'Golden Gate Bridge'")
        assert "Golden Gate Bridge" in places

        # Test 1d - Common skip words filtered out
        places = _extract_explicit_places("Please find the best restaurants")
        # "Please" starts a title-case word but should be skipped
        filtered_starts = {"Please", "Find", "Best", "The"}
        for p in places:
            assert p.split()[0] not in filtered_starts

        # Test 1e - Max 10 places returned
        text = " ".join(f'"Place {chr(65+i)} Name"' for i in range(15))
        places = _extract_explicit_places(text)
        assert len(places) <= 10

        # Test 1f - Deduplication (same place quoted twice)
        places = _extract_explicit_places('"Taj Mahal" is great. "Taj Mahal" again')
        assert places.count("Taj Mahal") == 1


class TestParseDateSafe:
    def test_parse_date_safe(self):
        # Test 1a - Valid date string
        result = _parse_date_safe("March 15, 2025")
        assert result == date(2025, 3, 15)

        # Test 1b - Invalid/garbage string returns None
        result = _parse_date_safe("not a date at all xyz")
        assert result is None

        # Test 1c - Abbreviated month
        result = _parse_date_safe("Dec 25")
        assert result is not None
        assert result.month == 12
        assert result.day == 25


class TestBuildResidual:
    def test_build_residual(self):
        # Test 1a - City and country are stripped from residual
        extracted = PreExtracted(
            raw_text="5 days in Tokyo Japan with food and culture",
            city="Tokyo",
            country="Japan",
            country_code="JP",
            num_days=5,
            vibes=["food", "culture"],
        )
        residual = _build_residual(extracted.raw_text, extracted)
        assert "Tokyo" not in residual
        assert "Japan" not in residual

        # Test 1b - Duration pattern is stripped
        assert "5 days" not in residual

        # Test 1c - Multiple whitespace collapsed
        assert "  " not in residual

        # Test 1d - Budget keywords stripped
        extracted2 = PreExtracted(
            raw_text="budget trip to cheap hostels",
            budget_tier="budget",
        )
        residual2 = _build_residual(extracted2.raw_text, extracted2)
        assert "budget" not in residual2
        assert "cheap" not in residual2


class TestPreExtract:
    def test_pre_extract_full_sentence(self):
        # Test 1a - Full integration: all signals extracted from one sentence
        text = "Plan a 5 day luxury trip to Tokyo for 4 people with food and culture"
        result = pre_extract(text)

        assert result.city == "Tokyo"
        assert result.country == "Japan"
        assert result.country_code == "JP"
        assert result.num_days == 5
        assert result.group_size == 4
        assert result.budget_tier == "luxury"
        assert "food" in result.vibes
        assert "culture" in result.vibes

    def test_pre_extract_minimal_input(self):
        # Test 1b - Minimal input with no extractable signals
        result = pre_extract("hello")
        assert result.city is None
        assert result.country is None
        assert result.num_days is None
        assert result.group_size is None
        assert result.budget_tier is None
        assert result.vibes == []
        assert result.raw_text == "hello"

    def test_pre_extract_date_range_infers_num_days(self):
        # Test 1c - Date range infers num_days when not explicitly stated
        text = "Trip from Jan 10 to 15, 2025"
        result = pre_extract(text)
        if result.start_date and result.end_date:
            assert result.num_days == (result.end_date - result.start_date).days + 1

    def test_pre_extract_explicit_duration_overrides_date_inference(self):
        # Test 1d - Explicit "3 days" is used even if dates are present
        text = "3 days starting Dec 1"
        result = pre_extract(text)
        assert result.num_days == 3

    def test_pre_extract_residual_text_set(self):
        # Test 1e - residual_text is populated
        text = "5 days in Bali for 2 people budget"
        result = pre_extract(text)
        assert result.residual_text is not None
        assert "Bali" not in result.residual_text


class TestPreExtractedToContextBlock:
    def test_to_context_block(self):
        # Test 1a - Full context block with all fields
        extracted = PreExtracted(
            raw_text="test",
            city="Tokyo",
            country="Japan",
            num_days=5,
            start_date=date(2025, 6, 15),
            end_date=date(2025, 6, 20),
            group_size=4,
            budget_tier="luxury",
            vibes=["food", "culture"],
            explicit_places=["Shibuya Crossing", "Tsukiji Market"],
        )
        block = extracted.to_context_block()
        assert "dest=Tokyo, Japan" in block
        assert "days=5" in block
        assert "from=2025-06-15" in block
        assert "to=2025-06-20" in block
        assert "group=4" in block
        assert "budget=luxury" in block
        assert "vibes=food,culture" in block
        assert "places=Shibuya Crossing;Tsukiji Market" in block

        # Test 1b - Empty extraction returns empty string
        empty = PreExtracted(raw_text="hello")
        assert empty.to_context_block() == ""

        # Test 1c - Partial extraction only includes present fields
        partial = PreExtracted(raw_text="test", city="Paris", country="France")
        block = partial.to_context_block()
        assert "dest=Paris, France" in block
        assert "days=" not in block
        assert "group=" not in block
