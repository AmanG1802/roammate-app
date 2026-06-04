"""Unit tests for Claude model schema helper _clean_schema_for_claude."""
import pytest
from app.services.llm.models.claude_model import _clean_schema_for_claude


class TestCleanSchemaForClaude:
    def test_no_defs_passthrough(self):
        # Test 1a - Schema without $defs returns unchanged
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = _clean_schema_for_claude(schema.copy())
        assert result == {"type": "object", "properties": {"name": {"type": "string"}}}

    def test_inlines_defs(self):
        # Test 1b - $defs are inlined into $ref references
        schema = {
            "type": "object",
            "properties": {
                "item": {"$ref": "#/$defs/Item"},
            },
            "$defs": {
                "Item": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
            },
        }
        result = _clean_schema_for_claude(schema)
        assert "$defs" not in result
        assert "$ref" not in str(result)
        assert result["properties"]["item"]["type"] == "object"
        assert result["properties"]["item"]["properties"]["name"]["type"] == "string"

    def test_inlines_definitions_alt_key(self):
        # Test 1c - "definitions" key (older schemas) also inlined
        schema = {
            "type": "object",
            "properties": {
                "item": {"$ref": "#/definitions/Thing"},
            },
            "definitions": {
                "Thing": {"type": "string"},
            },
        }
        result = _clean_schema_for_claude(schema)
        assert "definitions" not in result
        assert result["properties"]["item"]["type"] == "string"

    def test_multiple_refs_inlined(self):
        # Test 1d - Multiple references to same def are all inlined
        schema = {
            "type": "object",
            "properties": {
                "first": {"$ref": "#/$defs/Shared"},
                "second": {"$ref": "#/$defs/Shared"},
            },
            "$defs": {
                "Shared": {"type": "integer"},
            },
        }
        result = _clean_schema_for_claude(schema)
        assert result["properties"]["first"]["type"] == "integer"
        assert result["properties"]["second"]["type"] == "integer"
