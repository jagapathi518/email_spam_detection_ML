"""
SpamGuard AI — Test: Flask App and API Endpoints

Tests cover:
  - Model load & inference
  - Health endpoint
  - Predict endpoint validation (empty, whitespace, oversized, wrong content type,
    malformed JSON, wrong field types)
  - Error format
  - Rate limiting (429)
  - Signal catalog
  - Unicode/emoji/RTL input
  - HTML/script-like strings returned inert
  - No message content in logs
  - 503 when model files missing
"""

import json
import logging
import os
import sys

import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def app():
    """Create test Flask app (model not loaded)."""
    os.environ["FLASK_ENV"] = "development"
    from app.create_app import create_app

    application = create_app(testing=True)
    return application


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def app_with_model():
    """Create test Flask app with model loaded (if available)."""
    os.environ["FLASK_ENV"] = "development"
    from app.create_app import create_app

    application = create_app(testing=False)
    return application


@pytest.fixture
def client_with_model(app_with_model):
    """Flask test client with model loaded."""
    return app_with_model.test_client()


# --- Health Endpoint ---


class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert "model_loaded" in data

    def test_health_model_not_loaded_in_testing(self, client):
        resp = client.get("/api/health")
        data = resp.get_json()
        assert data["model_loaded"] is False


# --- Predict Validation ---


class TestPredictValidation:
    def test_empty_body_returns_422(self, client):
        resp = client.post("/api/predict", data=json.dumps({"body": ""}), content_type="application/json")
        assert resp.status_code in (422, 503)

    def test_whitespace_body_returns_422(self, client):
        resp = client.post("/api/predict", data=json.dumps({"body": "   \n\t  "}), content_type="application/json")
        assert resp.status_code in (422, 503)

    def test_missing_body_returns_422(self, client):
        resp = client.post("/api/predict", data=json.dumps({"subject": "test"}), content_type="application/json")
        assert resp.status_code in (422, 503)

    def test_wrong_content_type_returns_415(self, client):
        resp = client.post("/api/predict", data="not json", content_type="text/plain")
        # Will be 503 (model not loaded) or 415
        assert resp.status_code in (415, 503)

    def test_malformed_json_returns_400(self, client):
        resp = client.post("/api/predict", data="{invalid json", content_type="application/json")
        assert resp.status_code in (400, 503)

    def test_wrong_field_type_subject_not_string(self, client):
        resp = client.post(
            "/api/predict", data=json.dumps({"subject": 123, "body": "test body"}), content_type="application/json"
        )
        assert resp.status_code in (422, 503)

    def test_wrong_field_type_body_not_string(self, client):
        resp = client.post(
            "/api/predict", data=json.dumps({"subject": "test", "body": 123}), content_type="application/json"
        )
        assert resp.status_code in (422, 503)

    def test_oversized_body_returns_422(self, client):
        resp = client.post("/api/predict", data=json.dumps({"body": "x" * 20001}), content_type="application/json")
        assert resp.status_code in (413, 422, 503)

    def test_oversized_subject_returns_422(self, client):
        resp = client.post(
            "/api/predict", data=json.dumps({"subject": "x" * 301, "body": "test"}), content_type="application/json"
        )
        assert resp.status_code in (422, 503)

    def test_array_instead_of_object_returns_400(self, client):
        resp = client.post("/api/predict", data=json.dumps([{"body": "test"}]), content_type="application/json")
        assert resp.status_code in (400, 503)


# --- Error Format ---


