from typing import Tuple, Dict, Any, Optional

from ..db import get_sql_connection
from ..constants import (
    aqi_categories,
    stations,
    pollutant_breakpoints,
)
from ..constants import conversion_factors
from ..utils.validation import value_violates_threshold
from .alert_service import record_sentinel_alert


def _compute_aqi_from_breakpoints(value: Optional[float], breakpoints) -> Optional[float]:
    """
    Compute AQI from concentration value using breakpoint table.
    Returns raw AQI as float (not capped at 500) or None if invalid.
    """
    if value is None or value == "":
        return None
    try:
        conc = float(value)
        if conc < 0:
            return None
    except (ValueError, TypeError):
        return None

    # Round to 1 decimal place for consistent precision with breakpoints
    conc = round(conc, 1)

    # Try to find matching breakpoint
    last_normal_bp = None
    for i, bp in enumerate(breakpoints):
        bp_lo = float(bp["BPLo"])
        bp_hi = float(bp["BPHi"])

        # Handle the special case where BPLo == BPHi (highest breakpoint)
        if bp_lo == bp_hi:
            # This is the highest breakpoint - use it for all values >= BPLo
            if conc >= bp_lo:
                # For values at exactly the breakpoint, return IHi
                if conc == bp_lo:
                    return float(bp["IHi"])

                # For values above, use the previous bracket's slope to extrapolate
                if last_normal_bp is not None:
                    prev_bp_lo = float(last_normal_bp["BPLo"])
                    prev_bp_hi = float(last_normal_bp["BPHi"])
                    prev_i_lo = float(last_normal_bp["ILo"])
                    prev_i_hi = float(last_normal_bp["IHi"])

                    # Use the slope from the previous (second-to-last) bracket
                    slope = (prev_i_hi - prev_i_lo) / (prev_bp_hi - prev_bp_lo)
                    # Continue from where the current bracket starts
                    aqi = float(bp["IHi"]) + slope * (conc - bp_lo)
                else:
                    # Fallback: just return the highest AQI value if no previous bracket
                    aqi = float(bp["IHi"])
                return aqi
        elif bp_lo <= conc <= bp_hi:
            # Normal case: concentration falls within this breakpoint range
            if bp_hi == bp_lo:
                # Avoid division by zero
                aqi = float(bp["IHi"])
            else:
                aqi = ((bp["IHi"] - bp["ILo"]) / (bp_hi - bp_lo)
                       ) * (conc - bp_lo) + bp["ILo"]
            return aqi

        # Track last normal (non-equal) breakpoint for extrapolation
        if bp_lo != bp_hi:
            last_normal_bp = bp

    # If no breakpoint matched, return None
    return None


def _category_for_aqi(aqi: Optional[int]) -> Optional[str]:
    if aqi is None:
        return None
    for cat in aqi_categories:
        if cat["range"][0] <= aqi <= cat["range"][1]:
            return cat["category"]
    return None


def calculate_aqi_from_reading(reading: Dict[str, Any]) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """
    Compute AQI across available pollutants in reading and return (AQI, category, pollutant).

    The AQI is capped at 500 for display, but the dominant pollutant is determined
    by the raw (uncapped) AQI values to ensure accuracy.
    """
    max_aqi_raw: Optional[float] = None
    max_pollutant: Optional[str] = None

    for pollutant_name, breakpoints in pollutant_breakpoints.items():
        value = reading.get(pollutant_name)

        # normalize sentinel values and threshold violations
        try:
            # Only check for -9999.0 and 985.0 (88888.0 removed, Status column handles <75%)
            if value is not None and (float(value) == -9999.0 or float(value) == 985.0):
                value = None
            elif value is not None and value_violates_threshold(pollutant_name, value):
                value = None
        except (ValueError, TypeError):
            pass

        aqi_raw = _compute_aqi_from_breakpoints(value, breakpoints)
        if aqi_raw is not None and (max_aqi_raw is None or aqi_raw > max_aqi_raw):
            max_aqi_raw = aqi_raw
            max_pollutant = pollutant_name

    # Cap the displayed AQI at 500, but the dominant pollutant is based on raw values
    max_aqi_display = None
    if max_aqi_raw is not None:
        max_aqi_display = min(round(max_aqi_raw), 500)

    category = _category_for_aqi(max_aqi_display)
    return max_aqi_display, category, max_pollutant


