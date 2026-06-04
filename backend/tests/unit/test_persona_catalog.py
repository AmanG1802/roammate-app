"""Unit tests for app.config.persona_catalog — travel persona definitions.

Static data validation: enum completeness, label/icon/description coverage.
"""
import pytest
from app.config.persona_catalog import (
    Persona,
    PERSONA_LABELS,
    PERSONA_ICONS,
    PERSONA_DESCRIPTIONS,
    get_catalog,
)


class TestPersonaEnum:
    def test_persona_enum(self):
        # Test 1a - All 14 personas defined
        assert len(Persona) == 14

        # Test 1b - All values are lowercase snake_case strings
        for p in Persona:
            assert p.value == p.value.lower()
            assert " " not in p.value

        # Test 1c - Persona is a str enum (string comparison works)
        assert Persona.FOODIE == "foodie"
        assert Persona.LUXURY == "luxury_traveller"


class TestPersonaLabels:
    def test_persona_labels(self):
        # Test 1a - Every persona has a label
        for p in Persona:
            assert p in PERSONA_LABELS

        # Test 1b - Labels are non-empty title-case strings
        for p, label in PERSONA_LABELS.items():
            assert isinstance(label, str)
            assert len(label) > 0
            assert label[0].isupper()

        # Test 1c - No extra keys beyond enum members
        assert set(PERSONA_LABELS.keys()) == set(Persona)


class TestPersonaIcons:
    def test_persona_icons(self):
        # Test 1a - Every persona has an icon
        for p in Persona:
            assert p in PERSONA_ICONS

        # Test 1b - Icons are non-empty strings (emojis)
        for p, icon in PERSONA_ICONS.items():
            assert isinstance(icon, str)
            assert len(icon) > 0


class TestPersonaDescriptions:
    def test_persona_descriptions(self):
        # Test 1a - Every persona has a description
        for p in Persona:
            assert p in PERSONA_DESCRIPTIONS

        # Test 1b - Descriptions are meaningful (>20 chars)
        for p, desc in PERSONA_DESCRIPTIONS.items():
            assert isinstance(desc, str)
            assert len(desc) > 20, f"{p.value} description is too short"

        # Test 1c - No duplicate descriptions
        descs = list(PERSONA_DESCRIPTIONS.values())
        assert len(descs) == len(set(descs))


class TestGetCatalog:
    def test_get_catalog(self):
        # Test 1a - Returns list of 14 dicts
        catalog = get_catalog()
        assert len(catalog) == 14

        # Test 1b - Each dict has slug, label, icon, description
        for item in catalog:
            assert "slug" in item
            assert "label" in item
            assert "icon" in item
            assert "description" in item

        # Test 1c - Slugs match persona values
        slugs = {item["slug"] for item in catalog}
        values = {p.value for p in Persona}
        assert slugs == values

        # Test 1d - Catalog preserves enum order
        catalog_slugs = [item["slug"] for item in catalog]
        enum_values = [p.value for p in Persona]
        assert catalog_slugs == enum_values
