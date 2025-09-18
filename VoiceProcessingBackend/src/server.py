"""
Server launcher for the Voice Processing Backend FastAPI application.

Usage:
    python -m server
or
    python server.py

This module:
- Adds its own directory to sys.path to allow 'api.main' imports.
- Reads HOST and PORT from environment variables (default HOST=0.0.0.0, PORT=3001).
- Runs uvicorn with the FastAPI app from api.main
"""
from __future__ import annotations

import os
import sys

def _ensure_this_dir_on_path():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    if this_dir not in sys.path:
        sys.path.insert(0, this_dir)

def main() -> None:
    """Start the uvicorn server for the FastAPI app."""
    _ensure_this_dir_on_path()
    import uvicorn  # type: ignore
    from api.main import app  # noqa: E402

    host = os.getenv("HOST", "0.0.0.0")
    try:
        port = int(os.getenv("PORT", "3001"))
    except ValueError:
        port = 3001

    uvicorn.run(app, host=host, port=port, reload=False, access_log=True)

if __name__ == "__main__":
    main()
