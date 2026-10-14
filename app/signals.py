"""
SpamGuard AI — Heuristic Signal Catalog

Documented, tested rules that detect common spam/phishing patterns.
These are labeled as "heuristic signals" and are separate from the
model prediction. They analyze the raw text for known patterns.
"""

import re
from dataclasses import dataclass


@dataclass
class Signal:
    """A heuristic signal found in the email text."""

    id: str
    name: str
    description: str
    severity: str  # "info", "warning", "danger"


# --- Pattern Definitions ---

URGENCY_PATTERNS = [
    re.compile(
        r"\b(urgent|immediate(?:ly)?|act\s+now|limited\s+time|expires?\s+(?:soon|today)|hurry|don'?t\s+(?:wait|delay|miss)|last\s+chance|final\s+(?:notice|warning))\b",
        re.IGNORECASE,
    ),
]

PRIZE_FINANCIAL_PATTERNS = [
    re.compile(
        r"\b(congratulations|you(?:'ve|\s+have)\s+won|winner|prize|lottery|jackpot|million\s+dollars?|free\s+(?:money|gift|cash)|claim\s+your|inheritance|beneficiary)\b",
        re.IGNORECASE,
    ),
]

CREDENTIAL_PATTERNS = [
    re.compile(
        r"\b(verify\s+your\s+(?:account|identity|email|password)|confirm\s+your\s+(?:account|identity)|update\s+your\s+(?:payment|billing|account)|social\s+security|ssn|credit\s+card\s+number|bank\s+account\s+(?:number|details)|enter\s+your\s+password|login\s+credentials)\b",
        re.IGNORECASE,
    ),
]

URL_IP_PATTERN = re.compile(r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
URL_SHORTENER_PATTERN = re.compile(
    r"https?://(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|ow\.ly|is\.gd|buff\.ly|short\.to|cutt\.ly|rb\.gy)/",
    re.IGNORECASE,
)
# Punycode detection (internationalized domain names that may be deceptive)
PUNYCODE_PATTERN = re.compile(r"https?://[^\s]*xn--[^\s/]+", re.IGNORECASE)


def analyze_signals(subject: str, body: str) -> list[dict]:
    """
    Analyze email text for heuristic spam/phishing signals.

    Args:
        subject: Email subject line
        body: Email body text

    Returns:
        List of signal dicts with keys: id, name, description, severity
    """
    combined = f"{subject} {body}"
    signals = []

    # Urgency language
    for pattern in URGENCY_PATTERNS:
        if pattern.search(combined):
            signals.append(
                {
                    "id": "urgency_language",
                    "name": "Urgency Language",
                    "description": "Contains words or phrases designed to create a sense of urgency, a common tactic in spam and phishing emails.",
                    "severity": "warning",
                }
            )
            break

    # Prize / financial claims
    for pattern in PRIZE_FINANCIAL_PATTERNS:
        if pattern.search(combined):
            signals.append(
                {
                    "id": "prize_financial",
                    "name": "Prize or Financial Claim",
                    "description": "Contains language about prizes, winnings, or unexpected financial offers — a hallmark of scam emails.",
                    "severity": "danger",
                }
            )
            break

    # Credential / sensitive info requests
    for pattern in CREDENTIAL_PATTERNS:
        if pattern.search(combined):
            signals.append(
                {
                    "id": "credential_request",
                    "name": "Credential or Sensitive Info Request",
                    "description": "Asks for passwords, account details, or personal information — a key indicator of phishing.",
                    "severity": "danger",
                }
            )
            break

    # IP address URLs
    if URL_IP_PATTERN.search(combined):
        signals.append(
            {
                "id": "url_ip_address",
                "name": "IP Address URL",
                "description": "Contains a link using an IP address instead of a domain name, which is unusual and often associated with phishing.",
                "severity": "warning",
            }
        )

    # URL shorteners
    if URL_SHORTENER_PATTERN.search(combined):
        signals.append(
            {
                "id": "url_shortener",
                "name": "URL Shortener",
                "description": "Contains a shortened URL that hides the actual destination. Legitimate senders typically use their own domain.",
                "severity": "info",
            }
        )

    # Punycode
    if PUNYCODE_PATTERN.search(combined):
        signals.append(
            {
                "id": "punycode_url",
                "name": "Punycode/IDN URL",
                "description": "Contains an internationalized domain name (punycode) that may be designed to look like a legitimate domain.",
                "severity": "warning",
            }
        )

    return signals
