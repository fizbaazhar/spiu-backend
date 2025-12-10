from typing import Dict, Any, List, Optional, Tuple

from ..db import get_sql_connection
from ..constants import pollutants, stations, conversion_factors
from ..utils.validation import value_violates_threshold, station_needs_conversion
from .aqi_service import calculate_aqi_from_reading
from .alert_service import (
    record_sentinel_alert,
    display_value_for_sentinel,
    record_threshold_alert,
)


def _determine_pollutant_status(value: Any, status: Any, pollutant_name: str, station_code: str) -> Tuple[Any, Optional[str]]:
    """
    Determine the status label for a pollutant based on its value and status column.
    Returns a tuple of (processed_value, status_label).

    Status labels:
    - "Incomplete" for < 75% data (status == 3)
    - "N/A" for -9999.0
    - "N/A" for 985.0
    - "Invalid" for threshold violations
    - None for normal/valid values
    """
    try:
        # Check Status column for <75% threshold (Status == 3)
        if status is not None and int(status) == 3:
            return value, "Incomplete"

        # Check for sentinel values in the data itself
        if value is not None and float(value) == -9999.0:
            mapped = display_value_for_sentinel(value)
            return (mapped if mapped is not None else value), "N/A"

        if value is not None and float(value) == 985.0:
            mapped = display_value_for_sentinel(value)
            return (mapped if mapped is not None else value), "N/A"

        # Check for threshold violations
        if value is not None and value_violates_threshold(pollutant_name, value, station_code):
            return "Invalid", "Invalid"

        # Normal value
        return value, None

    except (ValueError, TypeError):
        return value, None


def _convert_pollutants_in_place(reading: Dict[str, Any], station_code: str) -> None:
    if not station_needs_conversion(station_code):
        return
    for pollutant_name, factor in conversion_factors.items():
        value = reading.get(pollutant_name)
        try:
            if value is not None and value not in ("N/A", "Invalid"):
                reading[pollutant_name] = float(value) * float(factor)
        except (ValueError, TypeError):
            pass


def _converted_reading_for_aqi(reading: Dict[str, Any], station_code: str) -> Dict[str, Any]:
    if not station_needs_conversion(station_code):
        return reading
    conv: Dict[str, Any] = {}
    for pollutant_name, value in reading.items():
        try:
            if value is None or value in ("", "N/A", "Invalid"):
                conv[pollutant_name] = None
            else:
                conv[pollutant_name] = float(value) * float(
                    conversion_factors.get(pollutant_name, 1.0)
                )
        except (ValueError, TypeError):
            conv[pollutant_name] = None
    return conv


