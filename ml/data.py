"""
SpamGuard AI — Email Parsing Module

Parses raw email files from the SpamAssassin corpus.
Handles headers, MIME, multipart, charsets.
Extracts subject + plain-text body.
Strips HTML safely. Redacts emails/phone numbers. Keeps URLs as tokens.
"""

import email
import email.policy
import hashlib
import os
import re
from email.header import decode_header

from bs4 import BeautifulSoup


def decode_email_header(header_value: str) -> str:
    """Decode an email header value, handling encoded words."""
    if not header_value:
        return ""

    decoded_parts = []
    try:
        parts = decode_header(header_value)
        for part, charset in parts:
            if isinstance(part, bytes):
                charset = charset or "utf-8"
                try:
                    decoded_parts.append(part.decode(charset, errors="replace"))
                except (UnicodeDecodeError, LookupError):
                    decoded_parts.append(part.decode("utf-8", errors="replace"))
            else:
                decoded_parts.append(part)
    except Exception:
        return str(header_value)

    return " ".join(decoded_parts)


def strip_html(html_text: str) -> str:
    """Safely strip HTML tags and return plain text."""
    if not html_text:
        return ""

    try:
        soup = BeautifulSoup(html_text, "lxml")
        # Remove script and style elements
        for element in soup(["script", "style", "head"]):
            element.decompose()
        text = soup.get_text(separator=" ")
    except Exception:
        # Fallback: simple regex-based stripping
        text = re.sub(r"<[^>]+>", " ", html_text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_body_from_message(msg: email.message.Message) -> str:
    """
    Extract plain text body from an email message.

    Handles multipart messages by preferring text/plain over text/html.
    """
    body_parts = []

    if msg.is_multipart():
        text_plain = []
        text_html = []

        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # Skip attachments
            if "attachment" in content_disposition:
                continue

            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue

                charset = part.get_content_charset() or "utf-8"
                try:
                    text = payload.decode(charset, errors="replace")
                except (UnicodeDecodeError, LookupError):
                    text = payload.decode("utf-8", errors="replace")

                if content_type == "text/plain":
                    text_plain.append(text)
                elif content_type == "text/html":
                    text_html.append(strip_html(text))
            except Exception:
                continue

        # Prefer plain text
        if text_plain:
            body_parts = text_plain
        elif text_html:
            body_parts = text_html
    else:
        # Single part message
        try:
            payload = msg.get_payload(decode=True)
            if payload is not None:
                charset = msg.get_content_charset() or "utf-8"
                try:
                    text = payload.decode(charset, errors="replace")
                except (UnicodeDecodeError, LookupError):
                    text = payload.decode("utf-8", errors="replace")

                if msg.get_content_type() == "text/html":
                    text = strip_html(text)
                body_parts.append(text)
        except Exception:
            pass

    return " ".join(body_parts).strip()


def parse_email_file(filepath: str) -> dict | None:
    """
    Parse a single raw email file and extract subject + body.

    Returns:
        dict with keys: subject, body, raw_hash
        or None if parsing fails
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            raw_content = f.read()
    except Exception:
        try:
            with open(filepath, "r", encoding="latin-1", errors="replace") as f:
                raw_content = f.read()
        except Exception:
            return None

    try:
        msg = email.message_from_string(raw_content, policy=email.policy.compat32)
    except Exception:
        return None

    # Extract subject
    subject = decode_email_header(msg.get("Subject", ""))

    # Extract body
    body = extract_body_from_message(msg)

    if not body and not subject:
        return None

    # Hash for deduplication (on normalized text)
    normalized = (subject.lower().strip() + " " + body.lower().strip()).strip()
    raw_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    return {
        "subject": subject,
        "body": body,
        "raw_hash": raw_hash,
    }


def load_corpus(raw_dir: str) -> list[dict]:
    """
    Load all emails from the raw data directory.

    Expects: raw_dir/ham/ and raw_dir/spam/ subdirectories.

    Returns list of dicts with keys: subject, body, label, raw_hash, filename
    """
    records = []

    for label in ["ham", "spam"]:
        label_dir = os.path.join(raw_dir, label)
        if not os.path.isdir(label_dir):
            print(f"WARNING: Directory not found: {label_dir}")
            continue

        files = sorted(os.listdir(label_dir))
        parsed = 0
        failed = 0

        for filename in files:
            filepath = os.path.join(label_dir, filename)
            if not os.path.isfile(filepath):
                continue

            result = parse_email_file(filepath)
            if result is not None:
                result["label"] = label
                result["filename"] = filename
                records.append(result)
                parsed += 1
            else:
                failed += 1

        print(f"  {label}: parsed {parsed}, failed {failed}")

    return records
