# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
# Chunk: docs/chunks/leader_board_user_config - Board user config and defaults
"""CLI commands for Leader Board messaging.

Subcommands:
  start         — start the local WebSocket server
  swarm create  — generate key pair and register with server
  send          — encrypt and send a message to a channel
  watch         — block until next message, decrypt, print to stdout
  ack           — advance persisted cursor
  channels      — list channels in a swarm
  bind          — update swarm server binding or default swarm
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click

from board.client import BoardClient
from board.config import (
    add_swarm,
    load_board_config,
    resolve_server,
    resolve_swarm,
    save_board_config,
)
from leader_board.server import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_STORAGE_DIR
from board.crypto import (
    derive_swarm_id,
    derive_symmetric_key,
    encrypt,
    decrypt,
    generate_keypair,
)
from board.storage import (
    list_swarms,
    load_cursor,
    load_keypair,
    save_cursor,
    save_keypair,
)


@click.group()
def board():
    """Leader board messaging commands."""
    pass


# ---------------------------------------------------------------------------
# swarm subgroup
# ---------------------------------------------------------------------------


@board.command("start")
@click.option("--host", default=DEFAULT_HOST, show_default=True, help="Bind address")
@click.option("--port", type=int, default=DEFAULT_PORT, show_default=True, help="Bind port")
@click.option(
    "--storage-dir",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Storage directory (default: {DEFAULT_STORAGE_DIR})",
)
def start_cmd(host: str, port: int, storage_dir: Path | None) -> None:
    """Start the local leader board WebSocket server."""
    from leader_board.server import run_server

    run_server(storage_dir=storage_dir, host=host, port=port)


@board.group()
def swarm():
    """Swarm management commands."""
    pass


@swarm.command("create")
@click.option("--server", default=None, help="Server URL")
def swarm_create(server: str | None) -> None:
    """Generate a new swarm key pair and register with the server."""
    config = load_board_config()
    # For swarm create, resolve server without a swarm ID (no swarm exists yet)
    resolved_server = resolve_server(config, None, server)

    seed, public_key = generate_keypair()
    swarm_id = derive_swarm_id(public_key)

    # Register with server
    async def _register():
        client = BoardClient(resolved_server, swarm_id, seed)
        await client.register_swarm(public_key)

    asyncio.run(_register())

    # Persist keys (operator-global)
    save_keypair(swarm_id, seed, public_key)

    # Update board.toml with the new swarm entry
    add_swarm(config, swarm_id, resolved_server)
    save_board_config(config)

    click.echo(swarm_id)


# ---------------------------------------------------------------------------
# bind
# ---------------------------------------------------------------------------


@board.command("bind")
@click.argument("swarm_id", required=False, default=None)
@click.argument("url", required=False, default=None)
@click.option("--default", "set_default", default=None, metavar="SWARM", help="Set the default swarm")
def bind_cmd(swarm_id: str | None, url: str | None, set_default: str | None) -> None:
    """Update swarm server binding or default swarm.

    \b
    ve board bind <swarm> <url>      — update server URL for a swarm
    ve board bind --default <swarm>  — set the default swarm
    """
    if swarm_id is None and set_default is None:
        click.echo("Usage: ve board bind <swarm> <url>  or  ve board bind --default <swarm>", err=True)
        sys.exit(1)

    config = load_board_config()

    if set_default is not None:
        if set_default not in config.swarms:
            click.echo(f"Error: swarm '{set_default}' not found in config.", err=True)
            sys.exit(1)
        config.default_swarm = set_default
        save_board_config(config)
        click.echo(f"Default swarm set to '{set_default}'")
        return

    # swarm_id + url mode
    if url is None:
        click.echo("Usage: ve board bind <swarm> <url>", err=True)
        sys.exit(1)

    if swarm_id not in config.swarms:
        click.echo(f"Error: swarm '{swarm_id}' not found in config.", err=True)
        sys.exit(1)

    config.swarms[swarm_id].server_url = url
    save_board_config(config)
    click.echo(f"Swarm '{swarm_id}' bound to {url}")


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------


@board.command("send")
@click.argument("channel")
@click.argument("body")
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
def send_cmd(channel: str, body: str, swarm: str | None, server: str | None) -> None:
    """Encrypt and send a message to a channel."""
    config = load_board_config()
    swarm = resolve_swarm(config, swarm)
    if swarm is None:
        click.echo("Error: no swarm specified and no default_swarm in ~/.ve/board.toml", err=True)
        sys.exit(1)
    server = resolve_server(config, swarm, server)

    keypair = load_keypair(swarm)
    if keypair is None:
        click.echo(f"Error: swarm '{swarm}' not found. Run 've board swarm create' first.", err=True)
        sys.exit(1)

    seed, _pub = keypair
    sym_key = derive_symmetric_key(seed)
    ciphertext = encrypt(body, sym_key)

    async def _send():
        client = BoardClient(server, swarm, seed)
        await client.connect()
        try:
            position = await client.send(channel, ciphertext)
            click.echo(f"{position}")
        finally:
            await client.close()

    asyncio.run(_send())


# ---------------------------------------------------------------------------
# watch
# ---------------------------------------------------------------------------


@board.command("watch")
@click.argument("channel")
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
@click.option("--project-root", type=click.Path(exists=True, path_type=Path), default=".", help="Project root for cursor storage")
def watch_cmd(channel: str, swarm: str | None, server: str | None, project_root: Path) -> None:
    """Watch a channel for the next message after the persisted cursor.

    Blocks until a message exists, decrypts the body, prints plaintext to
    stdout, then exits. The cursor is NOT auto-advanced — use 'ack' after
    durable processing.
    """
    config = load_board_config()
    swarm = resolve_swarm(config, swarm)
    if swarm is None:
        click.echo("Error: no swarm specified and no default_swarm in ~/.ve/board.toml", err=True)
        sys.exit(1)
    server = resolve_server(config, swarm, server)

    keypair = load_keypair(swarm)
    if keypair is None:
        click.echo(f"Error: swarm '{swarm}' not found.", err=True)
        sys.exit(1)

    seed, _pub = keypair
    sym_key = derive_symmetric_key(seed)
    cursor = load_cursor(channel, project_root)

    async def _watch():
        client = BoardClient(server, swarm, seed)
        await client.connect()
        try:
            msg = await client.watch(channel, cursor)
            plaintext = decrypt(msg["body"], sym_key)
            click.echo(plaintext)
        finally:
            await client.close()

    asyncio.run(_watch())


# ---------------------------------------------------------------------------
# ack
# ---------------------------------------------------------------------------


@board.command("ack")
@click.argument("channel")
@click.argument("position", type=int)
@click.option("--project-root", type=click.Path(exists=True, path_type=Path), default=".", help="Project root for cursor storage")
def ack_cmd(channel: str, position: int, project_root: Path) -> None:
    """Advance the persisted cursor for a channel."""
    save_cursor(channel, position, project_root)
    click.echo(f"Cursor for '{channel}' advanced to {position}")


# ---------------------------------------------------------------------------
# channels
# ---------------------------------------------------------------------------


@board.command("channels")
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
def channels_cmd(swarm: str | None, server: str | None) -> None:
    """List channels in a swarm."""
    config = load_board_config()
    swarm = resolve_swarm(config, swarm)
    if swarm is None:
        click.echo("Error: no swarm specified and no default_swarm in ~/.ve/board.toml", err=True)
        sys.exit(1)
    server = resolve_server(config, swarm, server)

    keypair = load_keypair(swarm)
    if keypair is None:
        click.echo(f"Error: swarm '{swarm}' not found.", err=True)
        sys.exit(1)

    seed, _pub = keypair

    async def _channels():
        client = BoardClient(server, swarm, seed)
        await client.connect()
        try:
            channels = await client.list_channels()
            if not channels:
                click.echo("No channels.")
                return
            for ch in channels:
                click.echo(f"{ch['name']}  head={ch['head_position']}  oldest={ch['oldest_position']}")
        finally:
            await client.close()

    asyncio.run(_channels())
