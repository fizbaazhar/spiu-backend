from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from datetime import datetime, timedelta
import os

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
except Exception:
    BackgroundScheduler = None


socketio = SocketIO(cors_allowed_origins="*")
_scheduler_started = False


def create_app() -> Flask:
    # Load .env file if python-dotenv is available
    # This will search for .env in current directory and parent directories
    if load_dotenv is not None:
        try:
            load_dotenv()  # Automatically finds .env file
            print("Loaded .env file successfully")
        except Exception as e:
            print(f"Warning: Could not load .env file: {e}")

    app = Flask(__name__)
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Requested-With"],
        expose_headers=["Content-Type"],
        supports_credentials=False,
    )
    socketio.init_app(app, async_mode="eventlet")

    # Register blueprints
    from .routes.general import general_bp
    from .routes.station import station_bp
    from .auth import bind_blueprint_api_key_guard

    # Configure API key from env if present
    api_key = os.getenv('API_KEY')
    app.config['API_KEY'] = api_key

    # Warn if API key is not configured
    if not api_key:
        print("WARNING: API_KEY environment variable is not set! API authentication will fail.")
        print("Please set API_KEY in your .env file or as an environment variable.")
    else:
        print(f"API_KEY loaded successfully (first 8 chars): {api_key[:8]}...")

    # Attach API key guard to blueprints
    bind_blueprint_api_key_guard(general_bp)
    bind_blueprint_api_key_guard(station_bp)

    app.register_blueprint(general_bp)
    app.register_blueprint(station_bp)

    # Scheduling for alerts (guarded to avoid duplicate starts)
    global _scheduler_started
    if BackgroundScheduler is not None and not _scheduler_started:
        from .services.alert_service import (
            check_no_hourly_data,
            run_sentinel_threshold_checks,
            check_spike_abrupt_changes,
            check_choking_sticking
        )
        scheduler = BackgroundScheduler(daemon=True, timezone="Asia/Karachi")

        # Run missing-hour check after grace window (minute 10)
        # This ensures it runs every hour at 10 minutes past the hour
        scheduler.add_job(
            check_no_hourly_data,
            CronTrigger(minute=10),
            id='hourly_data_check',
            name='Check for missing hourly data',
            misfire_grace_time=300  # Allow 5 minutes of delay if scheduler is busy
        )

        # Sentinel/threshold checks can run earlier
        scheduler.add_job(
            run_sentinel_threshold_checks,
            CronTrigger(minute=5),
            id='sentinel_check',
            name='Check for sentinel values and thresholds',
            misfire_grace_time=300  # Allow 5 minutes of delay if scheduler is busy
        )

        # Check for spike/abrupt changes (>300% change)
        scheduler.add_job(
            check_spike_abrupt_changes,
            CronTrigger(minute=7),
            id='spike_check',
            name='Check for spike/abrupt changes',
            misfire_grace_time=300
        )

        # Check for choking/sticking (same value for 2+ hours)
        scheduler.add_job(
            check_choking_sticking,
            CronTrigger(minute=12),
            id='choking_check',
            name='Check for choking/sticking values',
            misfire_grace_time=300
        )

        scheduler.start()
        _scheduler_started = True

    return app
