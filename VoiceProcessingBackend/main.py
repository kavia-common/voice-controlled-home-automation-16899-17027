#!/usr/bin/env python3
"""
Entrypoint script to start the Voice Processing Backend FastAPI server.

This script:
- Ensures the 'src' directory is on sys.path so package imports like 'api.main:app' work.
- Reads HOST and PORT from environment variables (default HOST=0.0.0.0, PORT=3001).
- Starts uvicorn with the FastAPI app defined in api.main.

Environment variables:
- HOST: Bind address for the server (default: 0.0.0.0)
- PORT: Port for the server (default: 3001)
- VOICE_API_KEY: Required API key for protected endpoints (header: X-API-KEY)
- DATABASE_URL: Optional database connection string
- FIRMWARE_BASE_URL: Optional base URL for firmware service
- EXTERNAL_VOICE_API_URL: Optional external voice recognition service URL
"""
import os
import sys

def _ensure_src_on_path():
    # Add ./src to sys.path to allow "import api.main"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(base_dir, "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

def _run():
    _ensure_src_on_path()
    import uvicorn  # type: ignore
    host = os.getenv("HOST", "0.0.0.0")
    try:
        port = int(os.getenv("PORT", "3001"))
    except ValueError:
        port = 3001

    # Import app after sys.path adjustment
    from api.main import app  # noqa: E402

    # Start uvicorn
    uvicorn.run(app, host=host, port=port, reload=False, access_log=True)

if __name__ == "__main__":
    _run()
