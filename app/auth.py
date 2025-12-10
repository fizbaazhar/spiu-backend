import os
from functools import wraps
from typing import Callable, Optional

from flask import Blueprint, current_app, jsonify, request


def _get_configured_api_key() -> Optional[str]:
    # Prefer app config, fall back to environment
    configured = None
    try:
        configured = current_app.config.get(
            'API_KEY')  # type: ignore[attr-defined]
    except Exception:
        configured = None
    if not configured:
        configured = os.getenv('API_KEY')
    return configured


def _extract_provided_key() -> Optional[str]:
    # Header takes precedence, then query param
    header_key = request.headers.get(
        'X-API-Key') or request.headers.get('X-Api-Key')
    if header_key:
        return header_key.strip()
    query_key = request.args.get('api_key')
    if query_key:
        return query_key.strip()
    return None


def require_api_key(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        configured = _get_configured_api_key()
        provided = _extract_provided_key()

        if not configured:
            return jsonify({"error": "Server API key not configured"}), 500

        if not provided or provided != configured:
            return jsonify({"error": "Unauthorized: invalid API key"}), 401

        return fn(*args, **kwargs)

    return wrapper


def bind_blueprint_api_key_guard(bp: Blueprint) -> None:
    @bp.before_request
    def _guard():  # type: ignore[func-returns-value]
        # Allow CORS preflight to pass without auth
        if request.method == 'OPTIONS':
            return None
        configured = _get_configured_api_key()
        provided = _extract_provided_key()
        if not configured:
            return jsonify({"error": "Server API key not configured"}), 500
        if not provided or provided != configured:
            return jsonify({"error": "Unauthorized: invalid API key"}), 401
