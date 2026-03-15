# Chunk: docs/chunks/leader_board_user_config - Board user config and defaults
"""Board configuration: per-swarm server bindings and default swarm.

Config file: ~/.ve/board.toml

Structure:
    default_swarm = "abc123..."

    [swarms.abc123]
    server_url = "wss://board.example.com"

    [swarms.def456]
    server_url = "ws://localhost:8374"
"""

from __future__ import annotations

import os
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w

DEFAULT_CONFIG_PATH = Path.home() / ".ve" / "board.toml"
DEFAULT_SERVER_URL = "ws://localhost:8374"


@dataclass
class SwarmConfig:
    server_url: str


@dataclass
class BoardConfig:
    default_swarm: str | None = None
    swarms: dict[str, SwarmConfig] = field(default_factory=dict)


def load_board_config(config_path: Path | None = None) -> BoardConfig:
    """Read ~/.ve/board.toml and return a BoardConfig.

    Returns an empty config if the file does not exist.
    """
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return BoardConfig()

    with open(path, "rb") as f:
        data = tomllib.load(f)

    swarms: dict[str, SwarmConfig] = {}
    for swarm_id, swarm_data in data.get("swarms", {}).items():
        swarms[swarm_id] = SwarmConfig(server_url=swarm_data["server_url"])

    return BoardConfig(
        default_swarm=data.get("default_swarm"),
        swarms=swarms,
    )


def save_board_config(config: BoardConfig, config_path: Path | None = None) -> None:
    """Write a BoardConfig to ~/.ve/board.toml atomically."""
    path = config_path or DEFAULT_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {}
    if config.default_swarm is not None:
        data["default_swarm"] = config.default_swarm
    if config.swarms:
        data["swarms"] = {
            sid: {"server_url": sc.server_url} for sid, sc in config.swarms.items()
        }

    # Write to a temp file in the same directory, then atomic rename
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            tomli_w.dump(data, f)
        os.replace(tmp, path)
    except BaseException:
        # Clean up temp file on failure
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def add_swarm(config: BoardConfig, swarm_id: str, server_url: str) -> BoardConfig:
    """Add a swarm entry; set default_swarm if none is set yet."""
    config.swarms[swarm_id] = SwarmConfig(server_url=server_url)
    if config.default_swarm is None:
        config.default_swarm = swarm_id
    return config


def resolve_swarm(config: BoardConfig, explicit: str | None) -> str | None:
    """Return explicit swarm if provided, else default_swarm, else None."""
    if explicit is not None:
        return explicit
    return config.default_swarm


def resolve_server(
    config: BoardConfig, swarm_id: str | None, explicit: str | None
) -> str:
    """Return explicit server if provided, else the swarm's server_url, else fallback."""
    if explicit is not None:
        return explicit
    if swarm_id is not None and swarm_id in config.swarms:
        return config.swarms[swarm_id].server_url
    return DEFAULT_SERVER_URL
