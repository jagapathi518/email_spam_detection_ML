FROM python:3.11-slim AS base

# Security: run as non-root
RUN groupadd -r spamguard && useradd -r -g spamguard -d /app -s /sbin/nologin spamguard

WORKDIR /app

# Install production dependencies only (NO TensorFlow)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY ml/__init__.py ml/__init__.py
COPY ml/tokenizer.py ml/tokenizer.py
COPY ml/export.py ml/export.py
COPY wsgi.py .

# Copy model artifacts (baked in)
COPY models/ models/

# Set ownership
RUN chown -R spamguard:spamguard /app

# Switch to non-root user
USER spamguard

# Environment
ENV FLASK_ENV=production
ENV PORT=10000
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 10000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/api/health')" || exit 1

# Start gunicorn: 1 worker, 2 threads, 120s timeout, bind to PORT
CMD ["sh", "-c", "gunicorn wsgi:app --bind 0.0.0.0:${PORT} --workers 1 --threads 2 --timeout 120 --access-logfile - --error-logfile -"]
