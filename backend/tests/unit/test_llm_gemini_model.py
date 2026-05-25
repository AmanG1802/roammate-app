"""Unit tests for Gemini model schema helpers."""
import pytest
from app.services.llm.models.gemini_model import (
    _clean_schema_for_gemini,
    _strip_additional_properties,
)


class TestStripAdditionalProperties:
    def test_strips_top_level(self):
        # Test 1a - Removes additionalProperties from top-level
        schema = {"type": "object", "additionalProperties": False, "properties": {}}
        _strip_additional_properties(schema)
        assert "additionalProperties" not in schema

    def test_strips_nested(self):
        # Test 1b - Recursively strips from nested properties
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "inner": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"x": {"type": "string"}},
                },
            },
        }
        _strip_additional_properties(schema)
        assert "additionalProperties" not in schema
        assert "additionalProperties" not in schema["properties"]["inner"]

    def test_strips_from_allof(self):
        # Test 1c - Strips from allOf/anyOf/oneOf entries
        schema = {
            "allOf": [
                {"type": "object", "additionalProperties": False, "properties": {}},
            ],
        }
        _strip_additional_properties(schema)
        assert "additionalProperties" not in schema["allOf"][0]

    def test_no_op_on_simple_schema(self):
        # Test 1d - Schema without additionalProperties is unchanged
        schema = {"type": "string"}
        _strip_additional_properties(schema)
        assert schema == {"type": "string"}


class TestCleanSchemaForGemini:
    def test_inlines_defs_and_strips(self):
        # Test 1a - Full pipeline: inline $defs + strip additionalProperties
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "item": {"$ref": "#/$defs/Item"},
            },
            "$defs": {
                "Item": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"name": {"type": "string"}},
                },
            },
        }
        result = _clean_schema_for_gemini(schema)
        assert "$defs" not in result
        assert "additionalProperties" not in result
        assert "additionalProperties" not in result["properties"]["item"]
        assert result["properties"]["item"]["properties"]["name"]["type"] == "string"

    def test_no_defs_still_strips(self):
        # Test 1b - Without $defs, still strips additionalProperties
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"x": {"type": "integer"}},
        }
        result = _clean_schema_for_gemini(schema)
        assert "additionalProperties" not in result
