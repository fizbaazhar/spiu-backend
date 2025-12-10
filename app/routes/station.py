from flask import Blueprint, jsonify, request
from datetime import datetime
from ..services.data_service import (
    get_periodic_data_for_station,
)
from ..services.aqi_service import get_latest_aqi_data
from ..constants import intervals
from zoneinfo import ZoneInfo


station_bp = Blueprint('station', __name__)


@station_bp.route('/daily/<station_name>', methods=['GET'])
def daily_data_for_station(station_name: str):
    tz = ZoneInfo("Asia/Karachi")
    now_local = datetime.now(tz)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_str = start_local.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    end_str = now_local.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    return jsonify(get_periodic_data_for_station(station_name, "60", start_str, end_str))


@station_bp.route('/monthly/<station_name>', methods=['GET'])
def monthly_data_for_station(station_name: str):
    tz = ZoneInfo("Asia/Karachi")
    now_local = datetime.now(tz)
    start_local = now_local.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)
    start_str = start_local.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    end_str = now_local.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    return jsonify(get_periodic_data_for_station(station_name, "1440", start_str, end_str))


@station_bp.route('/periodic/<station_name>', methods=['GET'])
def periodic_data_for_station_route(station_name: str):
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
        return jsonify(get_periodic_data_for_station(station_name, interval, start_datetime, end_datetime))
    except Exception as e:
        return jsonify({"error": f"Periodic data retrieval failed: {str(e)}"}), 500


@station_bp.route('/aqi/<station_name>', methods=['GET'])
def aqi_for_station(station_name: str):
    try:
        aqi_data = get_latest_aqi_data(station_name)
        if "error" in aqi_data:
            return jsonify(aqi_data), 404
        return jsonify(aqi_data)
    except Exception as e:
        return jsonify({"error": f"AQI calculation failed: {str(e)}"}), 500