def get_historical_data(interval_code: str, limit: int) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    try:
        conn = get_sql_connection()
        cursor = conn.cursor()
        for station_code, station_name in stations.items():
            station_data: List[Dict[str, Any]] = []
            table = f'dbo.S{station_code}T{interval_code}'
            try:
                cursor.execute(
                    f"SELECT TOP {limit} * FROM {table} ORDER BY Date_Time DESC")
                rows = cursor.fetchall()
                if rows:
                    columns = [col[0] for col in cursor.description]
                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        current_dt = row_dict.get("Date_Time")
                        reading: Dict[str, Any] = {
                            "Date_Time": str(current_dt),
                        }

                        for i, gas in enumerate(pollutants, start=1):
                            value_col = f"Value{i}"
                            status_col = f"Status{i}"
                            value = row_dict.get(value_col)
                            status = row_dict.get(status_col)

                            # Determine status and process value
                            processed_value, status_label = _determine_pollutant_status(
                                value, status, gas, station_code
                            )

                            # Record appropriate alerts
                            try:
                                # Check Status column for <75% threshold (Status == 3)
                                if status is not None and int(status) == 3:
                                    record_sentinel_alert(
                                        station_name, gas, 88888.0, current_dt)
                                # Check for sentinel values in the data itself (only -9999.0 and 985.0)
                                elif value is not None and (float(value) == -9999.0 or float(value) == 985.0):
                                    record_sentinel_alert(
                                        station_name, gas, value, current_dt)
                                elif status_label != "Invalid":
                                    # non-sentinel numeric: check thresholds using correct units
                                    value_for_alert = value
                                    try:
                                        if station_needs_conversion(station_code):
                                            value_for_alert = float(value) * float(
                                                conversion_factors.get(
                                                    gas, 1.0)
                                            )
                                    except (ValueError, TypeError):
                                        pass
                                    record_threshold_alert(
                                        station_name, gas, value_for_alert, current_dt)
                            except (ValueError, TypeError):
                                pass

                            reading[gas] = processed_value
                            # Add status field if there's a status to report
                            if status_label is not None:
                                reading[f"Status_{gas}"] = status_label

                        reading['PM25'] = reading.pop('PM2.5', None)
                        # Also rename PM2.5 status field if it exists
                        if 'Status_PM2.5' in reading:
                            reading['Status_PM25'] = reading.pop(
                                'Status_PM2.5')

                        aqi_input = _converted_reading_for_aqi(
                            reading, station_code)
                        aqi, category, dominant = calculate_aqi_from_reading(
                            aqi_input)
                        if aqi is not None:
                            reading["AQI"] = aqi
                            reading["AQI_category"] = category
                            reading["Dominant_Pollutant"] = dominant
                        _convert_pollutants_in_place(reading, station_code)
                        station_data.append(reading)

                    station_data.reverse()
                else:
                    station_data = [{"error": "no data"}]
            except Exception as e:
                station_data = [{"error": str(e)}]
            data[station_name] = station_data
        conn.close()
    except Exception as e:
        return {"error": f"connection failed: {str(e)}"}
    return data


