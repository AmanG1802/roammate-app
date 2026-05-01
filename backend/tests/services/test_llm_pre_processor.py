"""§1C — Pre-processor tests.

Verifies zero-LLM signal extraction from free-form travel queries.
"""
from __future__ import annotations

from app.services.llm.pre_processor import PreExtracted, pre_extract


def test_pre_processor_extracts_city_and_country():
    result = pre_extract("5 days in Bangkok with 4 friends")
    assert result.city == "Bangkok"
    assert result.country == "Thailand"
    assert result.num_days == 5
    assert result.group_size == 4


def test_pre_processor_extracts_budget_tier():
    result = pre_extract("luxury trip to Paris")
    assert result.budget_tier == "luxury"
    assert result.city == "Paris"


def test_pre_processor_extracts_vibes():
    result = pre_extract("I want food and nightlife in Tokyo")
    assert "food" in result.vibes
    assert "nightlife" in result.vibes


def test_pre_processor_extracts_solo():
    result = pre_extract("solo trip to Bali")
    assert result.group_size == 1


def test_pre_processor_extracts_couple():
    result = pre_extract("romantic getaway for couple in Santorini")
    assert result.group_size == 2


def test_pre_processor_extracts_week_duration():
    result = pre_extract("a week in Rome")
    assert result.num_days == 7


def test_pre_processor_extracts_two_weeks():
    result = pre_extract("two weeks in Japan")
    assert result.num_days == 14


def test_pre_processor_no_city_returns_none():
    result = pre_extract("suggest something fun for the weekend")
    assert result.city is None
    assert result.country is None


def test_pre_processor_to_context_block_format():
    result = pre_extract("3 days in Bangkok budget food trip solo")
    block = result.to_context_block()
    assert "dest=Bangkok, Thailand" in block
    assert "days=3" in block
    assert "budget=budget" in block


def test_pre_processor_empty_input():
    result = pre_extract("")
    assert result.city is None
    assert result.num_days is None
    assert result.to_context_block() == ""


def test_pre_processor_explicit_places_from_quotes():
    result = pre_extract('I want to visit "Wat Pho" and "Grand Palace"')
    assert "Wat Pho" in result.explicit_places
    assert "Grand Palace" in result.explicit_places