def get_latest_aqi_data(station_name_filter: Optional[str] = None) -> Dict[str, Any]:
    data: Dict[str, Any] = {}

    target_stations = stations
    if station_name_filter:
        target_stations = {code: name for code,
                           name in stations.items() if name == station_name_filter}
        if not target_stations:
            return {"error": f"Station '{station_name_filter}' not found"}

    try:
        conn = get_sql_connection()
        cursor = conn.cursor()

        # Column indices: follow order in constants.pollutants
        # pollutants = ["O3","CO","SO2","NO","NO2","NOX","PM10","PM2.5", ...]
        # We need those pollutant columns that are part of pollutant_breakpoints
        # Build select list dynamically for the required indices
        breakpoint_pollutants = list(pollutant_breakpoints.keys())
        # Map pollutant name to its ValueN index based on position in constants.pollutants
        from ..constants import pollutants as all_pollutants
        value_indices = {p: (all_pollutants.index("PM2.5") + 1 if p == "PM25" else all_pollutants.index(p) + 1)
                         for p in breakpoint_pollutants}
        select_cols = [
            f"Value{value_indices[p]} AS {p}" for p in breakpoint_pollutants]

        for station_code, station_name in target_stations.items():
            table = f'dbo.S{station_code}T05'
            try:
                cursor.execute(
                    f"SELECT TOP 1 Date_Time, {', '.join(select_cols)} FROM {table} ORDER BY Date_Time DESC"
                )
                row = cursor.fetchone()

                if not row:
                    data[station_name] = {"error": "no data"}
                    continue

                columns = [col[0] for col in cursor.description]
                row_dict = dict(zip(columns, row))
                latest_datetime = row_dict.get("Date_Time")
                # Build a reading-like dict limited to pollutants with breakpoints
                reading: Dict[str, Any] = {p: row_dict.get(
                    p) for p in breakpoint_pollutants}
                # record sentinel alerts on latest (only -9999.0 and 985.0)
                for p in breakpoint_pollutants:
                    try:
                        v = reading.get(p)
                        if v is not None and (float(v) == -9999.0 or float(v) == 985.0):
                            record_sentinel_alert(
                                station_name, p, v, latest_datetime)
                    except (ValueError, TypeError):
                        pass
                # convert units before AQI only for stations 001-009

                def _needs_conv(code: str) -> bool:
                    try:
                        return int(code) <= 9
                    except Exception:
                        return code in {"001", "002", "003", "004", "005", "006", "007", "008", "009"}

                if _needs_conv(station_code):
                    conv_reading: Dict[str, Any] = {}
                    for p, v in reading.items():
                        try:
                            # Only check for -9999.0 and 985.0 (88888.0 removed)
                            if v is None or v == "" or float(v) in (-9999.0, 985.0):
                                conv_reading[p] = None
                            else:
                                converted_val = float(
                                    v) * float(conversion_factors.get(p, 1.0))
                                # Check if converted value violates thresholds
                                if value_violates_threshold(p, converted_val):
                                    conv_reading[p] = None
                                else:
                                    conv_reading[p] = converted_val
                        except (ValueError, TypeError):
                            conv_reading[p] = None
                    aqi_input = conv_reading
                else:
                    # For stations that don't need conversion, still need to filter out threshold violations
                    aqi_input = {}
                    for p, v in reading.items():
                        try:
                            # Only check for -9999.0 and 985.0 (88888.0 removed)
                            if v is None or v == "" or float(v) in (-9999.0, 985.0) or value_violates_threshold(p, v):
                                aqi_input[p] = None
                            else:
                                aqi_input[p] = v
                        except (ValueError, TypeError):
                            aqi_input[p] = None

                aqi, category, dominant = calculate_aqi_from_reading(aqi_input)
                station_result = {
                    "Date_Time": str(latest_datetime),
                    "AQI": aqi,
                    "AQI_category": category,
                    "Dominant_Pollutant": dominant
                }

                if station_name_filter:
                    conn.close()
                    return {station_name: station_result}

                data[station_name] = station_result

            except Exception as e:
                data[station_name] = {
                    "error": f"Error processing station {station_name}: {str(e)}"}

        conn.close()
    except Exception as e:
        return {"error": f"Database connection or processing failed: {str(e)}"}

    return data
