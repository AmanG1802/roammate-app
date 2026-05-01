"""§2A — Persona catalog tests.

Verifies the persona catalog data integrity and enum alignment.
"""
from __future__ import annotations

from app.config.persona_catalog import (
    Persona,
    PERSONA_DESCRIPTIONS,
    PERSONA_ICONS,
    PERSONA_LABELS,
    get_catalog,
)


def test_catalog_has_14_entries():
    catalog = get_catalog()
    assert len(catalog) == 14


def test_catalog_slugs_are_unique():
    catalog = get_catalog()
    slugs = [entry["slug"] for entry in catalog]
    assert len(slugs) == len(set(slugs))


def test_catalog_slugs_match_persona_enum():
    catalog = get_catalog()
    enum_values = {p.value for p in Persona}
    catalog_slugs = {entry["slug"] for entry in catalog}
    assert catalog_slugs == enum_values


def test_catalog_each_entry_has_label_icon_description():
    catalog = get_catalog()
    for entry in catalog:
        assert "slug" in entry
        assert "label" in entry and len(entry["label"]) > 0
        assert "icon" in entry and len(entry["icon"]) > 0
        assert "description" in entry and len(entry["description"]) > 0


def test_catalog_descriptions_under_140_chars():
    """Guard prompt budget — descriptions should be concise."""
    for persona, desc in PERSONA_DESCRIPTIONS.items():
        assert len(desc) <= 140, (
            f"Persona {persona.value} description is {len(desc)} chars (max 140)"
        )


def test_all_personas_have_labels():
    for persona in Persona:
        assert persona in PERSONA_LABELS


def test_all_personas_have_icons():
    for persona in Persona:
        assert persona in PERSONA_ICONS


def test_all_personas_have_descriptions():
    for persona in Persona:
        assert persona in PERSONA_DESCRIPTIONS
