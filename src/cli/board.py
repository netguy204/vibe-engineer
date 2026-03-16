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
import hashlib
import secrets
import subprocess
import sys
from pathlib import Path

import click
import httpx

from board.client import BoardClient
from board.config import (
    add_swarm,
    gateway_http_url,
    load_board_config,
    resolve_server,
    resolve_swarm,
    save_board_config,
)
from leader_board.server import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_STORAGE_DIR
from board.crypto import (
    derive_swarm_id,
    derive_symmetric_key,
    derive_token_key,
    encrypt,
    decrypt,
    generate_keypair,
)
from board.storage import (
    collect_board_files,
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


# Chunk: docs/chunks/websocket_keepalive - Added --no-reconnect flag
@board.command("watch")
@click.argument("channel")
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
@click.option("--project-root", type=click.Path(exists=True, path_type=Path), default=".", help="Project root for cursor storage")
@click.option("--no-reconnect", is_flag=True, help="Disable automatic reconnect on disconnect")
def watch_cmd(channel: str, swarm: str | None, server: str | None, project_root: Path, no_reconnect: bool) -> None:
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
            if no_reconnect:
                msg = await client.watch(channel, cursor)
            else:
                msg = await client.watch_with_reconnect(channel, cursor)
            plaintext = decrypt(msg["body"], sym_key)
            click.echo(plaintext)
        finally:
            await client.close()

    asyncio.run(_watch())


# ---------------------------------------------------------------------------
# watch-multi
# Chunk: docs/chunks/multichannel_watch - Multi-channel watch CLI command
# ---------------------------------------------------------------------------


@board.command("watch-multi")
@click.argument("channels", nargs=-1, required=True)
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
@click.option("--project-root", type=click.Path(exists=True, path_type=Path), default=".", help="Project root for cursor storage")
@click.option("--no-reconnect", is_flag=True, help="Disable automatic reconnect on disconnect")
# Chunk: docs/chunks/watchmulti_exit_on_message - --count flag for event-driven workflows
@click.option("--count", default=1, type=int, help="Exit after N messages (0 = stream indefinitely)")
# Chunk: docs/chunks/watchmulti_manual_ack - Manual ack mode
@click.option("--no-auto-ack", is_flag=True, help="Don't auto-advance cursor; include position in output for manual acking")
def watch_multi_cmd(channels: tuple[str, ...], swarm: str | None, server: str | None, project_root: Path, no_reconnect: bool, count: int, no_auto_ack: bool) -> None:
    """Watch multiple channels on a single connection.

    Blocks and prints messages from any subscribed channel.
    Output format: [channel-name] message text

    With --count N (default 1), exits after receiving N messages. Use
    --count 0 to stream indefinitely.

    With --no-auto-ack, cursors are NOT auto-advanced and the output
    includes position for manual acking via 've board ack'.
    Output format: [channel-name] position=N message text
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

    # Load per-channel cursors
    channel_cursors = {}
    for ch in channels:
        channel_cursors[ch] = load_cursor(ch, project_root)

    async def _watch_multi():
        client = BoardClient(server, swarm, seed)
        await client.connect()
        try:
            auto_ack = not no_auto_ack
            if no_reconnect:
                gen = client.watch_multi(channel_cursors, count=count, auto_ack=auto_ack)
            else:
                gen = client.watch_multi_with_reconnect(channel_cursors, count=count, auto_ack=auto_ack)

            async for msg in gen:
                plaintext = decrypt(msg["body"], sym_key)
                if no_auto_ack:
                    click.echo(f"[{msg['channel']}] position={msg['position']} {plaintext}")
                else:
                    click.echo(f"[{msg['channel']}] {plaintext}")
                    # Auto-advance cursor
                    save_cursor(msg["channel"], msg["position"], project_root)
        except KeyboardInterrupt:
            pass
        finally:
            await client.close()

    try:
        asyncio.run(_watch_multi())
    except KeyboardInterrupt:
        pass


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


# ---------------------------------------------------------------------------
# scp
# ---------------------------------------------------------------------------


# Chunk: docs/chunks/board_scp_command - Board SCP command
@board.command("scp")
@click.argument("host")
def scp_cmd(host: str) -> None:
    """Copy board config and swarm keys to a remote host via SCP.

    Copies ~/.ve/board.toml and all key material from ~/.ve/keys/ to
    the same paths under ~/.ve/ on the remote HOST.
    """
    try:
        files = collect_board_files()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    # Group files by their parent directory to preserve remote layout.
    # board.toml → <host>:~/.ve/
    # keys/*.key, keys/*.pub → <host>:~/.ve/keys/
    home_ve = Path.home() / ".ve"

    # Ensure remote directories exist
    keys_files = [f for f in files if f.parent.name == "keys"]
    if keys_files:
        try:
            subprocess.run(
                ["ssh", host, "mkdir", "-p", "~/.ve/keys"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            click.echo(f"Error: SSH to '{host}' failed: {exc.stderr.strip()}", err=True)
            sys.exit(1)

    # SCP board.toml
    config_files = [f for f in files if f.name == "board.toml"]
    if config_files:
        try:
            subprocess.run(
                ["scp", *[str(f) for f in config_files], f"{host}:~/.ve/"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            click.echo(f"Error: SCP to '{host}' failed: {exc.stderr.strip()}", err=True)
            sys.exit(1)

    # SCP key files
    if keys_files:
        try:
            subprocess.run(
                ["scp", *[str(f) for f in keys_files], f"{host}:~/.ve/keys/"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            click.echo(f"Error: SCP to '{host}' failed: {exc.stderr.strip()}", err=True)
            sys.exit(1)

    file_count = len(files)
    click.echo(f"Copied {file_count} file(s) to {host}:~/.ve/")


# ---------------------------------------------------------------------------
# invite
# ---------------------------------------------------------------------------


_INVITE_WARNING = """\
WARNING: Creating an invite link enables cleartext gateway access to this swarm.

The cleartext gateway trades end-to-end encryption for agent accessibility.
Any agent with the invite URL can read and write messages in plaintext via
the gateway, without needing the swarm's private key locally.

The invite token is the sole security boundary — treat it like a password.
"""


# Chunk: docs/chunks/invite_cli_command
# Chunk: docs/chunks/invite_list_revoke - Restructured invite from command to group
@board.group()
def invite():
    """Invite management commands."""
    pass


@invite.command("create")
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def invite_create_cmd(swarm: str | None, server: str | None, yes: bool) -> None:
    """Generate an invite link for agent access to a swarm."""
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

    # Display warning and prompt for confirmation
    click.echo(_INVITE_WARNING)
    if not yes:
        if not click.confirm("Do you want to continue?"):
            click.echo("Aborted.")
            return

    # Generate token and derive encryption key
    token = secrets.token_bytes(32)
    sym_key = derive_token_key(token)

    # Encrypt the seed (as hex string for lossless round-trip)
    encrypted_blob = encrypt(seed.hex(), sym_key)

    # Compute token hash for server-side indexing
    token_hash = hashlib.sha256(token).hexdigest()

    # Upload to gateway
    http_url = gateway_http_url(server)
    response = httpx.put(
        f"{http_url}/gateway/keys",
        params={"swarm": swarm},
        json={"token_hash": token_hash, "encrypted_blob": encrypted_blob},
    )

    if response.status_code != 200:
        click.echo(f"Error: server returned {response.status_code}", err=True)
        sys.exit(1)

    invite_url = f"{http_url}/invite/{token.hex()}"
    click.echo(invite_url)


# Chunk: docs/chunks/invite_list_revoke - List active invite tokens
@invite.command("list")
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
def invite_list_cmd(swarm: str | None, server: str | None) -> None:
    """List all active invite tokens for a swarm."""
    config = load_board_config()
    swarm = resolve_swarm(config, swarm)
    if swarm is None:
        click.echo("Error: no swarm specified and no default_swarm in ~/.ve/board.toml", err=True)
        sys.exit(1)
    server = resolve_server(config, swarm, server)

    http_url = gateway_http_url(server)
    response = httpx.get(
        f"{http_url}/gateway/keys",
        params={"swarm": swarm},
    )

    if response.status_code != 200:
        click.echo(f"Error: server returned {response.status_code}", err=True)
        sys.exit(1)

    data = response.json()
    keys = data.get("keys", [])
    if not keys:
        click.echo("No active invite tokens.")
        return

    for key in keys:
        hint = key.get("hint", key["token_hash"][:8])
        created = key.get("created_at", "unknown")
        click.echo(f"{hint}  created={created}")


# ---------------------------------------------------------------------------
# revoke (subcommand of invite)
# ---------------------------------------------------------------------------


# Chunk: docs/chunks/invite_cli_command
# Chunk: docs/chunks/invite_list_revoke - Added --all flag for bulk revocation
# Chunk: docs/chunks/invite_revoke_subcommand - Moved from board to invite group
@invite.command("revoke")
@click.argument("token", required=False, default=None)
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
@click.option("--all", "revoke_all", is_flag=True, help="Revoke all tokens for this swarm")
def revoke_cmd(token: str | None, swarm: str | None, server: str | None, revoke_all: bool) -> None:
    """Revoke an invite token, immediately invalidating access."""
    if not revoke_all and token is None:
        click.echo("Error: provide a TOKEN argument or use --all", err=True)
        sys.exit(1)

    config = load_board_config()
    swarm = resolve_swarm(config, swarm)
    if swarm is None:
        click.echo("Error: no swarm specified and no default_swarm in ~/.ve/board.toml", err=True)
        sys.exit(1)
    server = resolve_server(config, swarm, server)

    http_url = gateway_http_url(server)

    if revoke_all:
        response = httpx.delete(
            f"{http_url}/gateway/keys",
            params={"swarm": swarm},
        )
        if response.status_code == 200:
            data = response.json()
            count = data.get("deleted", 0)
            click.echo(f"Revoked {count} invite token(s).")
        else:
            click.echo(f"Error: server returned {response.status_code}", err=True)
            sys.exit(1)
    else:
        # Resolve token argument: could be a full raw token (32 bytes = 64 hex chars)
        # or a hint prefix (first 8 chars of the token_hash shown by 'invite list').
        if len(token) == 64:
            # Full raw token — hash it to get the server-side key
            token_bytes = bytes.fromhex(token)
            token_hash = hashlib.sha256(token_bytes).hexdigest()
        else:
            # Hint prefix — look up the full token_hash from the server
            list_response = httpx.get(
                f"{http_url}/gateway/keys",
                params={"swarm": swarm},
            )
            if list_response.status_code != 200:
                click.echo(f"Error: server returned {list_response.status_code}", err=True)
                sys.exit(1)

            keys = list_response.json().get("keys", [])
            matches = [
                k for k in keys
                if k["token_hash"].startswith(token)
                or k.get("hint", k["token_hash"][:8]) == token
            ]

            if len(matches) == 0:
                click.echo("Error: token not found or already revoked.", err=True)
                sys.exit(1)
            elif len(matches) > 1:
                click.echo("Error: ambiguous prefix — matches multiple tokens. Provide more characters.", err=True)
                sys.exit(1)

            token_hash = matches[0]["token_hash"]

        response = httpx.delete(
            f"{http_url}/gateway/keys/{token_hash}",
            params={"swarm": swarm},
        )

        if response.status_code == 200:
            click.echo("Invite revoked successfully.")
        elif response.status_code == 404:
            click.echo("Error: token not found or already revoked.", err=True)
            sys.exit(1)
        else:
            click.echo(f"Error: server returned {response.status_code}", err=True)
            sys.exit(1)


# ---------------------------------------------------------------------------
# deprecated alias: ve board revoke → ve board invite revoke
# ---------------------------------------------------------------------------


# Chunk: docs/chunks/invite_revoke_subcommand - Deprecated alias for old location
@board.command("revoke")
@click.argument("token", required=False, default=None)
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
@click.option("--all", "revoke_all", is_flag=True, help="Revoke all tokens for this swarm")
@click.pass_context
def revoke_deprecated(ctx, token: str | None, swarm: str | None, server: str | None, revoke_all: bool) -> None:
    """Revoke an invite token (deprecated — use 've board invite revoke')."""
    click.echo("Warning: 've board revoke' is deprecated. Use 've board invite revoke' instead.", err=True)
    ctx.invoke(revoke_cmd, token=token, swarm=swarm, server=server, revoke_all=revoke_all)
