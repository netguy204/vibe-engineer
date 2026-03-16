# Chunk: docs/chunks/leader_board_local_server - Local WebSocket server adapter
"""Wire protocol frame parsing and serialization.

Defines typed dataclasses for every frame in the leader board wire protocol
(JSON over WebSocket). This module is shared between the local server adapter
and the Durable Objects adapter — both speak the same wire format.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Union


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InvalidFrameError(Exception):
    """Raised when a frame cannot be parsed (malformed JSON, unknown type, missing fields)."""

    pass


# ---------------------------------------------------------------------------
# Client → Server frames
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthFrame:
    """Client response to a challenge (existing swarm)."""

    swarm: str
    signature: str  # hex-encoded Ed25519 signature


@dataclass(frozen=True)
class RegisterSwarmFrame:
    """Client request to register a new swarm."""

    swarm: str
    public_key: str  # hex-encoded Ed25519 public key


@dataclass(frozen=True)
class WatchFrame:
    """Subscribe to a channel starting after a cursor position."""

    channel: str
    swarm: str
    cursor: int


@dataclass(frozen=True)
class SendFrame:
    """Append an encrypted message to a channel."""

    channel: str
    swarm: str
    body: str  # base64-encoded ciphertext


@dataclass(frozen=True)
class ChannelsFrame:
    """List all channels in a swarm."""

    swarm: str


@dataclass(frozen=True)
class SwarmInfoFrame:
    """Retrieve metadata about a swarm."""

    swarm: str


ClientFrame = Union[
    AuthFrame, RegisterSwarmFrame, WatchFrame, SendFrame, ChannelsFrame, SwarmInfoFrame
]


# ---------------------------------------------------------------------------
# Server → Client frames
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChallengeFrame:
    """Server challenge sent on connection open."""

    nonce: str  # hex-encoded 32-byte nonce


@dataclass(frozen=True)
class AuthOkFrame:
    """Server confirmation of successful authentication."""

    pass


@dataclass(frozen=True)
class MessageFrame:
    """A single message delivered in response to a watch."""

    channel: str
    position: int
    body: str  # base64-encoded ciphertext
    sent_at: str  # ISO 8601 UTC


@dataclass(frozen=True)
class AckFrame:
    """Confirmation that a send was appended."""

    channel: str
    position: int


@dataclass(frozen=True)
class ChannelsListFrame:
    """Response listing all channels in a swarm."""

    channels: list[dict]  # [{"name": ..., "head_position": ..., "oldest_position": ...}]


@dataclass(frozen=True)
class SwarmInfoResponseFrame:
    """Response with swarm metadata."""

    swarm: str
    created_at: str  # ISO 8601 UTC


@dataclass(frozen=True)
class PingFrame:
    """Server keepalive ping. Clients should ignore this frame."""

    pass


@dataclass(frozen=True)
class ErrorFrame:
    """Error response."""

    code: str
    message: str
    # Optional additional fields depending on error code
    earliest_position: int | None = None


ServerFrame = Union[
    ChallengeFrame,
    AuthOkFrame,
    MessageFrame,
    AckFrame,
    ChannelsListFrame,
    SwarmInfoResponseFrame,
    PingFrame,
    ErrorFrame,
]


# ---------------------------------------------------------------------------
# Parsing (JSON string → ClientFrame)
# ---------------------------------------------------------------------------

_CLIENT_FRAME_REQUIRED_FIELDS: dict[str, list[str]] = {
    "auth": ["swarm", "signature"],
    "register_swarm": ["swarm", "public_key"],
    "watch": ["channel", "swarm", "cursor"],
    "send": ["channel", "swarm", "body"],
    "channels": ["swarm"],
    "swarm_info": ["swarm"],
}


def parse_client_frame(data: str) -> ClientFrame:
    """Parse a JSON string into a typed client frame.

    Raises :class:`InvalidFrameError` for malformed JSON, unknown frame types,
    or missing required fields.
    """
    try:
        obj = json.loads(data)
    except (json.JSONDecodeError, TypeError) as exc:
        raise InvalidFrameError(f"Malformed JSON: {exc}") from exc

    if not isinstance(obj, dict):
        raise InvalidFrameError("Frame must be a JSON object")

    frame_type = obj.get("type")
    if frame_type is None:
        raise InvalidFrameError("Missing 'type' field")

    required = _CLIENT_FRAME_REQUIRED_FIELDS.get(frame_type)
    if required is None:
        raise InvalidFrameError(f"Unknown frame type: {frame_type!r}")

    for field in required:
        if field not in obj:
            raise InvalidFrameError(
                f"Missing required field {field!r} for frame type {frame_type!r}"
            )

    if frame_type == "auth":
        return AuthFrame(swarm=obj["swarm"], signature=obj["signature"])
    elif frame_type == "register_swarm":
        return RegisterSwarmFrame(swarm=obj["swarm"], public_key=obj["public_key"])
    elif frame_type == "watch":
        return WatchFrame(
            channel=obj["channel"], swarm=obj["swarm"], cursor=int(obj["cursor"])
        )
    elif frame_type == "send":
        return SendFrame(
            channel=obj["channel"], swarm=obj["swarm"], body=obj["body"]
        )
    elif frame_type == "channels":
        return ChannelsFrame(swarm=obj["swarm"])
    elif frame_type == "swarm_info":
        return SwarmInfoFrame(swarm=obj["swarm"])
    else:
        raise InvalidFrameError(f"Unknown frame type: {frame_type!r}")


# ---------------------------------------------------------------------------
# Serialization (ServerFrame → JSON string)
# ---------------------------------------------------------------------------


def serialize_server_frame(frame: ServerFrame) -> str:
    """Serialize a server frame to a JSON string."""
    if isinstance(frame, ChallengeFrame):
        obj = {"type": "challenge", "nonce": frame.nonce}
    elif isinstance(frame, AuthOkFrame):
        obj = {"type": "auth_ok"}
    elif isinstance(frame, MessageFrame):
        obj = {
            "type": "message",
            "channel": frame.channel,
            "position": frame.position,
            "body": frame.body,
            "sent_at": frame.sent_at,
        }
    elif isinstance(frame, AckFrame):
        obj = {"type": "ack", "channel": frame.channel, "position": frame.position}
    elif isinstance(frame, ChannelsListFrame):
        obj = {"type": "channels_list", "channels": frame.channels}
    elif isinstance(frame, SwarmInfoResponseFrame):
        obj = {
            "type": "swarm_info",
            "swarm": frame.swarm,
            "created_at": frame.created_at,
        }
    elif isinstance(frame, PingFrame):
        obj = {"type": "ping"}
    elif isinstance(frame, ErrorFrame):
        obj: dict = {"type": "error", "code": frame.code, "message": frame.message}
        if frame.earliest_position is not None:
            obj["earliest_position"] = frame.earliest_position
    else:
        raise TypeError(f"Unknown server frame type: {type(frame)}")

    return json.dumps(obj, separators=(",", ":"))
