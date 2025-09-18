import os
import logging
from typing import Dict, Optional

from fastapi import FastAPI, Depends, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field, ConfigDict

# Note on configuration:
# - Set environment variables (do not commit secrets):
#   VOICE_API_KEY: API key to secure this API (header: X-API-KEY)
#   DATABASE_URL: PostgreSQL connection string (e.g., postgresql+psycopg://user:pass@host:5432/dbname)
#   FIRMWARE_BASE_URL: Base URL to communicate with the microcontroller firmware service
#   EXTERNAL_VOICE_API_URL: Optional external voice recognition service endpoint
#
# See .env.example addition in this repository for required variables.

logger = logging.getLogger("voice-backend")
logging.basicConfig(level=logging.INFO)

# Security: API Key via Header
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


# PUBLIC_INTERFACE
def get_api_key(
    api_key: Optional[str] = Header(None, alias=API_KEY_NAME),
) -> str:
    """Retrieve and validate the API key from headers.

    Raises HTTP 401 if the key is missing or invalid.
    """
    expected = os.getenv("VOICE_API_KEY")
    if not expected:
        # If no expected key is configured, deny all requests for safety.
        logger.error("VOICE_API_KEY is not set in environment.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server security not configured",
        )
    if not api_key or api_key != expected:
        logger.warning("Unauthorized request: invalid or missing API key.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key


# Models
class VoiceCommandRequest(BaseModel):
    """Request payload for the /voice-command endpoint."""
    model_config = ConfigDict(extra="forbid")
    command: str = Field(..., description="Raw voice command text")


class DeviceStateModel(BaseModel):
    """Represents state of devices in the home."""
    model_config = ConfigDict(extra="allow")
    # Example common devices; model allows arbitrary keys for extensibility
    lights: Dict[str, bool] = Field(default_factory=dict, description="Mapping of light id to on/off")
    fans: Dict[str, int] = Field(default_factory=dict, description="Mapping of fan id to speed (0-3)")
    # Additional devices can be added as arbitrary keys due to extra="allow"


class VoiceCommandResponse(BaseModel):
    """Response for processed voice command."""
    status: str = Field(..., description="Result status, e.g., 'ok'")
    deviceState: DeviceStateModel = Field(..., description="Current device state after processing")


class DeviceStateResponse(BaseModel):
    """Response for current device state."""
    deviceState: DeviceStateModel = Field(..., description="Current device state")


# Simple in-memory device state.
# In production, this would be synchronized with DB and firmware service.
class DeviceStateService:
    """Service layer for managing device state and firmware interactions."""

    def __init__(self) -> None:
        self._state = DeviceStateModel(
            lights={"living_room": False, "bedroom": False},
            fans={"ceiling_fan": 0},
        )
        # Placeholders for integration
        self.database_url = os.getenv("DATABASE_URL", "")
        self.firmware_base_url = os.getenv("FIRMWARE_BASE_URL", "")
        self.external_voice_api_url = os.getenv("EXTERNAL_VOICE_API_URL", "")

    # PUBLIC_INTERFACE
    def get_state(self) -> DeviceStateModel:
        """Return a copy of the current device state."""
        # In production, could fetch from DB or cached layer
        return DeviceStateModel.model_validate(self._state.model_dump())

    # PUBLIC_INTERFACE
    def apply_command(self, normalized_command: str) -> DeviceStateModel:
        """Apply a normalized text command to the device state.

        Supports very basic grammar:
        - 'turn on <room> light'
        - 'turn off <room> light'
        - 'set <fan> speed to <0-3>'
        """
        tokens = normalized_command.split()
        if not tokens:
            raise ValueError("Empty command")

        try:
            if tokens[:2] == ["turn", "on"] and tokens[-1] == "light":
                # Example: "turn on living room light"
                # naive extraction: words between 'on' and 'light' make the room name
                room = " ".join(tokens[2:-1]).replace(" ", "_")
                if not room:
                    raise ValueError("No room specified for turning on light")
                self._state.lights[room] = True
                self._notify_firmware({"deviceId": f"light:{room}", "command": "on"})

            elif tokens[:2] == ["turn", "off"] and tokens[-1] == "light":
                room = " ".join(tokens[2:-1]).replace(" ", "_")
                if not room:
                    raise ValueError("No room specified for turning off light")
                self._state.lights[room] = False
                self._notify_firmware({"deviceId": f"light:{room}", "command": "off"})

            elif tokens[0] == "set" and "speed" in tokens and "to" in tokens:
                # Example: "set ceiling fan speed to 2"
                # naive parse
                try:
                    to_index = tokens.index("to")
                    speed_str = tokens[to_index + 1]
                    speed = int(speed_str)
                    if speed < 0 or speed > 3:
                        raise ValueError("Fan speed must be between 0 and 3")
                    # device name is after 'set' up to 'speed'
                    speed_index = tokens.index("speed")
                    device_name = " ".join(tokens[1:speed_index]).replace(" ", "_")
                    if not device_name:
                        raise ValueError("No fan specified for setting speed")
                    self._state.fans[device_name] = speed
                    self._notify_firmware({"deviceId": f"fan:{device_name}", "command": f"speed:{speed}"})
                except (ValueError, IndexError) as e:
                    raise ValueError(f"Invalid fan speed command: {e}")
            else:
                raise ValueError("Unsupported command")
        except Exception:
            # In a real service, we'd log to DB
            logger.exception("Failed to apply command: %s", normalized_command)
            raise
        # In a real service, persist state changes to DB here
        return self.get_state()

    def _notify_firmware(self, payload: Dict) -> None:
        """Placeholder: send command to firmware service.

        Implement HTTP call to firmware service here using self.firmware_base_url.
        For now, just log the action.
        """
        if not self.firmware_base_url:
            logger.info("Firmware notification (simulated): %s", payload)
            return
        # Example implementation (commented to avoid external call during CI):
        # try:
        #     import httpx
        #     url = f"{self.firmware_base_url.rstrip('/')}/commands"
        #     r = httpx.post(url, json=payload, timeout=3.0)
        #     r.raise_for_status()
        # except Exception:
        #     logger.exception("Firmware notification failed for payload %s", payload)

    def _log_to_db(self, entry: Dict) -> None:
        """Placeholder: log command/state change to PostgreSQL.

        Use self.database_url to connect via SQLAlchemy/asyncpg/psycopg.
        For now, just log the action.
        """
        if not self.database_url:
            logger.debug("DB log (simulated): %s", entry)
            return
        # Example pseudo-implementation:
        # from sqlalchemy import create_engine, text
        # engine = create_engine(self.database_url, future=True)
        # with engine.begin() as conn:
        #     conn.execute(text("INSERT INTO logs (event) VALUES (:e)"), {"e": json.dumps(entry)})

    # PUBLIC_INTERFACE
    def transcribe_external(self, audio_bytes: bytes) -> str:
        """Placeholder for external voice recognition API.

        Returns transcribed text from audio. Not used in current endpoints,
        but provided to support future expansion.
        """
        if not self.external_voice_api_url:
            # Simulate returning a fixed text
            return "turn on living room light"
        # Example:
        # import httpx
        # files = {"file": ("voice.wav", audio_bytes, "audio/wav")}
        # r = httpx.post(self.external_voice_api_url, files=files, timeout=10.0)
        # r.raise_for_status()
        # return r.json().get("text", "")
        return "turn on living room light"


# FastAPI app initialization with metadata and tags
app = FastAPI(
    title="Voice Processing Backend API",
    version="1.0.0",
    description=(
        "API for processing voice commands and managing device states in the "
        "Voice-Controlled Home Automation system."
    ),
    openapi_tags=[
        {
            "name": "Voice",
            "description": "Voice commands processing and recognition.",
        },
        {
            "name": "Devices",
            "description": "Device state retrieval and control endpoints.",
        },
        {
            "name": "Docs",
            "description": "API usage documentation and WebSocket notes (if any).",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state_service = DeviceStateService()


@app.get("/", summary="Health Check", tags=["Docs"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.post(
    "/voice-command",
    response_model=VoiceCommandResponse,
    summary="Submit a voice command for processing",
    tags=["Voice"],
    responses={
        200: {"description": "Command processed successfully"},
        400: {"description": "Invalid command format"},
        500: {"description": "Internal server error"},
    },
)
def post_voice_command(
    payload: VoiceCommandRequest,
    api_key: str = Depends(get_api_key),
):
    """Process a text-based voice command.

    Parameters:
    - payload: VoiceCommandRequest containing 'command' string.
    - api_key: provided via the X-API-KEY header (validated by dependency).

    Returns:
    - VoiceCommandResponse: status and the updated deviceState.

    Notes:
    - This implementation performs basic parsing. It is structured to be
      extended to integrate with an external voice recognition service.
    """
    command = (payload.command or "").strip().lower()
    if not command or len(command) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Command must be a non-empty string",
        )

    try:
        new_state = state_service.apply_command(command)
        # Simulated DB log
        try:
            state_service._log_to_db({"event": "command", "command": command, "state": new_state.model_dump()})
        except Exception:
            logger.exception("Failed to log command to DB")

        return VoiceCommandResponse(status="ok", deviceState=new_state)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except HTTPException:
        # bubble up
        raise
    except Exception:
        logger.exception("Internal error while processing command")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# PUBLIC_INTERFACE
@app.get(
    "/device-state",
    response_model=DeviceStateResponse,
    summary="Retrieve current device state",
    tags=["Devices"],
    responses={
        200: {"description": "Current device state retrieved"},
        500: {"description": "Internal server error"},
    },
)
def get_device_state(
    api_key: str = Depends(get_api_key),
):
    """Retrieve the current device state.

    Parameters:
    - api_key: provided via the X-API-KEY header (validated by dependency).

    Returns:
    - DeviceStateResponse: the current deviceState.
    """
    try:
        current = state_service.get_state()
        return DeviceStateResponse(deviceState=current)
    except Exception:
        logger.exception("Internal error while retrieving device state")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
