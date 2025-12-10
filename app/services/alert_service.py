from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import smtplib
from email.message import EmailMessage
from smtplib import SMTP_SSL
import time

from ..db import get_sql_connection
from .. import socketio
from ..constants import stations, threshold_limits, conversion_factors
from ..constants import pollutants as all_pollutants
from ..config import Config


# In-memory cache of emailed alerts to prevent duplicates
# Format: {alert_text+timestamp: expiry_timestamp}
_EMAILED_ALERTS_CACHE = {}
# Cache expiry in seconds (24 hours)
_CACHE_EXPIRY = 86400


SENTINEL_DISPLAY_MAP = {
    -9999.0: "analyzer comm. error",
    985.0: "analyzer error",
    88888.0: "< sample",
}


def insert_alert(alert_text: str, when: Optional[datetime] = None) -> None:
    dt = when or datetime.now()
    try:
        conn = get_sql_connection()
        cursor = conn.cursor()
        # de-duplicate: skip if same alert exists for this data timestamp (+/- 1 minute tolerance)
        # This prevents recreating alerts for old data points that have already been alerted on
        try:
            cursor.execute(
                "SELECT TOP 1 1 FROM dbo.alerts WHERE Alert = ? AND Date_Time BETWEEN DATEADD(minute, -1, ?) AND DATEADD(minute, 1, ?)",
                (alert_text, dt, dt),
            )
            if cursor.fetchone():
                conn.close()
                return
        except Exception:
            pass
        cursor.execute(
            "INSERT INTO dbo.alerts (Date_Time, Alert) VALUES (?, ?)",
            (dt, alert_text),
        )
        conn.commit()
        conn.close()
        try:
            socketio.emit("alert", {"Date_Time": str(dt), "Alert": alert_text})
        except Exception:
            pass
        # Send email notification (best-effort, with deduplication)
        try:
            # Check if we've already emailed this alert
            cache_key = f"{alert_text}:{dt.isoformat()}"
            now = time.time()

            # Clean expired entries from cache
            expired_keys = [
                k for k, v in _EMAILED_ALERTS_CACHE.items() if v < now]
            for k in expired_keys:
                _EMAILED_ALERTS_CACHE.pop(k, None)

            # Only send if not in cache
            if cache_key not in _EMAILED_ALERTS_CACHE:
                send_email_alert(
                    subject=f"Alert: {alert_text}",
                    body=f"Timestamp: {dt}\n\n{alert_text}",
                )
                # Add to cache with expiry
                _EMAILED_ALERTS_CACHE[cache_key] = now + _CACHE_EXPIRY
        except Exception:
            pass
    except Exception:
        # Best-effort; avoid breaking data flow if alerts table write fails
        pass


def display_value_for_sentinel(value: Any) -> Optional[str]:
    try:
        f = float(value)
        return SENTINEL_DISPLAY_MAP.get(f)
    except (ValueError, TypeError):
        return None


def record_sentinel_alert(station_name: str, pollutant: str, value: Any, when: Optional[datetime]) -> None:
    msg: Optional[str] = None
    try:
        f = float(value)
        if f == -9999.0:
            msg = f"E04.1: No Data from Analyzer: {pollutant} for {station_name}"
        elif f == 985.0:
            msg = f"E04.2: No Data from Dust Analyzer: {pollutant} for {station_name}"
        elif f == 88888.0:
            msg = f"E03: Incomplete Data (< 75%) for {pollutant} at {station_name}"
    except (ValueError, TypeError):
        msg = None

    if msg:
        insert_alert(msg, when)


def record_threshold_alert(station_name: str, pollutant: str, value: Any, data_timestamp: Optional[datetime] = None) -> None:
    limits = threshold_limits.get(pollutant)
    if not limits:
        return
    try:
        f = float(value)
    except (ValueError, TypeError):
        return
    max_limit = limits.get("max")
    min_limit = limits.get("min")
    if max_limit is not None and f > max_limit:
        insert_alert(
            f"E06: {pollutant} Range Beyond Threshold ({max_limit}) for {station_name}", data_timestamp)
    if min_limit is not None and f < min_limit:
        insert_alert(
            f"E05: {pollutant} Range Below Threshold ({min_limit}) for {station_name}", data_timestamp)


