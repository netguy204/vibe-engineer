"""Tests for the migrations module."""

import pathlib
import pytest


class TestMigrationsCreateManagedClaudeMd:
    """Tests for creating managed_claude_md migrations."""

    def test_create_migration_managed_claude_md(self, temp_project):
        """create_migration creates managed_claude_md migration directory."""
        from migrations import Migrations

        migrations = Migrations(temp_project)
        migration_dir = migrations.create_migration("managed_claude_md")

        assert migration_dir.exists()
        assert migration_dir == temp_project / "docs" / "migrations" / "managed_claude_md"

    def test_create_migration_managed_claude_md_creates_migration_md(self, temp_project):
        """create_migration creates MIGRATION.md for managed_claude_md type."""
        from migrations import Migrations

        migrations = Migrations(temp_project)
        migration_dir = migrations.create_migration("managed_claude_md")

        migration_md = migration_dir / "MIGRATION.md"
        assert migration_md.exists()

        content = migration_md.read_text()
        assert "status: ANALYZING" in content
        assert "target_file: CLAUDE.md" in content

    def test_create_migration_managed_claude_md_does_not_create_subdirs(self, temp_project):
        """managed_claude_md migration does not create analysis/proposals/questions dirs."""
        from migrations import Migrations

        migrations = Migrations(temp_project)
        migration_dir = migrations.create_migration("managed_claude_md")

        # managed_claude_md is simpler and doesn't need these subdirectories
        assert not (migration_dir / "analysis").exists()
        assert not (migration_dir / "proposals").exists()
        assert not (migration_dir / "questions").exists()

    def test_create_migration_managed_claude_md_raises_if_exists(self, temp_project):
        """create_migration raises ValueError if migration already exists."""
        from migrations import Migrations

        migrations = Migrations(temp_project)
        migrations.create_migration("managed_claude_md")

        with pytest.raises(ValueError, match="already exists"):
            migrations.create_migration("managed_claude_md")

    def test_migration_exists_returns_true_for_managed_claude_md(self, temp_project):
        """migration_exists returns True after creating managed_claude_md migration."""
        from migrations import Migrations

        migrations = Migrations(temp_project)
        assert not migrations.migration_exists("managed_claude_md")

        migrations.create_migration("managed_claude_md")
        assert migrations.migration_exists("managed_claude_md")

    def test_enumerate_migrations_includes_managed_claude_md(self, temp_project):
        """enumerate_migrations includes managed_claude_md after creation."""
        from migrations import Migrations

        migrations = Migrations(temp_project)
        migrations.create_migration("managed_claude_md")

        migration_list = migrations.enumerate_migrations()
        assert "managed_claude_md" in migration_list


class TestMigrationsSupportedTypes:
    """Tests for migration type validation."""

    def test_create_migration_rejects_unknown_type(self, temp_project):
        """create_migration raises ValueError for unknown migration type."""
        from migrations import Migrations

        migrations = Migrations(temp_project)

        with pytest.raises(ValueError, match="Unknown migration type"):
            migrations.create_migration("unknown_type")

    def test_create_migration_accepts_chunks_to_subsystems(self, temp_project):
        """create_migration accepts chunks_to_subsystems type."""
        from migrations import Migrations

        migrations = Migrations(temp_project)
        migration_dir = migrations.create_migration("chunks_to_subsystems")

        assert migration_dir.exists()
        # chunks_to_subsystems creates subdirectories
        assert (migration_dir / "analysis").exists()

    def test_create_migration_accepts_subsystem_discovery(self, temp_project):
        """create_migration accepts subsystem_discovery type."""
        from migrations import Migrations

        migrations = Migrations(temp_project)
        migration_dir = migrations.create_migration("subsystem_discovery")

        assert migration_dir.exists()