def get_periodic_data(interval_code: str, start_datetime: str, end_datetime: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    try:
        conn = get_sql_connection()
        cursor = conn.cursor()
        for station_code, station_name in stations.items():
            station_data: List[Dict[str, Any]] = []
            table = f'dbo.S{station_code}T{interval_code}'
            try:
                query = f"""
                    SELECT * FROM {table}
                    WHERE Date_Time BETWEEN ? AND ?
                    ORDER BY Date_Time ASC
                """
                # Shift selection window forward by +1 hour so that after
                # labeling as previous hour, data aligns with requested range
                start_param = start_datetime
                end_param = end_datetime
                cursor.execute(query, (start_param, end_param))
                rows = cursor.fetchall()
                if rows:
                    columns = [col[0] for col in cursor.description]
                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        current_dt = row_dict.get("Date_Time")
                        reading: Dict[str, Any] = {
                            "Date_Time": str(current_dt),
                        }

                        for i, gas in enumerate(pollutants, start=1):
                            value_col = f"Value{i}"
                            status_col = f"Status{i}"
                            value = row_dict.get(value_col)
                            status = row_dict.get(status_col)

                            # Determine status and process value
                            processed_value, status_label = _determine_pollutant_status(
                                value, status, gas, station_code
                            )

                            # Record appropriate alerts
                            try:
                                # Check Status column for <75% threshold (Status == 3)
                                if status is not None and int(status) == 3:
                                    record_sentinel_alert(
                                        station_name, gas, 88888.0, current_dt)
                                # Check for sentinel values in the data itself (only -9999.0 and 985.0)
                                elif value is not None and (float(value) == -9999.0 or float(value) == 985.0):
                                    record_sentinel_alert(
                                        station_name, gas, value, current_dt)
                                elif status_label != "Invalid":
                                    value_for_alert = value
                                    try:
                                        if station_needs_conversion(station_code):
                                            value_for_alert = float(value) * float(
                                                conversion_factors.get(
                                                    gas, 1.0)
                                            )
                                    except (ValueError, TypeError):
                                        pass
                                    record_threshold_alert(
                                        station_name, gas, value_for_alert, current_dt)
                            except (ValueError, TypeError):
                                pass

                            reading[gas] = processed_value
                            # Add status field if there's a status to report
                            if status_label is not None:
                                reading[f"Status_{gas}"] = status_label

                        reading['PM25'] = reading.pop('PM2.5', None)
                        # Also rename PM2.5 status field if it exists
                        if 'Status_PM2.5' in reading:
                            reading['Status_PM25'] = reading.pop(
                                'Status_PM2.5')

                        aqi_input = _converted_reading_for_aqi(
                            reading, station_code)
                        aqi, category, dominant = calculate_aqi_from_reading(
                            aqi_input)
                        if aqi is not None:
                            reading["AQI"] = aqi
                            reading["AQI_category"] = category
                            reading["Dominant_Pollutant"] = dominant
                        _convert_pollutants_in_place(reading, station_code)
                        station_data.append(reading)
                else:
                    station_data = [{"error": "no data"}]
            except Exception as e:
                station_data = [{"error": str(e)}]
            data[station_name] = station_data
        conn.close()
    except Exception as e:
        return {"error": f"connection failed: {str(e)}"}
    return data


def get_historical_data_for_station(station_name: str, interval_code: str, limit: int) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    try:
        station_code = None
        for code, name in stations.items():
            if name == station_name:
                station_code = code
                break
        if not station_code:
            return {"error": f"Station '{station_name}' not found"}
        conn = get_sql_connection()
        cursor = conn.cursor()
        station_data: List[Dict[str, Any]] = []
        table = f'dbo.S{station_code}T{interval_code}'
        try:
            cursor.execute(
                f"SELECT TOP {limit} * FROM {table} ORDER BY Date_Time DESC")
            rows = cursor.fetchall()
            if rows:
                columns = [col[0] for col in cursor.description]
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    current_dt = row_dict.get("Date_Time")
                    reading: Dict[str, Any] = {
                        "Date_Time": str(current_dt),
                    }
                    for i, gas in enumerate(pollutants, start=1):
                        value_col = f"Value{i}"
                        status_col = f"Status{i}"
                        value = row_dict.get(value_col)
                        status = row_dict.get(status_col)

                        # Determine status and process value
                        processed_value, status_label = _determine_pollutant_status(
                            value, status, gas, station_code
                        )

                        # Record appropriate alerts
                        try:
                            # Check Status column for <75% threshold (Status == 3)
                            if status is not None and int(status) == 3:
                                record_sentinel_alert(
                                    station_name, gas, 88888.0, current_dt)
                            # Check for sentinel values in the data itself (only -9999.0 and 985.0)
                            elif value is not None and (float(value) == -9999.0 or float(value) == 985.0):
                                record_sentinel_alert(
                                    station_name, gas, value, current_dt)
                            elif status_label != "Invalid":
                                value_for_alert = value
                                try:
                                    if station_needs_conversion(station_code):
                                        value_for_alert = float(value) * float(
                                            conversion_factors.get(gas, 1.0)
                                        )
                                except (ValueError, TypeError):
                                    pass
                                record_threshold_alert(
                                    station_name, gas, value_for_alert, current_dt)
                        except (ValueError, TypeError):
                            pass

                        reading[gas] = processed_value
                        # Add status field if there's a status to report
                        if status_label is not None:
                            reading[f"Status_{gas}"] = status_label

                    # finalize per-row reading
                    reading["PM25"] = reading.pop("PM2.5", None)
                    # Also rename PM2.5 status field if it exists
                    if 'Status_PM2.5' in reading:
                        reading['Status_PM25'] = reading.pop('Status_PM2.5')

                    aqi_input = _converted_reading_for_aqi(
                        reading, station_code)
                    aqi, category, dominant = calculate_aqi_from_reading(
                        aqi_input)
                    if aqi is not None:
                        reading["AQI"] = aqi
                        reading["AQI_category"] = category
                        reading["Dominant_Pollutant"] = dominant
                    _convert_pollutants_in_place(reading, station_code)
                    station_data.append(reading)
                # reverse after processing all rows
                station_data.reverse()
            else:
                station_data = [{"error": "no data"}]
        except Exception as e:
            station_data = [{"error": str(e)}]
        data[station_name] = station_data
        conn.close()
    except Exception as e:
        return {"error": f"connection failed: {str(e)}"}
    return data


def get_periodic_data_for_station(station_name: str, interval_code: str, start_datetime: str, end_datetime: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    try:
        station_code = None
        for code, name in stations.items():
            if name == station_name:
                station_code = code
                break
        if not station_code:
            return {"error": f"Station '{station_name}' not found"}
        conn = get_sql_connection()
        cursor = conn.cursor()
        station_data: List[Dict[str, Any]] = []
        table = f'dbo.S{station_code}T{interval_code}'
        try:
            query = f"""
                SELECT * FROM {table}
                WHERE Date_Time BETWEEN ? AND ?
                ORDER BY Date_Time ASC
            """
            start_param = start_datetime
            end_param = end_datetime
            cursor.execute(query, (start_param, end_param))
            rows = cursor.fetchall()
            if rows:
                columns = [col[0] for col in cursor.description]
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    current_dt = row_dict.get("Date_Time")
                    reading: Dict[str, Any] = {
                        "Date_Time": str(current_dt),
                    }
                    for i, gas in enumerate(pollutants, start=1):
                        value_col = f"Value{i}"
                        status_col = f"Status{i}"
                        value = row_dict.get(value_col)
                        status = row_dict.get(status_col)

                        # Determine status and process value
                        processed_value, status_label = _determine_pollutant_status(
                            value, status, gas, station_code
                        )

                        # Record appropriate alerts
                        try:
                            # Check Status column for <75% threshold (Status == 3)
                            if status is not None and int(status) == 3:
                                record_sentinel_alert(
                                    station_name, gas, 88888.0, current_dt)
                            # Check for sentinel values in the data itself (only -9999.0 and 985.0)
                            elif value is not None and (float(value) == -9999.0 or float(value) == 985.0):
                                record_sentinel_alert(
                                    station_name, gas, value, current_dt)
                            elif status_label != "Invalid":
                                value_for_alert = value
                                try:
                                    if station_needs_conversion(station_code):
                                        value_for_alert = float(value) * float(
                                            conversion_factors.get(gas, 1.0)
                                        )
                                except (ValueError, TypeError):
                                    pass
                                record_threshold_alert(
                                    station_name, gas, value_for_alert, current_dt)
                        except (ValueError, TypeError):
                            pass

                        reading[gas] = processed_value
                        # Add status field if there's a status to report
                        if status_label is not None:
                            reading[f"Status_{gas}"] = status_label

                    # finalize per-row reading
                    reading["PM25"] = reading.pop("PM2.5", None)
                    # Also rename PM2.5 status field if it exists
                    if 'Status_PM2.5' in reading:
                        reading['Status_PM25'] = reading.pop('Status_PM2.5')

                    aqi_input = _converted_reading_for_aqi(
                        reading, station_code)
                    aqi, category, dominant = calculate_aqi_from_reading(
                        aqi_input)
                    if aqi is not None:
                        reading["AQI"] = aqi
                        reading["AQI_category"] = category
                        reading["Dominant_Pollutant"] = dominant
                    _convert_pollutants_in_place(reading, station_code)
                    station_data.append(reading)
            else:
                station_data = [{"error": "no data"}]
        except Exception as e:
            station_data = [{"error": str(e)}]
        data[station_name] = station_data
        conn.close()
    except Exception as e:
        return {"error": f"connection failed: {str(e)}"}
    return data
