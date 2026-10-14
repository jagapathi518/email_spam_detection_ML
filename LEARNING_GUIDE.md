# Learning Guide — SpamGuard AI

A beginner-friendly walkthrough of every important file and concept in this project.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Key Files Explained](#key-files-explained)
3. [How Tokenization Works](#how-tokenization-works)
4. [How the Model Turns Text into a Score](#how-the-model-turns-text-into-a-score)
5. [Why We Train with TensorFlow but Serve Without It](#why-we-train-with-tensorflow-but-serve-without-it)
6. [How Thresholds Create Three Labels](#how-thresholds-create-three-labels)
7. [How Flask and the Frontend Communicate](#how-flask-and-the-frontend-communicate)
8. [How Docker and Render Deployment Work](#how-docker-and-render-deployment-work)
9. [Troubleshooting Table](#troubleshooting-table)

---

## Project Overview

SpamGuard AI is a web application that analyzes email text for spam indicators. The project demonstrates a complete ML pipeline: data collection → preprocessing → training → evaluation → deployment.

## Key Files Explained

### `ml/tokenizer.py` — The Shared Preprocessor
This is the **most important module** in the project. It converts raw email text into numbers that the model can understand. The same code is used during training AND serving, ensuring identical preprocessing.

**Key functions:**
- `standardize_text()` — Lowercases, strips HTML, replaces URLs/emails/phones with tokens
- `combine_subject_body()` — Joins subject and body with special marker tokens
- `preprocess_text()` — The single entry point used everywhere
- `Tokenizer.encode_and_pad()` — Converts text to a fixed-length array of integers

### `ml/data.py` — Email Parser
Reads raw email files (with headers, MIME encoding, attachments) and extracts just the subject and plain-text body. Handles character encoding issues gracefully.

### `ml/train.py` — Training Pipeline
The complete training pipeline:
1. Loads raw emails from `data/raw/`
2. Deduplicates (exact hashes + near-duplicate detection)
3. Splits into train/val/test (70/15/15)
4. Trains a baseline (TF-IDF + Logistic Regression)
5. Trains the production model (Keras neural network)
6. Chooses thresholds on the validation set
7. Evaluates on the test set (touched once)
8. Exports everything to `models/v1/`

### `ml/export.py` — NumPy Forward Pass
Reimplements the neural network's forward pass using only NumPy. This is what runs in production instead of TensorFlow.

### `ml/parity.py` — Parity Gate
Verifies that the NumPy forward pass produces identical results to the Keras model. This is a critical quality gate.

### `app/create_app.py` — Flask App Factory
Creates the Flask application with security headers, rate limiting, and model loading.

### `app/routes.py` — API Endpoints
Defines the HTTP endpoints: `/api/health`, `/api/predict`, `/api/model-info`, and page routes.

### `app/services.py` — Model Service
Manages model loading (once at startup) and inference. Acts as the bridge between the API and the ML model.

### `app/signals.py` — Heuristic Signal Catalog
Rule-based pattern matching for common spam/phishing indicators. Independent from the ML model.

### `wsgi.py` — Entry Point
The file that starts everything. Used by gunicorn in production and waitress/Flask dev server locally.

---

## How Tokenization Works

Email text goes through several steps to become numbers:

```
"URGENT: Click http://evil.com now!" 
    ↓ standardize_text()
"urgent click <URL> now"
    ↓ tokenizer.encode()
[145, 89, 3, 201]        ← integer token IDs
    ↓ tokenizer.pad_sequence()
[145, 89, 3, 201, 0, 0, 0, ...]   ← padded to fixed length
```

**Why padding?** Neural networks need fixed-size inputs. Short texts are padded with zeros; long texts are truncated.

**Why special tokens?** `<URL>`, `<EMAIL>`, `<PHONE>` replace actual values so the model learns "there's a URL here" without memorizing specific URLs.

---

## How the Model Turns Text into a Score

The model has three layers:

```
[145, 89, 3, 201, 0, 0, ...]     ← Token IDs (integers)
         ↓ Embedding Layer
[[0.1, 0.3, ...],                  ← Each token becomes a vector
 [0.4, 0.2, ...],                    (learned during training)
 [0.2, 0.7, ...],
 [0.5, 0.1, ...],
 [0.0, 0.0, ...], ...]            ← Padding vectors (ignored)
         ↓ Global Average Pooling
[0.3, 0.325, ...]                  ← Average of non-padding vectors
         ↓ Dense + ReLU
[0.8, 0.1, ...]                    ← Intermediate features
         ↓ Dense + Sigmoid
0.87                                ← Score between 0 and 1
```

**Score interpretation:** Higher = more spam-like. But it's NOT a probability — it's a model score.

---

## Why We Train with TensorFlow but Serve Without It

**Problem:** TensorFlow is ~400 MB. Our free server has 512 MB total RAM.

**Solution:** 
- **Training:** Use TensorFlow/Keras (powerful tools for building and training models)
- **Export:** Save the trained weights as NumPy arrays
- **Serving:** Reimplement the forward pass (just matrix multiplications + simple math) in pure NumPy

The `ml/parity.py` script verifies both implementations produce identical results.

---

## How Thresholds Create Three Labels

Instead of a simple spam/not-spam binary, we use three labels:

```
Score: 0.0 ←————————————————————→ 1.0
       |        |            |        |
   Not Spam  Lower      Upper     Spam
              Threshold  Threshold
       |        |            |        |
    "not_spam"  "uncertain"    "spam"
```

**Why?** Reduces false positives. If the model isn't confident, it says "uncertain" instead of guessing wrong.

Thresholds are chosen on the **validation set** (never the test set) to minimize false positives on legitimate email.

---

## How Flask and the Frontend Communicate

```
Browser                          Server
  |                                |
  |  GET /analyze                  |
  |  ←————— HTML page ———————→   |
  |                                |
  |  User types email text         |
  |  Clicks "Analyze"             |
  |                                |
  |  POST /api/predict             |
  |  {"subject":"..","body":".."}  |
  |  ————————————————————————→    |
  |                                |
  |         Server processes:      |
  |         1. Validate input      |
  |         2. Preprocess text     |
  |         3. Run model           |
  |         4. Run heuristics      |
  |         5. Build response      |
  |                                |
  |  ←—— JSON response ————————  |
  |  {label, score, signals, ...}  |
  |                                |
  |  JavaScript updates the page   |
  |  (using textContent, not       |
  |   innerHTML, for XSS safety)   |
```

---

## How Docker and Render Deployment Work

**Docker** packages our app into a container — a self-contained environment with Python, our code, and the model weights.

```dockerfile
FROM python:3.11-slim      # Start with a small Python image
COPY requirements.txt .    # Copy dependency list
RUN pip install ...        # Install dependencies (NO TensorFlow!)
COPY app/ models/ ml/ ...  # Copy our code and model
CMD gunicorn wsgi:app ...  # Start the web server
```

**Render** runs this container on their servers:
1. You push code to GitHub
2. Render detects the push and builds the Docker image
3. Render starts the container and routes traffic to it
4. After 15 min of no traffic, Render stops the container (free tier)
5. Next request wakes it up (~1 minute cold start)

---

## Troubleshooting Table

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| `ModuleNotFoundError: flask` | Virtual environment not activated | Run `.\venv\Scripts\Activate.ps1` |
| `FileNotFoundError: models/v1/config.json` | Model not trained yet | Run `python ml/train.py` |
| `ERROR: No matching distribution for tensorflow` | Wrong Python version | Use Python 3.11; see DECISIONS.md |
| Tests fail with 503 | Model not loaded (testing=True) | Expected — tests check 503 behavior |
| `Address already in use` | Port conflict | Set `PORT=5001` in environment |
| Slow first request | Free-tier cold start | Normal — server waking up |
| `PermissionError` on venv | PowerShell execution policy | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Docker build fails | Missing .dockerignore | Ensure `.dockerignore` exists |
| Render deploy fails | Health check timeout | Check `/api/health` works locally first |
| `ImportError: tensorflow` in production | TF in requirements.txt | Verify `requirements.txt` does NOT list tensorflow |
