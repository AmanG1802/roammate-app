"""Unit tests for app.core.time_categories — static constants validation.

Validates the integrity of the TIME_CATEGORIES list and TIME_CATEGORY_DEFAULTS mapping.
"""
from app.core.time_categories import TIME_CATEGORIES, TIME_CATEGORY_DEFAULTS


class TestTimeCategories:
    def test_time_categories(self):
        # Test 1a - Contains all 8 expected categories
        assert len(TIME_CATEGORIES) == 8

        # Test 1b - Correct ordering from early to late
        expected_order = [
            "early morning", "morning", "midday", "afternoon",
            "late afternoon", "evening", "night", "late night",
        ]
        assert TIME_CATEGORIES == expected_order

        # Test 1c - No duplicates
        assert len(TIME_CATEGORIES) == len(set(TIME_CATEGORIES))

        # Test 1d - All entries are lowercase strings
        for cat in TIME_CATEGORIES:
            assert isinstance(cat, str)
            assert cat == cat.lower()


class TestTimeCategoryDefaults:
    def test_time_category_defaults(self):
        # Test 1a - Every category has a default time
        for cat in TIME_CATEGORIES:
            assert cat in TIME_CATEGORY_DEFAULTS

        # Test 1b - No extra keys beyond the known categories
        assert set(TIME_CATEGORY_DEFAULTS.keys()) == set(TIME_CATEGORIES)

        # Test 1c - All values are strings in HH:MM AM/PM format
        import re
        time_re = re.compile(r"^\d{1,2}:\d{2} [AP]M$")
        for cat, val in TIME_CATEGORY_DEFAULTS.items():
            assert time_re.match(val), f"{cat} has invalid time format: {val}"

        # Test 1d - Default times are in chronological order
        from datetime import datetime
        times = []
        for cat in TIME_CATEGORIES:
            t = datetime.strptime(TIME_CATEGORY_DEFAULTS[cat], "%I:%M %p")
            times.append(t)
        for i in range(len(times) - 1):
            assert times[i] < times[i + 1], (
                f"{TIME_CATEGORIES[i]} ({TIME_CATEGORY_DEFAULTS[TIME_CATEGORIES[i]]}) "
                f"is not before {TIME_CATEGORIES[i+1]} ({TIME_CATEGORY_DEFAULTS[TIME_CATEGORIES[i+1]]})"
            )

        # Test 1e - Specific known defaults
        assert TIME_CATEGORY_DEFAULTS["early morning"] == "7:00 AM"
        assert TIME_CATEGORY_DEFAULTS["midday"] == "12:00 PM"
        assert TIME_CATEGORY_DEFAULTS["night"] == "8:00 PM"
