# Chunk: docs/chunks/orch_foundation - Orchestrator daemon foundation
# Chunk: docs/chunks/orch_scheduling - Scheduler integration
"""Daemon process management for the orchestrator.

Handles starting, stopping, and monitoring the orchestrator daemon process.
Uses standard Unix daemonization (double-fork) to detach from terminal.
"""

import asyncio
import atexit
import fcntl
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import uvicorn

from orchestrator.models import OrchestratorConfig, OrchestratorState
from orchestrator.state import StateStore, get_default_db_path


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class DaemonError(Exception):
    """Exception raised for daemon-related errors."""

    pass


def get_pid_path(project_dir: Path) -> Path:
    """Get the PID file path for a project.

    Args:
        project_dir: The project directory

    Returns:
        Path to the PID file
    """
    return project_dir / ".ve" / "orchestrator.pid"


def get_socket_path(project_dir: Path) -> Path:
    """Get the Unix socket path for a project.

    Args:
        project_dir: The project directory

    Returns:
        Path to the Unix socket
    """
    return project_dir / ".ve" / "orchestrator.sock"


def get_log_path(project_dir: Path) -> Path:
    """Get the log file path for a project.

    Args:
        project_dir: The project directory

    Returns:
        Path to the log file
    """
    return project_dir / ".ve" / "orchestrator.log"


def read_pid_file(pid_path: Path) -> Optional[int]:
    """Read the PID from the PID file.

    Args:
        pid_path: Path to the PID file

    Returns:
        The PID if file exists and is valid, None otherwise
    """
    if not pid_path.exists():
        return None

    try:
        content = pid_path.read_text().strip()
        return int(content)
    except (ValueError, IOError):
        return None