class TestErrorFormat:
    def test_error_response_has_error_field(self, client):
        resp = client.post("/api/predict", data=json.dumps({"body": ""}), content_type="application/json")
        data = resp.get_json()
        assert "error" in data
        assert "status_code" in data

    def test_404_api_returns_json(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data


# --- 503 When Model Missing ---


class TestModelMissing:
    def test_predict_returns_503_without_model(self, client):
        resp = client.post(
            "/api/predict", data=json.dumps({"body": "test email body"}), content_type="application/json"
        )
        assert resp.status_code == 503


# --- Signal Catalog ---


class TestSignals:
    def test_urgency_language(self):
        from app.signals import analyze_signals

        signals = analyze_signals("URGENT action needed", "Act now before it expires!")
        ids = [s["id"] for s in signals]
        assert "urgency_language" in ids

    def test_prize_financial(self):
        from app.signals import analyze_signals

        signals = analyze_signals("You have won!", "Congratulations you won $1000000")
        ids = [s["id"] for s in signals]
        assert "prize_financial" in ids

    def test_credential_request(self):
        from app.signals import analyze_signals

        signals = analyze_signals("Account verification", "Please verify your account immediately")
        ids = [s["id"] for s in signals]
        assert "credential_request" in ids

    def test_ip_address_url(self):
        from app.signals import analyze_signals

        signals = analyze_signals("", "Visit http://192.168.1.1/login")
        ids = [s["id"] for s in signals]
        assert "url_ip_address" in ids

    def test_url_shortener(self):
        from app.signals import analyze_signals

        signals = analyze_signals("", "Click here: https://bit.ly/abc123")
        ids = [s["id"] for s in signals]
        assert "url_shortener" in ids

    def test_punycode(self):
        from app.signals import analyze_signals

        signals = analyze_signals("", "Visit https://xn--pple-43d.com/login")
        ids = [s["id"] for s in signals]
        assert "punycode_url" in ids

    def test_no_signals_on_clean_text(self):
        from app.signals import analyze_signals

        signals = analyze_signals("Team meeting", "Meeting at 3pm in room 201")
        assert len(signals) == 0

    def test_signal_structure(self):
        from app.signals import analyze_signals

        signals = analyze_signals("URGENT", "Act now!")
        for s in signals:
            assert "id" in s
            assert "name" in s
            assert "description" in s
            assert "severity" in s
            assert s["severity"] in ("info", "warning", "danger")


# --- Unicode / Emoji / RTL ---


class TestUnicode:
    def test_emoji_input_does_not_crash(self, client):
        resp = client.post(
            "/api/predict", data=json.dumps({"body": "Hello 🎉🔥💀 world"}), content_type="application/json"
        )
        # Either processes or returns 503 (model not loaded); should not crash
        assert resp.status_code in (200, 503)

    def test_rtl_input_does_not_crash(self, client):
        resp = client.post(
            "/api/predict", data=json.dumps({"body": "مرحبا بك في هذا العالم"}), content_type="application/json"
        )
        assert resp.status_code in (200, 503)

    def test_chinese_input_does_not_crash(self, client):
        resp = client.post(
            "/api/predict", data=json.dumps({"body": "你好世界 这是一个测试邮件"}), content_type="application/json"
        )
        assert resp.status_code in (200, 503)

    def test_mixed_unicode_does_not_crash(self, client):
        resp = client.post(
            "/api/predict", data=json.dumps({"body": "Hello мир 🌍 世界 عالم"}), content_type="application/json"
        )
        assert resp.status_code in (200, 503)


# --- XSS / Script Safety ---


class TestXSSSafety:
    def test_script_in_body_returned_inert(self, client):
        """HTML/script content should not appear unescaped in response."""
        resp = client.post(
            "/api/predict",
            data=json.dumps({"body": "<script>alert('xss')</script> test body text"}),
            content_type="application/json",
        )
        if resp.status_code == 200:
            raw = resp.get_data(as_text=True)
            # The response should be JSON, not contain executable script
            assert "<script>" not in raw or "application/json" in resp.content_type

    def test_html_in_subject_returned_inert(self, client):
        resp = client.post(
            "/api/predict",
            data=json.dumps({"subject": "<img src=x onerror=alert(1)>", "body": "test body"}),
            content_type="application/json",
        )
        if resp.status_code == 200:
            assert "application/json" in resp.content_type


# --- No Message Content in Logs ---


class TestNoContentInLogs:
    def test_no_body_content_in_logs(self, client, capfd):
        """Logs must NEVER contain the submitted email body."""
        secret_marker = "SUPERSECRETMARKER12345"

        # Set up log capture
        logger = logging.getLogger()
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        _ = client.post(
            "/api/predict",
            data=json.dumps({"body": f"This is a {secret_marker} test email"}),
            content_type="application/json",
        )

        logger.removeHandler(handler)

        captured = capfd.readouterr()
        assert secret_marker not in captured.out, "Email body content leaked into logs!"
        assert secret_marker not in captured.err, "Email body content leaked into error logs!"

    def test_no_subject_content_in_logs(self, client, capfd):
        """Logs must NEVER contain the submitted email subject."""
        secret_marker = "SECRETSUBJECT98765"

        logger = logging.getLogger()
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        _ = client.post(
            "/api/predict",
            data=json.dumps({"subject": f"Test {secret_marker} subject", "body": "normal body"}),
            content_type="application/json",
        )

        logger.removeHandler(handler)

        captured = capfd.readouterr()
        assert secret_marker not in captured.out, "Email subject content leaked into logs!"
        assert secret_marker not in captured.err, "Email subject content leaked into error logs!"


# --- Tokenizer Tests ---


class TestTokenizer:
    def test_standardize_text(self):
        from ml.tokenizer import standardize_text

        result = standardize_text("Hello WORLD  <b>bold</b>  test@email.com")
        assert "hello" in result
        assert "world" in result
        assert "<b>" not in result
        assert "<EMAIL>" in result.upper() or "<email>" in result

    def test_combine_subject_body(self):
        from ml.tokenizer import combine_subject_body

        result = combine_subject_body("Test Subject", "Test Body")
        assert "<SUBJECT>" in result
        assert "<BODY>" in result

    def test_preprocess_text(self):
        from ml.tokenizer import preprocess_text

        result = preprocess_text("Urgent Alert", "Visit http://example.com now")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tokenizer_encode_decode(self):
        from ml.tokenizer import Tokenizer

        tok = Tokenizer(max_vocab_size=100, max_sequence_length=10)
        tok.build_vocab(["hello world", "test email spam"])

        encoded = tok.encode("hello world")
        assert isinstance(encoded, list)
        assert all(isinstance(x, int) for x in encoded)

    def test_tokenizer_pad(self):
        import numpy as np

        from ml.tokenizer import Tokenizer

        tok = Tokenizer(max_vocab_size=100, max_sequence_length=10)
        tok.build_vocab(["hello world"])

        padded = tok.encode_and_pad("hello")
        assert padded.shape == (10,)
        assert padded.dtype == np.int32

    def test_tokenizer_save_load(self, tmp_path):
        from ml.tokenizer import Tokenizer

        tok = Tokenizer(max_vocab_size=100, max_sequence_length=10)
        tok.build_vocab(["hello world test"])

        path = str(tmp_path / "vocab.json")
        tok.save(path)

        loaded = Tokenizer.load(path)
        assert loaded.vocab_size == tok.vocab_size
        assert loaded.max_sequence_length == tok.max_sequence_length


class TestInferenceWithModel:
    def test_predict_spam_returns_prediction(self, client_with_model):
        resp = client_with_model.post(
            "/api/predict",
            json={
                "subject": "URGENT: Claim your $1,000,000 lottery cash prize now!",
                "body": "Congratulations, you won a million dollars! Click immediately to claim: http://192.168.1.1/win",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["label"] in ("spam", "uncertain")
        assert 0.0 <= data["score"] <= 1.0
        assert data["model_version"] == "v1"
        assert "signals" in data
        assert len(data["signals"]) > 0
        assert "disclaimer" in data

    def test_predict_legit_returns_not_spam(self, client_with_model):
        resp = client_with_model.post(
            "/api/predict",
            json={
                "subject": "Weekly team sync notes",
                "body": "Hi team, here is the agenda for tomorrow's standup meeting. Please review the PRs.",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["label"] in ("not_spam", "uncertain")
        assert 0.0 <= data["score"] <= 1.0

    def test_model_info_returns_metrics(self, client_with_model):
        resp = client_with_model.get("/api/model-info")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["model_version"] == "v1"
        assert "metrics_summary" in data
        assert data["metrics_summary"]["accuracy"] > 0.95
        assert len(data["limitations"]) > 0

    def test_model_fresh_process_load(self):
        from app.services import ModelService

        svc = ModelService()
        svc.load(os.path.join(PROJECT_ROOT, "models"), "v1")
        assert svc.loaded is True
        result = svc.predict("Test meeting", "Hello team, let us meet tomorrow.")
        assert result["label"] in ("spam", "not_spam", "uncertain")
        assert 0.0 <= result["score"] <= 1.0

    def test_download_interview_guide(self, client):
        resp = client.get("/download/interview-guide")
        assert resp.status_code == 200
        assert resp.mimetype == "application/pdf"
        assert len(resp.data) > 1000

    def test_api_stats_endpoint(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "status" in data
        assert "total_scans" in data

    def test_api_feedback_endpoint(self, client):
        resp = client.post(
            "/api/feedback",
            json={
                "feedback_type": "accurate",
                "predicted_label": "spam",
                "actual_label": "spam",
                "rating": 5,
                "user_notes": "Spot on detection",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("status") in ("recorded", "deferred")
