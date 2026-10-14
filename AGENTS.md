# AGENTS.md — SpamGuard AI Build Brief (Sections 1–3, 11)

## 1. Honesty rules
- Never claim a step passed unless you ran it and saw the output. Summarize real command output in PROGRESS.md.
- Never invent metrics, datasets, certifications, testimonials, user counts, or legal compliance.
- Never return a hardcoded or default prediction. If the model cannot run, return HTTP 503.
- Never substitute SMS or synthetic data for the email dataset. If the dataset cannot be obtained, stop at a gate, report it, and give manual download steps.
- Never fix a failing test by weakening it unless the test itself is wrong; explain why if so.
- State limitations plainly. The product never guarantees an email is safe.

## 2. Product
SpamGuard AI — "Check Suspicious Emails Before You Trust Them." A free, no-registration website where a user pastes an email subject and body and receives: a model prediction, heuristic signals, and safe next steps. Audience: students, job seekers, office workers, everyday users.

## 3. Fixed decisions (do not re-debate; record any forced deviation in DECISIONS.md)

HOSTING TARGET: Render, free Web Service, Docker runtime, Hobby workspace. Do NOT create Vercel or Netlify deployment configs (neither suits a persistent Flask service). Before relying on any limit below, verify it against Render's current docs via web search and record the date and source in DECISIONS.md.
FREE-TIER BUDGET (verify, then treat as hard constraints): 512 MB RAM, ~0.1 CPU, spin-down after ~15 min idle with ~1 minute wake time, shared monthly instance-hour allowance, no persistent disk (local files vanish on spin-down), no paid add-ons.

STACK:
- Python 3.11 (3.10/3.12 only if required). Training uses TensorFlow CPU + Keras (versions pinned after verifying install on Windows; if Windows TF install fails, document WSL2 as the fallback and tell me the exact steps).
- PRODUCTION RUNTIME MUST NOT INSTALL TENSORFLOW. Train and evaluate with Keras, then serve with a lightweight runtime: a NumPy forward pass for embedding+pooling+dense architectures, or ai-edge-litert/TFLite for conv/LSTM architectures. requirements.txt (runtime) excludes tensorflow; requirements-train.txt and requirements-dev.txt include it.
- Tokenization is a plain-Python/NumPy module (vocab JSON + standardization + tokenizer + padding) shared by training, evaluation and serving, so preprocessing is identical everywhere. The Keras model is trained on integer token IDs produced by this module.
- Parity gate: serving-runtime scores must match the Keras model on the FULL test set within 1e-4 (or documented tolerance with reason) and give identical labels. Record the result in docs/PARITY.md.
- Backend: Flask + gunicorn (1 worker, 2–4 threads, request timeout), binding to the PORT env var. Waitress or Flask dev server is fine only locally on Windows.
- Frontend: HTML/CSS/vanilla JS, no build step, no CDN scripts, no inline scripts/styles (strict CSP). Render user text only via textContent.
- No database. Store nothing about submitted messages. Feedback = mailto link plus GitHub Issues link.
- Rate limiting: Flask-Limiter with in-memory storage (single worker). Document that counters reset on restart/spin-down and that multi-instance needs Redis.
- Security headers via Flask-Talisman or equivalent: CSP default-src 'self', HSTS in production, X-Content-Type-Options, Referrer-Policy, frame-ancestors none. ProxyFix configured for Render's proxy (verify the correct hop count from docs and test it).
- Repo layout: app/ (routes, services, static/, templates/), ml/ (data, tokenizer, train, evaluate, export, parity), models/ (versioned artifacts + model_card.md), tests/, scripts/, docs/, Dockerfile, .dockerignore, requirements.txt, requirements-train.txt, requirements-dev.txt, .env.example, .gitignore, render.yaml, .github/workflows/ci.yml, README.md, LEARNING_GUIDE.md, DEPLOYMENT.md, AGENTS.md, PROGRESS.md, DECISIONS.md.

## 11. Definition of done (all evidenced)
1. pytest and ruff pass; output summarized in PROGRESS.md.
2. models/<version>/ loads in a fresh process; parity gate passes; metrics.json and model_card.md exist and match what the site displays.
3. Docker image passes the container smoke test under --memory=512m --cpus=0.1, or the gate (d) outcome is documented.
4. No message content in logs or storage (a test proves it).
5. Public HTTPS URL passes scripts/smoke_test.py, and a real prediction works from a fresh browser session, including after a cold start.
6. All limitations are documented; no unverified claims appear in the UI or docs.
If any item is unmet, say exactly which and why; do not declare the project complete.