def is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is running.

    Args:
        pid: The process ID to check

    Returns:
        True if the process is running, False otherwise
    """
    try:
        # Signal 0 doesn't actually send a signal, but checks if process exists
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def is_daemon_running(project_dir: Path) -> bool:
    """Check if the daemon is running for a project.

    Args:
        project_dir: The project directory

    Returns:
        True if daemon is running, False otherwise
    """
    project_dir = project_dir.resolve()
    pid_path = get_pid_path(project_dir)
    pid = read_pid_file(pid_path)

    if pid is None:
        return False

    return is_process_running(pid)


def get_daemon_status(project_dir: Path) -> OrchestratorState:
    """Get the status of the daemon for a project.

    Args:
        project_dir: The project directory

    Returns:
        OrchestratorState with daemon status information
    """
    project_dir = project_dir.resolve()
    pid_path = get_pid_path(project_dir)
    pid = read_pid_file(pid_path)

    if pid is None or not is_process_running(pid):
        return OrchestratorState(running=False)

    # Try to get work unit counts from the database
    db_path = get_default_db_path(project_dir)
    work_unit_counts = {}

    if db_path.exists():
        try:
            store = StateStore(db_path)
            store.initialize()
            work_unit_counts = store.count_by_status()
            store.close()
        except Exception:
            pass  # Ignore database errors for status

    # Calculate uptime from PID file mtime
    started_at = None
    uptime_seconds = None
    try:
        stat = pid_path.stat()
        started_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        uptime_seconds = (datetime.now(timezone.utc) - started_at).total_seconds()
    except OSError:
        pass

    return OrchestratorState(
        running=True,
        pid=pid,
        uptime_seconds=uptime_seconds,
        started_at=started_at,
        work_unit_counts=work_unit_counts,
    )


def _write_pid_file(pid_path: Path, pid: int) -> None:
    """Write the PID to the PID file with a lock.

    Args:
        pid_path: Path to the PID file
        pid: The process ID to write

    Raises:
        DaemonError: If another instance is already running
    """
    pid_path.parent.mkdir(parents=True, exist_ok=True)

    # Open file for writing, create if doesn't exist
    fd = os.open(str(pid_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        # Try to acquire exclusive lock
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        # Check if there's an existing PID that's still running
        try:
            content = os.read(fd, 100).decode().strip()
            if content:
                existing_pid = int(content)
                if is_process_running(existing_pid):
                    raise DaemonError(
                        f"Daemon already running with PID {existing_pid}"
                    )
        except (ValueError, UnicodeDecodeError):
            pass

        # Write new PID
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, f"{pid}\n".encode())

    except BlockingIOError:
        os.close(fd)
        raise DaemonError("Could not acquire lock on PID file - daemon may be starting")
    except Exception:
        os.close(fd)
        raise


def _remove_pid_file(pid_path: Path) -> None:
    """Remove the PID file.

    Args:
        pid_path: Path to the PID file
    """
    try:
        pid_path.unlink()
    except FileNotFoundError:
        pass


def _daemonize() -> None:
    """Daemonize the current process using double-fork.

    This properly detaches the process from the controlling terminal.
    """
    # First fork - parent exits, child continues
    try:
        pid = os.fork()
        if pid > 0:
            # Parent exits
            os._exit(0)
    except OSError as e:
        raise DaemonError(f"First fork failed: {e}")

    # Decouple from parent environment
    os.chdir("/")
    os.setsid()  # Create new session
    os.umask(0)

    # Second fork - prevents zombie processes
    try:
        pid = os.fork()
        if pid > 0:
            # First child exits
            os._exit(0)
    except OSError as e:
        raise DaemonError(f"Second fork failed: {e}")

    # Redirect standard file descriptors to /dev/null
    sys.stdout.flush()
    sys.stderr.flush()

    with open("/dev/null", "rb", 0) as null_in:
        os.dup2(null_in.fileno(), sys.stdin.fileno())

    # Note: stdout/stderr will be redirected to log file by start_daemon


def start_daemon(project_dir: Path) -> int:
    """Start the orchestrator daemon.

    Args:
        project_dir: The project directory

    Returns:
        The PID of the started daemon

    Raises:
        DaemonError: If daemon is already running or startup fails
    """
    # Resolve to absolute path before forking (daemon changes cwd to /)
    project_dir = project_dir.resolve()

    # Check if already running
    if is_daemon_running(project_dir):
        pid = read_pid_file(get_pid_path(project_dir))
        raise DaemonError(f"Daemon already running with PID {pid}")

    # Get paths (all absolute since project_dir is resolved)
    pid_path = get_pid_path(project_dir)
    socket_path = get_socket_path(project_dir)
    log_path = get_log_path(project_dir)

    # Ensure .ve directory exists
    pid_path.parent.mkdir(parents=True, exist_ok=True)

    # Clean up stale socket if exists
    if socket_path.exists():
        socket_path.unlink()

    # Fork to create daemon
    try:
        pid = os.fork()
    except OSError as e:
        raise DaemonError(f"Fork failed: {e}")

    if pid > 0:
        # Parent process - wait a bit for daemon to start
        time.sleep(0.5)

        # Verify daemon started
        if not is_daemon_running(project_dir):
            raise DaemonError("Daemon failed to start - check logs")

        return read_pid_file(pid_path)

    # Child process - become daemon
    try:
        _daemonize()

        # Redirect stdout/stderr to log file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_fd = os.open(str(log_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        os.dup2(log_fd, sys.stdout.fileno())
        os.dup2(log_fd, sys.stderr.fileno())
        os.close(log_fd)

        # Write PID file
        _write_pid_file(pid_path, os.getpid())

        # Register cleanup
        atexit.register(lambda: _remove_pid_file(pid_path))
        atexit.register(lambda: socket_path.unlink() if socket_path.exists() else None)

        # Set up signal handlers
        def handle_term(signum, frame):
            sys.exit(0)

        signal.signal(signal.SIGTERM, handle_term)
        signal.signal(signal.SIGINT, handle_term)

        # Initialize state store
        db_path = get_default_db_path(project_dir)
        store = StateStore(db_path)
        store.initialize()

        # Capture base branch at startup
        base_branch = _get_current_branch(project_dir)
        store.set_config("base_branch", base_branch)
        logger.info(f"Daemon started on branch: {base_branch}")

        # Load config from database or use defaults
        orch_config = _load_config(store)

        # Import and create the API app
        from orchestrator.api import create_app

        app = create_app(project_dir)

        # Run the server with scheduler
        asyncio.run(_run_daemon_async(
            app=app,
            socket_path=socket_path,
            store=store,
            project_dir=project_dir,
            config=orch_config,
            base_branch=base_branch,
        ))

    except Exception as e:
        print(f"Daemon startup error: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


def _get_current_branch(project_dir: Path) -> str:
    """Get the current git branch name.

    Args:
        project_dir: The project directory

    Returns:
        Current branch name

    Raises:
        DaemonError: If not in a git repo or git command fails
    """
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DaemonError(f"Failed to get current branch: {result.stderr}")

    branch = result.stdout.strip()
    if branch == "HEAD":
        # Detached HEAD state - get the commit instead
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise DaemonError("Failed to get current commit in detached HEAD state")
        return result.stdout.strip()

    return branch


def _load_config(store: StateStore) -> OrchestratorConfig:
    """Load orchestrator config from database.

    Args:
        store: State store

    Returns:
        OrchestratorConfig with values from database or defaults
    """
    config = OrchestratorConfig()

    # Load max_agents
    max_agents_str = store.get_config("max_agents")
    if max_agents_str is not None:
        try:
            config.max_agents = int(max_agents_str)
        except ValueError:
            pass

    # Load dispatch_interval_seconds
    dispatch_str = store.get_config("dispatch_interval_seconds")
    if dispatch_str is not None:
        try:
            config.dispatch_interval_seconds = float(dispatch_str)
        except ValueError:
            pass

    return config


async def _run_daemon_async(
    app,
    socket_path: Path,
    store: StateStore,
    project_dir: Path,
    config: OrchestratorConfig,
    base_branch: str,
) -> None:
    """Run the daemon with scheduler as async tasks.

    Args:
        app: Starlette application
        socket_path: Unix socket path
        store: State store
        project_dir: Project directory
        config: Orchestrator config
        base_branch: Git branch to use as base for worktrees
    """
    from orchestrator.scheduler import create_scheduler

    # Create scheduler with base branch
    scheduler = create_scheduler(store, project_dir, config, base_branch)

    # Create uvicorn server
    uvicorn_config = uvicorn.Config(
        app,
        uds=str(socket_path),
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(uvicorn_config)

    # Create shutdown event
    shutdown_event = asyncio.Event()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Run scheduler and server concurrently
    scheduler_task = asyncio.create_task(scheduler.start())
    server_task = asyncio.create_task(server.serve())

    # Wait for shutdown signal
    await shutdown_event.wait()

    # Graceful shutdown
    logger.info("Shutting down...")

    # Stop scheduler first
    await scheduler.stop()
    scheduler_task.cancel()

    # Then stop server
    server.should_exit = True
    try:
        await asyncio.wait_for(server_task, timeout=5.0)
    except asyncio.TimeoutError:
        server_task.cancel()

    logger.info("Daemon shutdown complete")


def stop_daemon(project_dir: Path, timeout: float = 5.0) -> bool:
    """Stop the orchestrator daemon.

    Args:
        project_dir: The project directory
        timeout: Seconds to wait for graceful shutdown

    Returns:
        True if daemon was stopped, False if it wasn't running

    Raises:
        DaemonError: If daemon doesn't stop within timeout
    """
    project_dir = project_dir.resolve()
    pid_path = get_pid_path(project_dir)
    pid = read_pid_file(pid_path)

    if pid is None:
        return False

    if not is_process_running(pid):
        # Stale PID file - clean up
        _remove_pid_file(pid_path)
        return False

    # Send SIGTERM for graceful shutdown
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        _remove_pid_file(pid_path)
        return False

    # Wait for process to exit
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_process_running(pid):
            # Clean up PID file if it still exists
            _remove_pid_file(pid_path)
            return True
        time.sleep(0.1)

    # Process didn't exit - try SIGKILL
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass

    # Wait a bit more
    time.sleep(0.5)

    if is_process_running(pid):
        raise DaemonError(f"Failed to stop daemon (PID {pid})")

    _remove_pid_file(pid_path)
    return True
