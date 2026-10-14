"""
SpamGuard AI — Model Service

Singleton service that loads and manages the ML model.
Handles inference, threshold application, and model info.
"""

import json
import logging
import os
from typing import Optional

from ml.export import NumpyModel
from ml.tokenizer import Tokenizer, preprocess_text

logger = logging.getLogger(__name__)


class ModelService:
    """
    Loads the NumPy model once at startup and provides inference.

    Thread-safe: NumPy operations on read-only weights are safe
    with multiple reader threads (gunicorn with threads).
    """

    def __init__(self):
        self.model: Optional[NumpyModel] = None
        self.tokenizer: Optional[Tokenizer] = None
        self.thresholds: Optional[dict] = None
        self.config: Optional[dict] = None
        self.metrics: Optional[dict] = None
        self.model_version: Optional[str] = None
        self.loaded = False
        self._load_error: Optional[str] = None

    def load(self, models_base_dir: str, version: str = "v1") -> None:
        """
        Load model, tokenizer, thresholds, and metrics.

        Called once at startup.
        """
        model_dir = os.path.join(models_base_dir, version)
        logger.info("Loading model from %s", model_dir)

        try:
            # Load config
            config_path = os.path.join(model_dir, "config.json")
            with open(config_path) as f:
                self.config = json.load(f)

            # Load NumPy model
            self.model = NumpyModel()
            self.model.load(model_dir, use_float16=False)

            # Load tokenizer
            vocab_path = os.path.join(model_dir, "vocab.json")
            self.tokenizer = Tokenizer.load(vocab_path)

            # Load thresholds
            thresholds_path = os.path.join(model_dir, "thresholds.json")
            with open(thresholds_path) as f:
                self.thresholds = json.load(f)

            # Load metrics
            metrics_path = os.path.join(model_dir, "metrics.json")
            with open(metrics_path) as f:
                self.metrics = json.load(f)

            self.model_version = version
            self.loaded = True
            self._load_error = None

            # Warm up with a dummy inference
            logger.info("Warming up model...")
            dummy_text = preprocess_text("test subject", "test body content")
            dummy_input = self.tokenizer.encode_and_pad(dummy_text)
            _ = self.model.predict_single(dummy_input)
            logger.info("Model loaded and warmed up successfully (version=%s)", version)

        except Exception as e:
            self._load_error = str(e)
            self.loaded = False
            logger.error("Failed to load model: %s", e)
            raise

    def predict(self, subject: str, body: str) -> dict:
        """
        Run inference on an email.

        Args:
            subject: Email subject line
            body: Email body text

        Returns:
            dict with: label, score, model_version, thresholds_version
        """
        if not self.loaded:
            raise RuntimeError("Model not loaded")

        # Preprocess (uses the shared function)
        preprocessed = preprocess_text(subject, body)

        # Encode and pad
        encoded = self.tokenizer.encode_and_pad(preprocessed)

        # Inference
        score = self.model.predict_single(encoded)

        # Apply thresholds
        spam_thresh = self.thresholds["spam_threshold"]
        not_spam_thresh = self.thresholds["not_spam_threshold"]

        if score >= spam_thresh:
            label = "spam"
        elif score <= not_spam_thresh:
            label = "not_spam"
        else:
            label = "uncertain"

        return {
            "label": label,
            "score": round(float(score), 6),
            "model_version": self.model_version,
            "thresholds_version": self.model_version,
        }

    def get_model_info(self) -> dict:
        """
        Return model information for the /api/model-info endpoint.
        """
        if not self.loaded or self.metrics is None:
            return {"error": "Model not loaded"}

        prod_metrics = self.metrics.get("production_model", {})

        return {
            "model_version": self.model_version,
            "dataset": self.metrics.get("dataset", "Unknown"),
            "metrics_summary": {
                "accuracy": prod_metrics.get("accuracy"),
                "precision": prod_metrics.get("precision"),
                "recall": prod_metrics.get("recall"),
                "f1": prod_metrics.get("f1"),
                "roc_auc": prod_metrics.get("roc_auc"),
            },
            "limitations": [
                "Trained on the Apache SpamAssassin public corpus (early 2000s emails). May not recognize modern phishing patterns.",
                "Does not analyze email headers, attachments, SPF/DKIM/DMARC, or sender reputation.",
                "The model score is not a calibrated probability.",
                "This tool does not guarantee an email is safe. Always exercise caution with suspicious emails.",
                "Rate limiting counters reset on server restart.",
            ],
        }


# Global singleton
_model_service: Optional[ModelService] = None


def get_model_service() -> ModelService:
    """Get or create the global ModelService singleton."""
    global _model_service
    if _model_service is None:
        _model_service = ModelService()
    return _model_service
