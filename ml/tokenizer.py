"""
SpamGuard AI — Plain-Python/NumPy Tokenizer Module

This module is shared between training, evaluation, and serving to ensure
identical preprocessing everywhere. It does NOT depend on TensorFlow.

Pipeline:
  1. Text standardization (lowercase, strip HTML tags, normalize whitespace, etc.)
  2. Tokenization (split on whitespace/punctuation, map to integer IDs via vocab)
  3. Padding/truncation to fixed sequence length
"""

import json
import os
import re
import unicodedata
from typing import Optional

import numpy as np

# --- Text Standardization ---

# Pre-compiled regex patterns for performance
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
_MULTI_SPACE_RE = re.compile(r"\s+")
_NON_ALPHANUM_RE = re.compile(r"[^a-zA-Z0-9\s<>]")


def standardize_text(text: str) -> str:
    """
    Standardize text for tokenization.

    Steps:
      - Unicode normalize (NFKD)
      - Lowercase
      - Strip HTML tags
      - Replace URLs with <URL> token
      - Replace emails with <EMAIL> token
      - Replace phone numbers with <PHONE> token
      - Remove non-alphanumeric characters (keep spaces and special tokens)
      - Collapse whitespace
      - Strip leading/trailing whitespace
    """
    if not text:
        return ""

    # Unicode normalization
    text = unicodedata.normalize("NFKD", text)

    # Lowercase
    text = text.lower()

    # Strip HTML tags
    text = _HTML_TAG_RE.sub(" ", text)

    # Replace URLs (before email, since URLs may contain @-like patterns)
    text = _URL_RE.sub(" <URL> ", text)

    # Replace emails
    text = _EMAIL_RE.sub(" <EMAIL> ", text)

    # Replace phone numbers
    text = _PHONE_RE.sub(" <PHONE> ", text)

    # Remove non-alphanumeric (keep angle brackets for special tokens)
    text = _NON_ALPHANUM_RE.sub(" ", text)

    # Collapse whitespace
    text = _MULTI_SPACE_RE.sub(" ", text)

    return text.strip()


def combine_subject_body(subject: str, body: str) -> str:
    """
    Combine email subject and body into a single string.

    This is the shared function used in BOTH training and inference
    to ensure identical input formatting.

    Format: "<SUBJECT> {subject} <BODY> {body}"
    """
    subject = subject.strip() if subject else ""
    body = body.strip() if body else ""

    parts = []
    if subject:
        parts.append(f"<SUBJECT> {subject}")
    if body:
        parts.append(f"<BODY> {body}")

    return " ".join(parts) if parts else ""


# --- Vocabulary ---

# Special tokens
PAD_TOKEN = "<PAD>"
UNK_TOKEN = "<UNK>"
URL_TOKEN = "<URL>"
EMAIL_TOKEN = "<EMAIL>"
PHONE_TOKEN = "<PHONE>"
SUBJECT_TOKEN = "<SUBJECT>"
BODY_TOKEN = "<BODY>"

SPECIAL_TOKENS = [PAD_TOKEN, UNK_TOKEN, URL_TOKEN, EMAIL_TOKEN, PHONE_TOKEN, SUBJECT_TOKEN, BODY_TOKEN]

PAD_ID = 0
UNK_ID = 1


class Tokenizer:
    """
    A simple word-level tokenizer that maps tokens to integer IDs.

    The vocabulary is built during training and saved as a JSON file
    for use in serving.
    """

    def __init__(self, vocab: Optional[dict] = None, max_vocab_size: int = 20000, max_sequence_length: int = 512):
        self.max_vocab_size = max_vocab_size
        self.max_sequence_length = max_sequence_length

        if vocab is not None:
            self.word_to_id = vocab
            self.id_to_word = {v: k for k, v in vocab.items()}
        else:
            self.word_to_id = {}
            self.id_to_word = {}

    @property
    def vocab_size(self) -> int:
        return len(self.word_to_id)

    def build_vocab(self, texts: list[str]) -> None:
        """
        Build vocabulary from a list of ALREADY STANDARDIZED texts.

        Counts word frequencies, keeps top max_vocab_size words,
        plus special tokens.
        """
        word_counts: dict[str, int] = {}

        for text in texts:
            for word in text.split():
                if word in SPECIAL_TOKENS:
                    continue
                word_counts[word] = word_counts.get(word, 0) + 1

        # Sort by frequency (descending), then alphabetically for ties
        sorted_words = sorted(word_counts.items(), key=lambda x: (-x[1], x[0]))

        # Build vocab with special tokens first
        self.word_to_id = {}
        for token in SPECIAL_TOKENS:
            self.word_to_id[token] = len(self.word_to_id)

        # Add most frequent words
        budget = self.max_vocab_size - len(SPECIAL_TOKENS)
        for word, count in sorted_words[:budget]:
            self.word_to_id[word] = len(self.word_to_id)

        self.id_to_word = {v: k for k, v in self.word_to_id.items()}

        print(f"Vocabulary built: {len(self.word_to_id)} tokens (from {len(word_counts)} unique words)")

    def encode(self, text: str) -> list[int]:
        """
        Encode a STANDARDIZED text string to a list of integer token IDs.

        Unknown words are mapped to UNK_ID.
        """
        tokens = text.split()
        ids = []
        for token in tokens:
            if token in self.word_to_id:
                ids.append(self.word_to_id[token])
            else:
                ids.append(UNK_ID)
        return ids

    def pad_sequence(self, ids: list[int]) -> np.ndarray:
        """
        Pad or truncate a sequence to max_sequence_length.

        Returns a 1D numpy array of int32.
        """
        length = len(ids)
        if length >= self.max_sequence_length:
            return np.array(ids[: self.max_sequence_length], dtype=np.int32)

        # Pad with PAD_ID (0)
        padded = np.zeros(self.max_sequence_length, dtype=np.int32)
        padded[:length] = ids
        return padded

    def encode_and_pad(self, text: str) -> np.ndarray:
        """
        Full pipeline: encode text to IDs, then pad/truncate.

        Input should be ALREADY STANDARDIZED text.
        Returns a 1D numpy array of shape (max_sequence_length,).
        """
        ids = self.encode(text)
        return self.pad_sequence(ids)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        """
        Encode and pad a batch of STANDARDIZED texts.

        Returns a 2D numpy array of shape (batch_size, max_sequence_length).
        """
        return np.array([self.encode_and_pad(t) for t in texts], dtype=np.int32)

    def save(self, path: str) -> None:
        """Save vocabulary and config to a JSON file."""
        data = {
            "vocab": self.word_to_id,
            "max_vocab_size": self.max_vocab_size,
            "max_sequence_length": self.max_sequence_length,
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Vocabulary saved to {path}")

    @classmethod
    def load(cls, path: str) -> "Tokenizer":
        """Load vocabulary and config from a JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        tokenizer = cls(
            vocab=data["vocab"],
            max_vocab_size=data.get("max_vocab_size", 20000),
            max_sequence_length=data.get("max_sequence_length", 512),
        )
        return tokenizer


def preprocess_text(subject: str, body: str) -> str:
    """
    Full preprocessing pipeline for a single email.

    Combines subject and body, then standardizes.
    This is the single entry point used in BOTH training and inference.
    """
    combined = combine_subject_body(subject, body)
    return standardize_text(combined)
