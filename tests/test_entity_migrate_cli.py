"""Tests for the 've entity migrate' CLI command.

# Chunk: docs/chunks/entity_memory_migration - Migration CLI tests
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from cli.entity import entity
from entity_migration import MigrationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stub_result(
    entity_name: str = "slack-watcher",
    source_dir: Path | None = None,
    dest_dir: Path | None = None,
    wiki_pages_created: list[str] | None = None,
    memories_preserved: int = 4,
    sessions_migrated: int = 1,
    unclassified_count: int = 0,
) -> MigrationResult:
    """Build a fixed MigrationResult for CLI test assertions."""
    return MigrationResult(
        entity_name=entity_name,
        source_dir=source_dir or Path("/tmp/source"),
        dest_dir=dest_dir or Path("/tmp/output/slack-watcher"),
        wiki_pages_created=wiki_pages_created
        or ["wiki/identity.md", "wiki/domain/heartbeat.md", "wiki/log.md"],
        memories_preserved=memories_preserved,
        sessions_migrated=sessions_migrated,
        unclassified_count=unclassified_count,
    )


def _make_identity_file(entity_dir: Path, name: str = "slack_watcher") -> None:
    """Write a minimal identity.md into entity_dir."""
    entity_dir.mkdir(parents=True, exist_ok=True)
    fm = {"name": name, "role": "Test role", "created": "2026-01-01T00:00:00+00:00"}
    (entity_dir / "identity.md").write_text(
        f"---\n{yaml.dump(fm)}---\n\nBody.\n"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMigrateCLI:
    """Tests for 've entity migrate' command using CliRunner."""

    def test_migrate_cli_success(self, tmp_path: Path) -> None:
        """Exit code 0 and output contains new entity name and summary."""
        runner = CliRunner()
        stub_result = _make_stub_result(
            entity_name="slack-watcher",
            dest_dir=tmp_path / "slack-watcher",
        )

        # Set up a fake entity dir so --entity-dir points somewhere real
        entity_dir = tmp_path / "legacy_entity"
        _make_identity_file(entity_dir)

        with patch("entity_migration.migrate_entity", return_value=stub_result):
            result = runner.invoke(
                entity,
                [
                    "migrate",
                    "58d36632-bf65-4ba3-8f34-481cf64e9701",
                    "--name", "slack-watcher",
                    "--entity-dir", str(entity_dir),
                    "--output-dir", str(tmp_path),
                ],
            )

        assert result.exit_code == 0, result.output
        assert "slack-watcher" in result.output
        assert "Wiki pages created:" in result.output
        assert "Memories preserved:" in result.output
        assert "Sessions migrated:" in result.output

    def test_migrate_cli_default_entity_dir_resolution(self, tmp_path: Path) -> None:
        """Resolves .entities/<name>/ from project dir when --entity-dir is omitted."""
        runner = CliRunner()

        # Set up a project dir with .entities/<name>/
        project_dir = tmp_path / "project"
        entity_name = "some-entity"
        entity_dir = project_dir / ".entities" / entity_name
        _make_identity_file(entity_dir)

        stub_result = _make_stub_result(
            entity_name="migrated",
            source_dir=entity_dir,
            dest_dir=tmp_path / "migrated",
        )

        with patch("entity_migration.migrate_entity", return_value=stub_result) as mock_migrate, \
             patch("cli.entity.resolve_entity_project_dir", return_value=project_dir):
            result = runner.invoke(
                entity,
                [
                    "migrate",
                    entity_name,
                    "--name", "migrated",
                    "--output-dir", str(tmp_path),
                ],
            )

        assert result.exit_code == 0, result.output
        # Verify migrate_entity was called with the correct source_dir
        called_source = mock_migrate.call_args[0][0]
        assert called_source == entity_dir

    def test_migrate_cli_custom_entity_dir(self, tmp_path: Path) -> None:
        """--entity-dir flag is respected (not resolved from project dir)."""
        runner = CliRunner()

        custom_dir = tmp_path / "custom_entity"
        _make_identity_file(custom_dir)

        stub_result = _make_stub_result(
            source_dir=custom_dir,
            dest_dir=tmp_path / "new-entity",
        )

        with patch("entity_migration.migrate_entity", return_value=stub_result) as mock_migrate:
            result = runner.invoke(
                entity,
                [
                    "migrate",
                    "irrelevant-uuid",
                    "--name", "new-entity",
                    "--entity-dir", str(custom_dir),
                    "--output-dir", str(tmp_path),
                ],
            )

        assert result.exit_code == 0, result.output
        # Verify entity_dir argument passed to migrate_entity
        called_source = mock_migrate.call_args[0][0]
        assert called_source == custom_dir

    def test_migrate_cli_error_propagates(self, tmp_path: Path) -> None:
        """ValueError from migration results in non-zero exit and error message."""
        runner = CliRunner()

        entity_dir = tmp_path / "missing_entity"
        # Do not create entity_dir — migrate_entity will raise

        with patch(
            "entity_migration.migrate_entity",
            side_effect=ValueError("Source entity directory not found: /tmp/x"),
        ):
            result = runner.invoke(
                entity,
                [
                    "migrate",
                    "missing-uuid",
                    "--name", "something",
                    "--entity-dir", str(entity_dir),
                    "--output-dir", str(tmp_path),
                ],
            )

        assert result.exit_code != 0
        assert "Source entity directory not found" in result.output

    def test_migrate_cli_shows_unclassified_count(self, tmp_path: Path) -> None:
        """Output includes unclassified count when it's non-zero."""
        runner = CliRunner()

        entity_dir = tmp_path / "legacy_entity"
        _make_identity_file(entity_dir)

        stub_result = _make_stub_result(
            entity_name="test-entity",
            dest_dir=tmp_path / "test-entity",
            unclassified_count=2,
        )

        with patch("entity_migration.migrate_entity", return_value=stub_result):
            result = runner.invoke(
                entity,
                [
                    "migrate",
                    "some-uuid",
                    "--name", "test-entity",
                    "--entity-dir", str(entity_dir),
                    "--output-dir", str(tmp_path),
                ],
            )

        assert result.exit_code == 0, result.output
        assert "2 (review manually)" in result.output
