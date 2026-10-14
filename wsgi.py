"""
SpamGuard AI — WSGI Entry Point

This is the main entry point for gunicorn and local development.
"""

import os

from app.create_app import create_app

app = create_app()

if __name__ == "__main__":
    # Local development on Windows — use waitress or Flask dev server
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_ENV") == "development"

    try:
        from waitress import serve

        print(f"Starting Waitress server on http://{host}:{port}")
        serve(app, host=host, port=port)
    except ImportError:
        print(f"Starting Flask dev server on http://{host}:{port}")
        app.run(host=host, port=port, debug=debug)

