from flask import Blueprint, jsonify, request
from datetime import datetime
from ..services.data_service import get_historical_data, get_periodic_data
from ..services.aqi_service import get_latest_aqi_data
from ..constants import intervals, station_coordinates
from ..db import get_sql_connection
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


general_bp = Blueprint('general', __name__)


@general_bp.route('/daily', methods=['GET'])
def daily_data():
    tz = ZoneInfo("Asia/Karachi")
    now_local = datetime.now(tz)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_str = start_local.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    end_str = now_local.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    return jsonify(get_periodic_data("60", start_str, end_str))


@general_bp.route('/monthly', methods=['GET'])
def monthly_data():
    tz = ZoneInfo("Asia/Karachi")
    now_local = datetime.now(tz)
    start_local = now_local.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)
    start_str = start_local.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    end_str = now_local.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    return jsonify(get_periodic_data("1440", start_str, end_str))


@general_bp.route('/aqi', methods=['GET'])
def get_aqi():
    try:
        return jsonify(get_latest_aqi_data())
    except Exception as e:
        return jsonify({"error": f"AQI calculation failed: {str(e)}"}), 500


@general_bp.route('/latest_hour', methods=['GET'])
def latest_hour():
    try:
        hourly_data = get_historical_data("60", 1)
        result = {}
        for station_name, readings in hourly_data.items():
            if isinstance(readings, list) and len(readings) > 0 and "error" not in readings[0]:
                latest_reading = readings[0]
                station_result = {
                    "Date_Time": latest_reading.get("Date_Time"),
                    "O3": latest_reading.get("O3"),
                    "CO": latest_reading.get("CO"),
                    "SO2": latest_reading.get("SO2"),
                    "NO": latest_reading.get("NO"),
                    "NO2": latest_reading.get("NO2"),
                    "NOX": latest_reading.get("NOX"),
                    "PM10": latest_reading.get("PM10"),
                    "PM25": latest_reading.get("PM25"),
                    "WS": latest_reading.get("WS"),
                    "WD": latest_reading.get("WD"),
                    "Temp": latest_reading.get("Temp"),
                    "RH": latest_reading.get("RH"),
                    "BP": latest_reading.get("BP"),
                    "Rain": latest_reading.get("Rain"),
                    "SR": latest_reading.get("SR"),
                    "AQI": latest_reading.get("AQI"),
                    "AQI_category": latest_reading.get("AQI_category"),
                    "Dominant_Pollutant": latest_reading.get("Dominant_Pollutant"),
                }
                result[station_name] = station_result
            else:
                result[station_name] = {"error": "no data"}
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Hourly data retrieval failed: {str(e)}"}), 500


@general_bp.route('/alerts/recent', methods=['GET'])
def recent_alerts():
    try:
        conn = get_sql_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 100 Date_Time, Alert FROM dbo.alerts ORDER BY Date_Time DESC")
        rows = cursor.fetchall()
        result = [
            {"Date_Time": str(r[0]), "Alert": r[1]} for r in rows
        ]
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch alerts: {str(e)}"}), 500


@general_bp.route('/alerts/last_two_days', methods=['GET'])
def alerts_last_two_days():
    try:
        tz = ZoneInfo("Asia/Karachi")
        now_local = datetime.now(tz)
        start_local = (now_local.replace(hour=0, minute=0,
                       second=0, microsecond=0) - timedelta(days=1))
        # Pass naive datetimes assuming DB stores local timestamps
        now_param = now_local.replace(tzinfo=None)
        start_param = start_local.replace(tzinfo=None)
        conn = get_sql_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Date_Time, Alert FROM dbo.alerts WHERE Date_Time BETWEEN ? AND ? ORDER BY Date_Time DESC",
            (start_param, now_param),
        )
        rows = cursor.fetchall()
        result = [{"Date_Time": str(r[0]), "Alert": r[1]} for r in rows]
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch alerts: {str(e)}"}), 500


@general_bp.route('/alerts/range', methods=['GET'])
def alerts_range():
    try:
        start_datetime = request.args.get('start_datetime')
        end_datetime = request.args.get('end_datetime')
        if not start_datetime or not end_datetime:
            return jsonify({"error": "start_datetime and end_datetime are required"}), 400
        try:
            start_obj = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
            end_obj = datetime.strptime(end_datetime, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({"error": "Invalid datetime format. Use 'YYYY-MM-DD HH:MM:SS'"}), 400

        conn = get_sql_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Date_Time, Alert FROM dbo.alerts WHERE Date_Time BETWEEN ? AND ? ORDER BY Date_Time DESC",
            (start_obj, end_obj),
        )
        rows = cursor.fetchall()
        result = [{"Date_Time": str(r[0]), "Alert": r[1]} for r in rows]
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch alerts: {str(e)}"}), 500


@general_bp.route('/periodic', methods=['GET'])
def periodic_data():
    try:
        start_datetime = request.args.get('start_datetime')
        end_datetime = request.args.get('end_datetime')
        interval = request.args.get('interval', '60')

        if not start_datetime or not end_datetime:
            return jsonify({"error": "start_datetime and end_datetime are required"}), 400

        if interval not in intervals:
            return jsonify({"error": "Invalid interval. Must be either '05', '15', '30', '60' or '1440'"}), 400

        try:
            datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
            datetime.strptime(end_datetime, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({"error": "Invalid datetime format. Use 'YYYY-MM-DD HH:MM:SS'"}), 400

        return jsonify(get_periodic_data(interval, start_datetime, end_datetime))
    except Exception as e:
        return jsonify({"error": f"Periodic data retrieval failed: {str(e)}"}), 500


@general_bp.route('/coordinates', methods=['GET'])
def get_coordinates():
    """
    Returns all station coordinates with their names.
    Response format:
    {
        "station_name": {"lat": latitude, "lng": longitude},
        ...
    }
    """
    try:
        return jsonify(station_coordinates)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch coordinates: {str(e)}"}), 500
