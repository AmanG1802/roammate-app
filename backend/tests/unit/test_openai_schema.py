"""Unit tests for OpenAI model's _ensure_additional_properties_false helper.

Pure recursive schema transformation with no network.
"""
import pytest
from app.services.llm.models.openai_model import _ensure_additional_properties_false


class TestEnsureAdditionalPropertiesFalse:
    def test_simple_object(self):
        # Test 1a - Adds additionalProperties: false to a simple object schema
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        }
        result = _ensure_additional_properties_false(schema)
        assert result["additionalProperties"] is False

    def test_nested_objects(self):
        # Test 1b - Recursively adds to nested object properties
        schema = {
            "type": "object",
            "properties": {
                "address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                    },
                },
            },
        }
        result = _ensure_additional_properties_false(schema)
        assert result["additionalProperties"] is False
        assert result["properties"]["address"]["additionalProperties"] is False

    def test_does_not_override_existing(self):
        # Test 1c - Does not override if additionalProperties already set
        schema = {
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "additionalProperties": True,
        }
        result = _ensure_additional_properties_false(schema)
        # setdefault does not override existing True
        assert result["additionalProperties"] is True

    def test_array_items(self):
        # Test 1d - Processes items in array schemas
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "string"},
                        },
                    },
                },
            },
        }
        result = _ensure_additional_properties_false(schema)
        assert result["properties"]["tags"]["items"]["additionalProperties"] is False

    def test_defs(self):
        # Test 1e - Processes $defs
        schema = {
            "type": "object",
            "properties": {
                "item": {"$ref": "#/$defs/Item"},
            },
            "$defs": {
                "Item": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
            },
        }
        result = _ensure_additional_properties_false(schema)
        assert result["$defs"]["Item"]["additionalProperties"] is False

    def test_allof_anyof(self):
        # Test 1f - Processes allOf, anyOf, oneOf
        schema = {
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "allOf": [
                {
                    "type": "object",
                    "properties": {"y": {"type": "string"}},
                }
            ],
        }
        result = _ensure_additional_properties_false(schema)
        assert result["allOf"][0]["additionalProperties"] is False

    def test_non_object_schema_untouched(self):
        # Test 1g - Schema without type=object or properties is not modified
        schema = {"type": "string"}
        result = _ensure_additional_properties_false(schema)
        assert "additionalProperties" not in result

    def test_schema_with_properties_but_no_type(self):
        # Test 1h - Schema with properties but no explicit "type" still gets the flag
        schema = {
            "properties": {
                "name": {"type": "string"},
            },
        }
        result = _ensure_additional_properties_false(schema)
        assert result["additionalProperties"] is False

    def test_empty_schema(self):
        # Test 1i - Empty schema returns unchanged
        schema = {}
        result = _ensure_additional_properties_false(schema)
        assert result == {}
