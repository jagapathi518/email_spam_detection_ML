# DECISIONS.md — SpamGuard AI

## Decision Log

### D1: Python Version — Use 3.14 instead of 3.11
- **Decision:** Use Python 3.14.6 (the only version available on the system) instead of Python 3.11
- **Alternatives:** Install Python 3.11 via winget (requires accepting MS Store terms interactively), use pyenv-win
- **Reason:** Brief says "Python 3.11 (3.10/3.12 only if required)". Only Python 3.14 is installed. TensorFlow 2.22.0rc0 is available for Python 3.14 on Windows. Installing a second Python version adds complexity and requires interactive input. Production runtime doesn't use TF anyway (NumPy forward pass), so Python 3.14 is fine for serving. Forced deviation recorded as required by brief.

### D2: Render Free-Tier Limits Verified
- **Decision:** Use the following as hard constraints: 512 MB RAM, 0.1 CPU shared, 750 instance-hours/month, 15-min idle spin-down, ~1-min cold start, 5 GB bandwidth/month, ephemeral filesystem
- **Alternatives:** N/A
- **Reason:** Verified via web search on 2026-10-13. Sources: render.com docs, livemy.app, codecapsules.io, freetier.co. Matches brief's stated constraints.

### D3: GitHub Repository URL
- **Decision:** Configured repository URL as `https://github.com/jagapathi518/email_spam_detection_ML`
- **Reason:** User provided their GitHub repository URL.