def check_no_hourly_data(now: Optional[datetime] = None) -> None:
    tz = ZoneInfo("Asia/Karachi")
    current_local = now or datetime.now(tz)
    # Grace window to allow ingestion to complete
    if current_local.minute < 10:
        return
    expected_start_local = current_local.replace(
        minute=0, second=0, microsecond=0)
    expected_end_local = expected_start_local + \
        timedelta(hours=1) - timedelta(seconds=1)

    try:
        conn = get_sql_connection()
        cursor = conn.cursor()
        for station_code, station_name in stations.items():
            table = f"dbo.S{station_code}T60"
            try:
                # Query for any row in the expected local hour window (pass naive datetimes)
                cursor.execute(
                    f"SELECT TOP 1 1 FROM {table} WHERE Date_Time BETWEEN ? AND ?",
                    (expected_start_local.replace(tzinfo=None),
                     expected_end_local.replace(tzinfo=None)),
                )
                hit = cursor.fetchone()
                if not hit:
                    # Generate alert for missing hourly data
                    alert_text = f"E04.3: No Data from Station {station_name} for: {expected_start_local}"
                    insert_alert(alert_text, expected_start_local)
            except Exception as e:
                # Log the error and skip station on error
                print(
                    f"Error checking hourly data for station {station_code}: {str(e)}")
                continue
        conn.close()
    except Exception as e:
        # Log the database connection error
        print(f"Database connection error in check_no_hourly_data: {str(e)}")


def run_sentinel_threshold_checks() -> None:
    """Scan latest 60-min data and create alerts for sentinels and thresholds."""
    try:
        conn = get_sql_connection()
        cursor = conn.cursor()

        # Map pollutant name to its ValueN and StatusN index based on position in constants.pollutants
        value_indices = {p: (all_pollutants.index("PM2.5") + 1 if p == "PM25" else all_pollutants.index(p) + 1)
                         for p in conversion_factors.keys()}

        for station_code, station_name in stations.items():
            table = f"dbo.S{station_code}T60"
            # Stations 001-009 and 031-038 need conversion to AQI units; 010+ already in correct units

            def _needs_conv(code: str) -> bool:
                conversion_station_codes = {
                    "001", "002", "003", "004", "005", "006", "007", "008", "009",
                    "031", "032", "033", "034", "035", "036", "037", "038"
                }
                try:
                    code_int = int(code)
                    return 1 <= code_int <= 9 or 31 <= code_int <= 38
                except (TypeError, ValueError):
                    return code in conversion_station_codes
            try:
                # Select both Value and Status columns for each pollutant
                select_cols = []
                for p in conversion_factors.keys():
                    idx = value_indices[p]
                    select_cols.append(f"Value{idx} AS {p}")
                    select_cols.append(f"Status{idx} AS {p}_Status")

                cursor.execute(
                    f"SELECT TOP 1 Date_Time, {', '.join(select_cols)} FROM {table} ORDER BY Date_Time DESC"
                )
                row = cursor.fetchone()
                if not row:
                    continue
                columns = [col[0] for col in cursor.description]
                row_dict = dict(zip(columns, row))
                latest_dt = row_dict.get("Date_Time")

                # sentinel alerts - check both value and status
                for p in conversion_factors.keys():
                    v = row_dict.get(p)
                    status = row_dict.get(f"{p}_Status")

                    try:
                        # Check Status column for <75% threshold (Status == 3)
                        if status is not None and int(status) == 3:
                            record_sentinel_alert(
                                station_name, p, 88888.0, latest_dt)
                        # Check value for sentinel conditions (only -9999.0 and 985.0)
                        elif v is not None and (float(v) == -9999.0 or float(v) == 985.0):
                            record_sentinel_alert(
                                station_name, p, v, latest_dt)
                    except (ValueError, TypeError):
                        continue

                # threshold alerts: use converted values only for stations needing conversion
                for p, factor in conversion_factors.items():
                    v = row_dict.get(p)
                    status = row_dict.get(f"{p}_Status")
                    try:
                        if v is None:
                            continue
                        # Skip threshold checks if Status == 3 (insufficient data)
                        if status is not None and int(status) == 3:
                            continue
                        f = float(v)
                        # Skip threshold checks for sentinel values (only -9999.0 and 985.0)
                        if f == -9999.0 or f == 985.0:
                            continue
                        value_for_check = f * \
                            float(factor) if _needs_conv(station_code) else f
                        record_threshold_alert(
                            station_name, p, value_for_check, latest_dt)
                    except (ValueError, TypeError):
                        continue

            except Exception:
                continue
        conn.close()
    except Exception:
        pass


