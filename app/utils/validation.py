from typing import Any

from ..constants import threshold_limits, conversion_factors


def station_needs_conversion(station_code: str) -> bool:
    """Check if a station needs unit conversion (only stations 001-009 and 031-038)."""
    conversion_station_codes = {
        "001", "002", "003", "004", "005", "006", "007", "008", "009",
        "031", "032", "033", "034", "035", "036", "037", "038"
    }
    try:
        code_int = int(station_code)
        return 1 <= code_int <= 9 or 31 <= code_int <= 38
    except (TypeError, ValueError):
        # Fall back to string comparison when station_code can't be cast to int
        return station_code in conversion_station_codes


def value_violates_threshold(pollutant: str, value: Any, station_code: str = None) -> bool:
    """Check if a value violates min or max thresholds for the given pollutant.

    Args:
        pollutant: Name of the pollutant (e.g., "PM25", "CO")
        value: The raw value from the database
        station_code: Station code to determine if conversion is needed (optional)
                     If provided, will convert values for stations 001-009 and 031-038

    Returns:
        True if value is below min or above max threshold, False otherwise
    """
    limits = threshold_limits.get(pollutant)
    if not limits:
        return False

    try:
        float_value = float(value)

        # Convert value to proper units if needed (for stations 001-009 and 031-038)
        if station_code is not None and station_needs_conversion(station_code):
            float_value = float_value * \
                float(conversion_factors.get(pollutant, 1.0))

        # Check both min and max thresholds
        max_limit = limits.get("max")
        min_limit = limits.get("min")

        if max_limit is not None and float_value > max_limit:
            return True
        if min_limit is not None and float_value < min_limit:
            return True

        return False
    except (ValueError, TypeError):
        return False
