"""
SpamGuard AI — Flask Routes

API endpoints:
  GET  /api/health   - Readiness check + model_loaded boolean
  POST /api/predict   - Spam analysis
  GET  /api/model-info - Model version, metrics, limitations

Pages:
  GET / - Landing page
  GET /analyze - Analyzer page
  GET /how-it-works - How It Works
  GET /about - About
  GET /privacy - Privacy Policy
  GET /terms - Terms of Service
  GET /feedback - Feedback
"""

import logging
import time
import uuid

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
)

from app.services import get_model_service
from app.signals import analyze_signals

logger = logging.getLogger(__name__)

# Blueprints
api_bp = Blueprint("api", __name__, url_prefix="/api")
pages_bp = Blueprint("pages", __name__)

# Disclaimer text
DISCLAIMER = (
    "This analysis is provided by an automated system for informational purposes only. "
    "It does not guarantee an email is safe or malicious. Always exercise caution "
    "with suspicious emails. Do not click links, download attachments, or share "
    "personal information from emails you do not trust."
)


def _request_id() -> str:
    """Generate a unique request ID for logging."""
    return str(uuid.uuid4())[:8]


def _safe_json_error(message: str, status_code: int, request_id: str = ""):
    """Return a structured JSON error. Never expose tracebacks or paths."""
    return jsonify(
        {
            "error": message,
            "status_code": status_code,
            "request_id": request_id,
        }
    ), status_code


# --- API Routes ---


@api_bp.route("/health", methods=["GET"])
def health():
    """Readiness check."""
    rid = _request_id()
    service = get_model_service()
    start = time.monotonic()
    result = {
        "status": "ok",
        "model_loaded": service.loaded,
    }
    latency = time.monotonic() - start
    logger.info("route=/api/health status=200 latency=%.4f request_id=%s", latency, rid)
    return jsonify(result), 200


@api_bp.route("/predict", methods=["POST"])
def predict():
    """
    Analyze an email for spam signals.

    Expects JSON: {"subject": "...", "body": "..."}
    - body is required, non-empty, max 20,000 chars
    - subject is optional, max 300 chars
    - Request body max 64 KB
    """
    rid = _request_id()
    start = time.monotonic()

    # Check model is loaded
    service = get_model_service()
    if not service.loaded:
        logger.info("route=/api/predict status=503 latency=%.4f request_id=%s", time.monotonic() - start, rid)
        return _safe_json_error("Model is not available. Please try again later.", 503, rid)

    # Check content type
    if not request.is_json:
        logger.info("route=/api/predict status=415 latency=%.4f request_id=%s", time.monotonic() - start, rid)
        return _safe_json_error("Content-Type must be application/json.", 415, rid)

    # Check request size (64 KB)
    content_length = request.content_length or 0
    if content_length > 65536:
        logger.info("route=/api/predict status=413 latency=%.4f request_id=%s", time.monotonic() - start, rid)
        return _safe_json_error("Request body too large. Maximum 64 KB.", 413, rid)

    # Parse JSON
    try:
        data = request.get_json(force=False, silent=False)
    except Exception:
        logger.info("route=/api/predict status=400 latency=%.4f request_id=%s", time.monotonic() - start, rid)
        return _safe_json_error("Invalid JSON in request body.", 400, rid)

    if data is None or not isinstance(data, dict):
        logger.info("route=/api/predict status=400 latency=%.4f request_id=%s", time.monotonic() - start, rid)
        return _safe_json_error("Request body must be a JSON object.", 400, rid)

    # Validate fields
    subject = data.get("subject", "")
    body = data.get("body", "")

    # Type checks
    if not isinstance(subject, str):
        logger.info("route=/api/predict status=422 latency=%.4f request_id=%s", time.monotonic() - start, rid)
        return _safe_json_error("Field 'subject' must be a string.", 422, rid)

    if not isinstance(body, str):
        logger.info("route=/api/predict status=422 latency=%.4f request_id=%s", time.monotonic() - start, rid)
        return _safe_json_error("Field 'body' must be a string.", 422, rid)

    # Body required and non-empty
    body_stripped = body.strip()
    if not body_stripped:
        logger.info("route=/api/predict status=422 latency=%.4f request_id=%s", time.monotonic() - start, rid)
        return _safe_json_error("Field 'body' is required and must not be empty or whitespace only.", 422, rid)

    # Length limits
    if len(body) > 20000:
        logger.info("route=/api/predict status=422 latency=%.4f request_id=%s", time.monotonic() - start, rid)
        return _safe_json_error("Field 'body' exceeds maximum length of 20,000 characters.", 422, rid)

    if len(subject) > 300:
        logger.info("route=/api/predict status=422 latency=%.4f request_id=%s", time.monotonic() - start, rid)
        return _safe_json_error("Field 'subject' exceeds maximum length of 300 characters.", 422, rid)

    # Run inference
    try:
        prediction = service.predict(subject, body_stripped)
    except Exception:
        logger.exception("Inference error request_id=%s", rid)
        logger.info("route=/api/predict status=500 latency=%.4f request_id=%s", time.monotonic() - start, rid)
        return _safe_json_error("An internal error occurred during analysis.", 500, rid)

    # Run heuristic signals
    signals = analyze_signals(subject, body_stripped)

    # Build response (never log subject/body)
    result = {
        "label": prediction["label"],
        "score": prediction["score"],
        "model_version": prediction["model_version"],
        "thresholds_version": prediction["thresholds_version"],
        "signals": signals,
        "disclaimer": DISCLAIMER,
    }

    latency = time.monotonic() - start
    logger.info("route=/api/predict status=200 latency=%.4f request_id=%s", latency, rid)
    return jsonify(result), 200


@api_bp.route("/model-info", methods=["GET"])
def model_info():
    """Return model version, metrics summary, and limitations."""
    rid = _request_id()
    start = time.monotonic()

    service = get_model_service()
    if not service.loaded:
        logger.info("route=/api/model-info status=503 latency=%.4f request_id=%s", time.monotonic() - start, rid)
        return _safe_json_error("Model is not available.", 503, rid)

    info = service.get_model_info()
    latency = time.monotonic() - start
    logger.info("route=/api/model-info status=200 latency=%.4f request_id=%s", latency, rid)
    return jsonify(info), 200


# --- Page Routes ---


@pages_bp.route("/")
def landing():
    """Landing page."""
    return render_template("landing.html")


@pages_bp.route("/analyze")
def analyze():
    """Analyzer page."""
    return render_template("analyze.html")


@pages_bp.route("/how-it-works")
def how_it_works():
    """How It Works page."""
    return render_template("how_it_works.html")


@pages_bp.route("/about")
def about():
    """About page."""
    return render_template("about.html")


@pages_bp.route("/privacy")
def privacy():
    """Privacy Policy page."""
    return render_template("privacy.html")


@pages_bp.route("/terms")
def terms():
    """Terms of Service page."""
    return render_template("terms.html")


@pages_bp.route("/feedback")
def feedback():
    """Feedback page."""
    return render_template("feedback.html")
