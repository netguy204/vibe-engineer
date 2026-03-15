# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
"""CLI commands for Leader Board messaging.

Subcommands:
  swarm create  — generate key pair and register with server
  send          — encrypt and send a message to a channel
  watch         — block until next message, decrypt, print to stdout
  ack           — advance persisted cursor
  channels      — list channels in a swarm
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click

from board.client import BoardClient
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


@board.group()
def swarm():
    """Swarm management commands."""
    pass


@swarm.command("create")
@click.option("--server", default="ws://localhost:8787", help="Server URL")
def swarm_create(server: str) -> None:
    """Generate a new swarm key pair and register with the server."""
    seed, public_key = generate_keypair()
    swarm_id = derive_swarm_id(public_key)

    # Register with server
    async def _register():
        client = BoardClient(server, swarm_id, seed)
        await client.register_swarm(public_key)

    asyncio.run(_register())

    # Persist keys (operator-global)
    save_keypair(swarm_id, seed, public_key)
    click.echo(swarm_id)


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------


@board.command("send")
@click.argument("channel")
@click.argument("body")
@click.option("--swarm", required=True, help="Swarm ID")
@click.option("--server", default="ws://localhost:8787", help="Server URL")
def send_cmd(channel: str, body: str, swarm: str, server: str) -> None:
    """Encrypt and send a message to a channel."""
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
@click.option("--swarm", required=True, help="Swarm ID")
@click.option("--server", default="ws://localhost:8787", help="Server URL")
@click.option("--project-root", type=click.Path(exists=True, path_type=Path), default=".", help="Project root for cursor storage")
def watch_cmd(channel: str, swarm: str, server: str, project_root: Path) -> None:
    """Watch a channel for the next message after the persisted cursor.

    Blocks until a message exists, decrypts the body, prints plaintext to
    stdout, then exits. The cursor is NOT auto-advanced — use 'ack' after
    durable processing.
    """
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
@click.option("--swarm", required=True, help="Swarm ID")
@click.option("--server", default="ws://localhost:8787", help="Server URL")
def channels_cmd(swarm: str, server: str) -> None:
    """List channels in a swarm."""
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
