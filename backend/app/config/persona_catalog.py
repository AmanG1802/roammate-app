from enum import Enum


class Persona(str, Enum):
    FOODIE = "foodie"
    CULTURE_BUFF = "culture_buff"
    NATURE_LOVER = "nature_lover"
    ADVENTURE_SEEKER = "adventure_seeker"
    BEACH_BUM = "beach_bum"
    HISTORY_NERD = "history_nerd"
    NIGHTLIFE = "nightlife_enthusiast"
    SHOPAHOLIC = "shopaholic"
    WELLNESS = "wellness_seeker"
    PHOTOGRAPHER = "photographer"
    FAMILY = "family_traveller"
    SOLO = "solo_explorer"
    LUXURY = "luxury_traveller"
    BUDGET = "budget_hacker"


PERSONA_LABELS: dict[Persona, str] = {
    Persona.FOODIE: "Foodie",
    Persona.CULTURE_BUFF: "Culture Buff",
    Persona.NATURE_LOVER: "Nature Lover",
    Persona.ADVENTURE_SEEKER: "Adventure Seeker",
    Persona.BEACH_BUM: "Beach Bum",
    Persona.HISTORY_NERD: "History Nerd",
    Persona.NIGHTLIFE: "Nightlife Enthusiast",
    Persona.SHOPAHOLIC: "Shopaholic",
    Persona.WELLNESS: "Wellness Seeker",
    Persona.PHOTOGRAPHER: "Photographer",
    Persona.FAMILY: "Family Traveller",
    Persona.SOLO: "Solo Explorer",
    Persona.LUXURY: "Luxury Traveller",
    Persona.BUDGET: "Budget Hacker",
}

PERSONA_ICONS: dict[Persona, str] = {
    Persona.FOODIE: "🍜",
    Persona.CULTURE_BUFF: "🎭",
    Persona.NATURE_LOVER: "🌿",
    Persona.ADVENTURE_SEEKER: "🧗",
    Persona.BEACH_BUM: "🏖️",
    Persona.HISTORY_NERD: "📜",
    Persona.NIGHTLIFE: "🍸",
    Persona.SHOPAHOLIC: "🛍️",
    Persona.WELLNESS: "🧘",
    Persona.PHOTOGRAPHER: "📸",
    Persona.FAMILY: "👨‍👩‍👧",
    Persona.SOLO: "🎒",
    Persona.LUXURY: "💎",
    Persona.BUDGET: "💸",
}

PERSONA_DESCRIPTIONS: dict[Persona, str] = {
    Persona.FOODIE: "Loves local cuisine, street food, and reservation-only restaurants.",
    Persona.CULTURE_BUFF: "Drawn to museums, galleries, theatre, and local arts scenes.",
    Persona.NATURE_LOVER: "Seeks parks, forests, scenic hikes, and wildlife encounters.",
    Persona.ADVENTURE_SEEKER: "Thrives on outdoor thrills — climbing, rafting, zip-lining, extreme sports.",
    Persona.BEACH_BUM: "Happiest on sandy shores, snorkelling reefs, and beachside sunsets.",
    Persona.HISTORY_NERD: "Fascinated by ancient ruins, heritage sites, and stories behind places.",
    Persona.NIGHTLIFE: "Energised by bars, clubs, live music, and vibrant after-dark scenes.",
    Persona.SHOPAHOLIC: "Hunts for local markets, boutiques, and unique souvenirs.",
    Persona.WELLNESS: "Prioritises spas, yoga retreats, meditation centres, and rest.",
    Persona.PHOTOGRAPHER: "Plans trips around golden-hour shots, hidden viewpoints, and visual stories.",
    Persona.FAMILY: "Needs family-friendly activities, safe neighbourhoods, and kid-approved dining.",
    Persona.SOLO: "Prefers self-paced exploration, solo-safe accommodations, and authentic local encounters.",
    Persona.LUXURY: "Seeks five-star stays, fine dining, private tours, and premium experiences.",
    Persona.BUDGET: "Maximises every dollar — free attractions, hostels, street food, and travel hacks.",
}


def get_catalog() -> list[dict]:
    return [
        {
            "slug": persona.value,
            "label": PERSONA_LABELS[persona],
            "icon": PERSONA_ICONS[persona],
            "description": PERSONA_DESCRIPTIONS[persona],
        }
        for persona in Persona
    ]
