# voice-controlled-home-automation-16899-17027

## VoiceProcessingBackend

How to run locally (port 3001):
1. Create a virtual environment and install dependencies:
   - cd VoiceProcessingBackend
   - python -m venv .venv && . .venv/bin/activate
   - pip install -r requirements.txt
2. Configure environment:
   - cp .env.example .env
   - Edit .env and set VOICE_API_KEY (required for protected endpoints)
3. Start the server:
   - python main.py
   - Server binds to HOST (default 0.0.0.0) and PORT (default 3001)

Health check:
- GET http://localhost:3001/ should return {"message": "Healthy"}

Protected endpoints require header:
- X-API-KEY: <value of VOICE_API_KEY>

OpenAPI docs:
- http://localhost:3001/docs
- http://localhost:3001/openapi.json