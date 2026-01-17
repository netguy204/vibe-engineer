# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""WebSocket support for real-time dashboard updates.

Provides a ConnectionManager for tracking active WebSocket connections
and broadcasting state updates to all connected clients.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for broadcasting state updates.

    Tracks active connections and provides methods to broadcast messages
    to all connected clients. Thread-safe for use with asyncio.
    """

    def __init__(self):
        """Initialize the connection manager."""
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection and add it to the active set.

        Args:
            websocket: The WebSocket connection to add
        """
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.debug(f"WebSocket connected, total connections: {len(self._connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the active set.

        Args:
            websocket: The WebSocket connection to remove
        """
        async with self._lock:
            self._connections.discard(websocket)
        logger.debug(f"WebSocket disconnected, total connections: {len(self._connections)}")

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients.

        Sends the message as JSON to all active connections. Connections
        that fail to receive the message are removed from the active set.

        Args:
            message: The message dict to broadcast
        """
        if not self._connections:
            return

        # Add timestamp to all messages
        message["timestamp"] = datetime.now(timezone.utc).isoformat()

        json_message = json.dumps(message)

        # Create a copy of connections to iterate over
        async with self._lock:
            connections = set(self._connections)

        # Send to all connections, tracking failures
        failed_connections: list[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_text(json_message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                failed_connections.append(connection)

        # Remove failed connections
        if failed_connections:
            async with self._lock:
                for conn in failed_connections:
                    self._connections.discard(conn)

    @property
    def connection_count(self) -> int:
        """Return the number of active connections."""
        return len(self._connections)


# Global connection manager instance
_manager: Optional[ConnectionManager] = None


def get_manager() -> ConnectionManager:
    """Get or create the global connection manager.

    Returns:
        The global ConnectionManager instance
    """
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


async def broadcast_state_update(
    event_type: str,
    data: dict[str, Any],
) -> None:
    """Broadcast a state update to all connected dashboard clients.

    Helper function that wraps the broadcast in a standard message format.

    Args:
        event_type: Type of event (e.g., "status_change", "attention_update")
        data: Event-specific data to include in the message
    """
    manager = get_manager()
    await manager.broadcast({
        "type": event_type,
        "data": data,
    })


async def broadcast_work_unit_update(
    chunk: str,
    status: str,
    phase: str,
    attention_reason: Optional[str] = None,
) -> None:
    """Broadcast a work unit status change.

    Args:
        chunk: The chunk name
        status: The new status value
        phase: The current phase value
        attention_reason: Reason for NEEDS_ATTENTION status, if applicable
    """
    await broadcast_state_update("work_unit_update", {
        "chunk": chunk,
        "status": status,
        "phase": phase,
        "attention_reason": attention_reason,
    })


async def broadcast_attention_update(
    action: str,
    chunk: str,
    attention_reason: Optional[str] = None,
) -> None:
    """Broadcast an attention queue change.

    Args:
        action: "added" or "resolved"
        chunk: The chunk name
        attention_reason: Reason for attention, if adding
    """
    await broadcast_state_update("attention_update", {
        "action": action,
        "chunk": chunk,
        "attention_reason": attention_reason,
    })
