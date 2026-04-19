"""Time category labels and their default display times."""
from __future__ import annotations

TIME_CATEGORIES = [
    "early morning",
    "morning",
    "midday",
    "afternoon",
    "late afternoon",
    "evening",
    "night",
    "late night",
]

# Default display time string shown in Idea Bin when no exact time is set
TIME_CATEGORY_DEFAULTS: dict[str, str] = {
    "early morning": "7:00 AM",
    "morning":       "10:00 AM",
    "midday":        "12:00 PM",
    "afternoon":     "2:00 PM",
    "late afternoon": "4:00 PM",
    "evening":       "6:00 PM",
    "night":         "8:00 PM",
    "late night":    "10:00 PM",
}
