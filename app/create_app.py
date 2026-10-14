"""
SpamGuard AI — Flask Application Factory

Creates and configures the Flask application with:
- Security headers (Flask-Talisman)
- Rate limiting (Flask-Limiter)
- ProxyFix for Render's reverse proxy
- Model loading at startup
"""

import logging
import os
import sys

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app(testing: bool = False) -> Flask:
    """Create and configure the Flask application."""

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    # --- Configuration ---
    app.config["TESTING"] = testing
    app.config["MAX_CONTENT_LENGTH"] = 65536  # 64 KB

    # --- Logging ---
    # Structured logging: timestamp, route, status, latency, request_id
    # NEVER log subject/body content
    log_format = "%(asctime)s %(levelname)s %(name)s %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # --- ProxyFix ---
    # Render uses 1 reverse proxy hop
    # This ensures request.remote_addr is the client IP, not the proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # --- Security Headers (Flask-Talisman) ---
    is_production = (
        os.environ.get("FLASK_ENV") == "production"
        or os.environ.get("RENDER") is not None
        or os.environ.get("FORCE_HTTPS", "").lower() in ("true", "1")
    )

    csp = {
        "default-src": "'self'",
        "script-src": "'self'",
        "style-src": "'self'",
        "img-src": "'self' data:",
        "font-src": "'self'",
        "frame-ancestors": "'none'",
        "base-uri": "'self'",
        "form-action": "'self'",
    }

    Talisman(
        app,
        content_security_policy=csp,
        force_https=is_production,
        strict_transport_security=is_production,
        session_cookie_secure=is_production,
        content_security_policy_nonce_in=None,  # No inline scripts
    )

    # --- Rate Limiting ---
    rate_limit_per_minute = os.environ.get("RATE_LIMIT_PER_MINUTE", "20")
    rate_limit_per_day = os.environ.get("RATE_LIMIT_PER_DAY", "200")

    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=[],  # No default limits on all routes
        storage_uri="memory://",  # In-memory (single worker)
    )

    # --- Register Blueprints ---
    from app.routes import api_bp, pages_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(pages_bp)

    # Apply rate limit specifically to /api/predict
    limiter.limit(f"{rate_limit_per_minute}/minute;{rate_limit_per_day}/day")(app.view_functions["api.predict"])

    # --- Load Model ---
    if not testing:
        try:
            from app.services import get_model_service

            service = get_model_service()
            models_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "models",
            )
            version = os.environ.get("MODEL_VERSION", "v1")
            service.load(models_dir, version)
        except Exception as e:
            logging.getLogger(__name__).error("Model failed to load at startup: %s. /api/predict will return 503.", e)

    # --- Error Handlers ---
    @app.errorhandler(404)
    def not_found(e):
        from flask import jsonify
        from flask import request as req

        if req.path.startswith("/api/"):
            return jsonify({"error": "Not found", "status_code": 404}), 404
        return (
            app.send_static_file("404.html")
            if os.path.exists(os.path.join(app.static_folder, "404.html"))
            else ("Not Found", 404)
        )

    @app.errorhandler(429)
    def rate_limited(e):
        from flask import jsonify

        return jsonify(
            {
                "error": "Rate limit exceeded. Please try again later.",
                "status_code": 429,
            }
        ), 429

    @app.errorhandler(413)
    def request_too_large(e):
        from flask import jsonify

        return jsonify(
            {
                "error": "Request body too large. Maximum 64 KB.",
                "status_code": 413,
            }
        ), 413

    return app
