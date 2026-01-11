# Chunk: docs/chunks/orch_foundation - Orchestrator daemon foundation
"""SQLite state store for the orchestrator daemon.

Provides persistent storage for work units and their state transitions.
Uses a simple migrations infrastructure for schema evolution.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from orchestrator.models import WorkUnit, WorkUnitPhase, WorkUnitStatus


class StateStore:
    """SQLite-based state store for work units.

    Manages the orchestrator's persistent state including work units
    and status transition logging.
    """

    CURRENT_VERSION = 2

    def __init__(self, db_path: Path):
        """Initialize the state store.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._ensure_directory()
        self._connection: Optional[sqlite3.Connection] = None

    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def connection(self) -> sqlite3.Connection:
        """Get or create a database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,  # Allow multi-threaded access
                isolation_level=None,  # Autocommit mode
            )
            self._connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrent access
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
        return self._connection

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def initialize(self) -> None:
        """Initialize the database schema, running migrations if needed."""
        current_version = self._get_schema_version()

        if current_version < self.CURRENT_VERSION:
            self._run_migrations(current_version)

    def _get_schema_version(self) -> int:
        """Get the current schema version.

        Returns 0 if the migrations table doesn't exist.
        """
        try:
            cursor = self.connection.execute(
                "SELECT MAX(version) FROM schema_migrations"
            )
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0
        except sqlite3.OperationalError:
            # Table doesn't exist
            return 0

    def _run_migrations(self, from_version: int) -> None:
        """Run all migrations from from_version to CURRENT_VERSION."""
        migrations = {
            1: self._migrate_v1,
            2: self._migrate_v2,
        }

        for version in range(from_version + 1, self.CURRENT_VERSION + 1):
            if version in migrations:
                migrations[version]()
                self._record_migration(version)

    def _migrate_v1(self) -> None:
        """Initial schema: work_units, schema_migrations, status_log tables."""
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS work_units (
                chunk TEXT PRIMARY KEY,
                phase TEXT NOT NULL,
                status TEXT NOT NULL,
                blocked_by TEXT,
                worktree TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS status_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_status_log_chunk
                ON status_log(chunk);
            CREATE INDEX IF NOT EXISTS idx_work_units_status
                ON work_units(status);
            """
        )

    def _migrate_v2(self) -> None:
        """Add scheduling fields and config table."""
        self.connection.executescript(
            """
            -- Add priority and session_id columns to work_units
            ALTER TABLE work_units ADD COLUMN priority INTEGER DEFAULT 0;
            ALTER TABLE work_units ADD COLUMN session_id TEXT;

            -- Create config table for daemon settings
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            -- Create index for priority-based ordering
            CREATE INDEX IF NOT EXISTS idx_work_units_priority
                ON work_units(priority DESC, created_at ASC);
            """
        )

    def _record_migration(self, version: int) -> None:
        """Record a completed migration."""
        now = datetime.now(timezone.utc).isoformat()
        self.connection.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, now),
        )

    # CRUD Operations

    def create_work_unit(self, work_unit: WorkUnit) -> WorkUnit:
        """Create a new work unit.

        Args:
            work_unit: The work unit to create

        Returns:
            The created work unit

        Raises:
            ValueError: If a work unit with the same chunk already exists
        """
        blocked_by_json = json.dumps(work_unit.blocked_by)

        try:
            self.connection.execute(
                """
                INSERT INTO work_units
                    (chunk, phase, status, blocked_by, worktree, priority, session_id,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    work_unit.chunk,
                    work_unit.phase.value,
                    work_unit.status.value,
                    blocked_by_json,
                    work_unit.worktree,
                    work_unit.priority,
                    work_unit.session_id,
                    work_unit.created_at.isoformat(),
                    work_unit.updated_at.isoformat(),
                ),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"Work unit for chunk '{work_unit.chunk}' already exists")

        # Log the initial status
        self._log_status_transition(work_unit.chunk, None, work_unit.status)

        return work_unit

    def get_work_unit(self, chunk: str) -> Optional[WorkUnit]:
        """Get a work unit by chunk name.

        Args:
            chunk: The chunk name

        Returns:
            The work unit, or None if not found
        """
        cursor = self.connection.execute(
            "SELECT * FROM work_units WHERE chunk = ?", (chunk,)
        )
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_work_unit(row)

    def update_work_unit(self, work_unit: WorkUnit) -> WorkUnit:
        """Update an existing work unit.

        Args:
            work_unit: The work unit with updated values

        Returns:
            The updated work unit

        Raises:
            ValueError: If the work unit doesn't exist
        """
        # Get the old status for logging
        old_unit = self.get_work_unit(work_unit.chunk)
        if old_unit is None:
            raise ValueError(f"Work unit for chunk '{work_unit.chunk}' not found")

        blocked_by_json = json.dumps(work_unit.blocked_by)

        self.connection.execute(
            """
            UPDATE work_units
            SET phase = ?, status = ?, blocked_by = ?, worktree = ?,
                priority = ?, session_id = ?, updated_at = ?
            WHERE chunk = ?
            """,
            (
                work_unit.phase.value,
                work_unit.status.value,
                blocked_by_json,
                work_unit.worktree,
                work_unit.priority,
                work_unit.session_id,
                work_unit.updated_at.isoformat(),
                work_unit.chunk,
            ),
        )

        # Log status transition if status changed
        if old_unit.status != work_unit.status:
            self._log_status_transition(
                work_unit.chunk, old_unit.status, work_unit.status
            )

        return work_unit

    def delete_work_unit(self, chunk: str) -> bool:
        """Delete a work unit.

        Args:
            chunk: The chunk name

        Returns:
            True if deleted, False if not found
        """
        cursor = self.connection.execute(
            "DELETE FROM work_units WHERE chunk = ?", (chunk,)
        )
        return cursor.rowcount > 0

    def list_work_units(
        self, status: Optional[WorkUnitStatus] = None
    ) -> list[WorkUnit]:
        """List all work units, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of work units
        """
        if status is not None:
            cursor = self.connection.execute(
                "SELECT * FROM work_units WHERE status = ? ORDER BY created_at",
                (status.value,),
            )
        else:
            cursor = self.connection.execute(
                "SELECT * FROM work_units ORDER BY created_at"
            )

        return [self._row_to_work_unit(row) for row in cursor.fetchall()]

    def count_by_status(self) -> dict[str, int]:
        """Count work units by status.

        Returns:
            Dict mapping status values to counts
        """
        cursor = self.connection.execute(
            "SELECT status, COUNT(*) FROM work_units GROUP BY status"
        )
        return {row[0]: row[1] for row in cursor.fetchall()}

    # Status logging

    def _log_status_transition(
        self,
        chunk: str,
        old_status: Optional[WorkUnitStatus],
        new_status: WorkUnitStatus,
    ) -> None:
        """Log a status transition for debugging."""
        now = datetime.now(timezone.utc).isoformat()
        old_value = old_status.value if old_status else None

        self.connection.execute(
            """
            INSERT INTO status_log (chunk, old_status, new_status, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (chunk, old_value, new_status.value, now),
        )

    def get_status_history(self, chunk: str) -> list[dict]:
        """Get the status transition history for a chunk.

        Args:
            chunk: The chunk name

        Returns:
            List of status transitions with timestamps
        """
        cursor = self.connection.execute(
            """
            SELECT old_status, new_status, timestamp
            FROM status_log
            WHERE chunk = ?
            ORDER BY id
            """,
            (chunk,),
        )
        return [
            {
                "old_status": row[0],
                "new_status": row[1],
                "timestamp": row[2],
            }
            for row in cursor.fetchall()
        ]

    # Config operations

    def get_config(self, key: str) -> Optional[str]:
        """Get a config value by key.

        Args:
            key: The config key

        Returns:
            The config value, or None if not found
        """
        cursor = self.connection.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def set_config(self, key: str, value: str) -> None:
        """Set a config value.

        Args:
            key: The config key
            value: The config value (stored as string)
        """
        self.connection.execute(
            """
            INSERT OR REPLACE INTO config (key, value)
            VALUES (?, ?)
            """,
            (key, value),
        )

    # Queue operations

    def get_ready_queue(self, limit: Optional[int] = None) -> list[WorkUnit]:
        """Get READY work units ordered by priority (highest first), then creation time.

        Args:
            limit: Optional maximum number of work units to return

        Returns:
            List of READY work units in scheduling order
        """
        query = """
            SELECT * FROM work_units
            WHERE status = ?
            ORDER BY priority DESC, created_at ASC
        """
        if limit is not None:
            query += f" LIMIT {limit}"

        cursor = self.connection.execute(query, (WorkUnitStatus.READY.value,))
        return [self._row_to_work_unit(row) for row in cursor.fetchall()]

    # Helper methods

    def _row_to_work_unit(self, row: sqlite3.Row) -> WorkUnit:
        """Convert a database row to a WorkUnit model."""
        blocked_by = json.loads(row["blocked_by"]) if row["blocked_by"] else []

        # Handle priority and session_id which may not exist in old databases
        try:
            priority = row["priority"] if row["priority"] is not None else 0
        except (IndexError, KeyError):
            priority = 0

        try:
            session_id = row["session_id"]
        except (IndexError, KeyError):
            session_id = None

        return WorkUnit(
            chunk=row["chunk"],
            phase=WorkUnitPhase(row["phase"]),
            status=WorkUnitStatus(row["status"]),
            blocked_by=blocked_by,
            worktree=row["worktree"],
            priority=priority,
            session_id=session_id,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


def get_default_db_path(project_dir: Path) -> Path:
    """Get the default database path for a project.

    Args:
        project_dir: The project directory

    Returns:
        Path to the orchestrator database
    """
    return project_dir / ".ve" / "orchestrator.db"
