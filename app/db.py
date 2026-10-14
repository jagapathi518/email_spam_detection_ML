"""
SpamGuard AI — Database Module (Supabase PostgreSQL Integration)

Provides privacy-first scan analytics and user feedback tracking.
Strictly adheres to privacy rules: email body and subject content
are NEVER persisted to the database.

Features:
  - Graceful fallback: app continues working normally if DB is offline or unset.
  - Connection pooling / SSL connection to Supabase PostgreSQL.
  - Automatic table creation on startup.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Cache tables initialized status
_db_initialized = False


def _load_env_if_needed():
    """Load key-value pairs from .env if DATABASE_URL is not in os.environ."""
    if "DATABASE_URL" not in os.environ:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception as e:
                logger.warning("Could not read .env file: %s", e)


def get_db_url() -> Optional[str]:
    """Return the database URL or None if not configured."""
    _load_env_if_needed()
    url = os.environ.get("DATABASE_URL")
    if not url:
        return None
    # Ensure SSL is enabled for Supabase
    if "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


def get_connection():
    """Get a raw psycopg2 database connection. Caller is responsible for closing."""
    url = get_db_url()
    if not url:
        return None

    try:
        import psycopg2

        conn = psycopg2.connect(url, connect_timeout=5)
        return conn
    except Exception as e:
        logger.warning("Supabase DB connection failed: %s", e)
        return None


def init_db() -> bool:
    """Create database tables if they do not exist."""
    global _db_initialized
    if _db_initialized:
        return True

    conn = get_connection()
    if not conn:
        logger.info("Database not configured or unreachable; operating in ephemeral mode.")
        return False

    try:
        with conn.cursor() as cur:
            # 1. Scan Analytics Table (Zero-content: only metadata, counts & labels)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS scan_analytics (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    label VARCHAR(20) NOT NULL,
                    score REAL NOT NULL,
                    signals_count INT DEFAULT 0,
                    signals_json JSONB DEFAULT '[]'::jsonb,
                    char_length INT DEFAULT 0,
                    model_version VARCHAR(20) DEFAULT 'v1'
                );
                CREATE INDEX IF NOT EXISTS idx_scan_analytics_created ON scan_analytics (created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_scan_analytics_label ON scan_analytics (label);
                """
            )

            # 2. User Feedback Table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    feedback_type VARCHAR(50) NOT NULL,
                    predicted_label VARCHAR(20),
                    actual_label VARCHAR(20),
                    user_notes TEXT,
                    rating INT
                );
                CREATE INDEX IF NOT EXISTS idx_user_feedback_created ON user_feedback (created_at DESC);
                """
            )
            conn.commit()
            _db_initialized = True
            logger.info("Supabase database tables verified/initialized successfully.")
            return True
    except Exception as e:
        logger.error("Failed to initialize database tables: %s", e)
        conn.rollback()
        return False
    finally:
        conn.close()


def log_scan_event(
    label: str,
    score: float,
    signals: List[Dict[str, Any]],
    char_length: int = 0,
    model_version: str = "v1",
) -> bool:
    """
    Log an anonymous scan event to Supabase.
    CRITICAL: Never passes or stores email body or subject text.
    """
    conn = get_connection()
    if not conn:
        return False

    try:
        # Extract signal IDs only (no text excerpts)
        signal_ids = [s.get("id") or s.get("name", "unknown") for s in (signals or [])]

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scan_analytics
                    (label, score, signals_count, signals_json, char_length, model_version)
                VALUES
                    (%s, %s, %s, %s, %s, %s);
                """,
                (
                    label,
                    float(score),
                    len(signals or []),
                    json.dumps(signal_ids),
                    int(char_length),
                    model_version,
                ),
            )
            conn.commit()
            return True
    except Exception as e:
        logger.warning("Failed to record scan analytics event: %s", e)
        conn.rollback()
        return False
    finally:
        conn.close()


def record_feedback(
    feedback_type: str,
    predicted_label: Optional[str] = None,
    actual_label: Optional[str] = None,
    user_notes: Optional[str] = None,
    rating: Optional[int] = None,
) -> bool:
    """Record user feedback into Supabase."""
    conn = get_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_feedback
                    (feedback_type, predicted_label, actual_label, user_notes, rating)
                VALUES
                    (%s, %s, %s, %s, %s);
                """,
                (
                    feedback_type,
                    predicted_label,
                    actual_label,
                    user_notes,
                    rating,
                ),
            )
            conn.commit()
            return True
    except Exception as e:
        logger.warning("Failed to record user feedback: %s", e)
        conn.rollback()
        return False
    finally:
        conn.close()


def get_analytics_summary() -> Dict[str, Any]:
    """Retrieve aggregate statistics from Supabase for public dashboard / stats."""
    conn = get_connection()
    if not conn:
        return {
            "status": "offline",
            "message": "Database not configured or unreachable",
            "total_scans": 0,
            "spam_count": 0,
            "not_spam_count": 0,
            "uncertain_count": 0,
        }

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE label = 'spam') as spam,
                    COUNT(*) FILTER (WHERE label = 'not_spam') as not_spam,
                    COUNT(*) FILTER (WHERE label = 'uncertain') as uncertain
                FROM scan_analytics;
                """
            )
            row = cur.fetchone()
            total, spam, not_spam, uncertain = row if row else (0, 0, 0, 0)

            cur.execute(
                """
                SELECT COUNT(*) FROM user_feedback;
                """
            )
            feedback_count = cur.fetchone()[0]

            return {
                "status": "online",
                "total_scans": total or 0,
                "spam_count": spam or 0,
                "not_spam_count": not_spam or 0,
                "uncertain_count": uncertain or 0,
                "feedback_submissions": feedback_count or 0,
            }
    except Exception as e:
        logger.warning("Failed to fetch analytics summary: %s", e)
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()