def check_spike_abrupt_changes() -> None:
    """Check for spike/abrupt changes (>300% difference between consecutive readings)."""
    try:
        conn = get_sql_connection()
        cursor = conn.cursor()

        # Map pollutant name to its ValueN index
        value_indices = {p: (all_pollutants.index("PM2.5") + 1 if p == "PM25" else all_pollutants.index(p) + 1)
                         for p in conversion_factors.keys()}

        for station_code, station_name in stations.items():
            table = f"dbo.S{station_code}T60"

            try:
                # Get the last 2 readings
                select_cols = [
                    f"Value{value_indices[p]} AS {p}" for p in conversion_factors.keys()]
                cursor.execute(
                    f"SELECT TOP 2 Date_Time, {', '.join(select_cols)} FROM {table} ORDER BY Date_Time DESC"
                )
                rows = cursor.fetchall()

                if len(rows) < 2:
                    continue

                columns = [col[0] for col in cursor.description]
                latest_row = dict(zip(columns, rows[0]))
                previous_row = dict(zip(columns, rows[1]))
                latest_dt = latest_row.get("Date_Time")

                # Check each pollutant for spike
                for p in conversion_factors.keys():
                    latest_value = latest_row.get(p)
                    previous_value = previous_row.get(p)

                    try:
                        if latest_value is None or previous_value is None:
                            continue

                        latest_f = float(latest_value)
                        previous_f = float(previous_value)

                        # Skip sentinel values
                        if latest_f in (-9999.0, 985.0) or previous_f in (-9999.0, 985.0):
                            continue

                        # Skip if previous value is zero or very close to zero
                        if abs(previous_f) < 0.01:
                            continue

                        # Calculate percentage change
                        percent_change = abs(
                            (latest_f - previous_f) / previous_f) * 100

                        if percent_change > 300:
                            alert_text = f"E07: Spike/Abrupt Changes for {p} at {station_name} at {latest_dt}"
                            insert_alert(alert_text, latest_dt)

                    except (ValueError, TypeError, ZeroDivisionError):
                        continue

            except Exception:
                continue

        conn.close()
    except Exception:
        pass


def check_choking_sticking() -> None:
    """Detect if same readings persist for 2 or more consecutive hours."""
    try:
        conn = get_sql_connection()
        cursor = conn.cursor()

        # Map pollutant name to its ValueN index
        value_indices = {p: (all_pollutants.index("PM2.5") + 1 if p == "PM25" else all_pollutants.index(p) + 1)
                         for p in conversion_factors.keys()}

        for station_code, station_name in stations.items():
            table = f"dbo.S{station_code}T60"

            try:
                # Get the last 3 readings (to check if 2+ consecutive are the same)
                select_cols = [
                    f"Value{value_indices[p]} AS {p}" for p in conversion_factors.keys()]
                cursor.execute(
                    f"SELECT TOP 3 Date_Time, {', '.join(select_cols)} FROM {table} ORDER BY Date_Time DESC"
                )
                rows = cursor.fetchall()

                if len(rows) < 2:
                    continue

                columns = [col[0] for col in cursor.description]
                readings = [dict(zip(columns, row)) for row in rows]
                latest_dt = readings[0].get("Date_Time")
                oldest_dt = readings[-1].get("Date_Time")

                # Check each pollutant for choking/sticking
                for p in conversion_factors.keys():
                    values = []
                    for reading in readings:
                        value = reading.get(p)
                        if value is not None:
                            try:
                                f = float(value)
                                # Skip sentinel values
                                if f not in (-9999.0, 985.0):
                                    values.append(f)
                            except (ValueError, TypeError):
                                continue

                    # Need at least 2 valid values
                    if len(values) < 2:
                        continue

                    # Check if all values are identical (with small tolerance for floating point)
                    first_value = values[0]
                    all_same = all(abs(v - first_value) < 0.01 for v in values)

                    if all_same and len(values) >= 2:
                        # Format time range
                        time_range = f"{oldest_dt} to {latest_dt}"
                        alert_text = f"E08: Choking/Sticking for {p} at {station_name} for {time_range}"
                        insert_alert(alert_text, latest_dt)

            except Exception:
                continue

        conn.close()
    except Exception:
        pass


def send_email_alert(subject: str, body: str) -> None:
    """Send an email using SMTP settings from Config. Best-effort and non-blocking.

    - Recipients are read from Config.ALERT_EMAIL_TO (comma-separated)
    - From address is Config.ALERT_EMAIL_FROM
    - Uses STARTTLS when Config.SMTP_USE_TLS is true
    """
    try:
        if not Config.SMTP_HOST or not Config.ALERT_EMAIL_TO or not Config.ALERT_EMAIL_FROM:
            return
        recipients = [addr.strip()
                      for addr in Config.ALERT_EMAIL_TO.split(',') if addr.strip()]
        if not recipients:
            return

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = Config.ALERT_EMAIL_FROM
        msg['To'] = ', '.join(recipients)
        msg.set_content(body)

        # If TLS is enabled (STARTTLS), use SMTP; if disabled and port is 465, use SSL
        if Config.SMTP_USE_TLS and Config.SMTP_PORT != 465:
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
                try:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                except Exception:
                    pass
                if Config.SMTP_USERNAME:
                    server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
                if Config.SMTP_USERNAME:
                    server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
                server.send_message(msg)
    except Exception:
        # Swallow to avoid impacting the main flow
        pass
