"""Tests for entity_migration.py.

# Chunk: docs/chunks/entity_memory_migration - Migration tests
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml

from entity_migration import (
    ClassifiedMemories,
    LegacyMemory,
    MigrationResult,
    _IDENTITY_SYNTHESIS_PROMPT,
    _KNOWLEDGE_PAGES_PROMPT,
    classify_memories,
    format_log_page,
    migrate_entity,
    read_legacy_entity,
    synthesize_identity_page,
    synthesize_knowledge_pages,
)
from models.entity import (
    EntityIdentity,
    MemoryCategory,
    MemoryFrontmatter,
    MemoryTier,
    MemoryValence,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(path: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a git command in the given path."""
    return subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
    )


def _make_memory_file(
    directory: Path,
    filename: str,
    title: str,
    category: MemoryCategory,
    valence: MemoryValence = MemoryValence.NEUTRAL,
    salience: int = 3,
    tier: MemoryTier = MemoryTier.CONSOLIDATED,
    last_reinforced: str = "2026-01-02T00:00:00+00:00",
    recurrence_count: int = 1,
    content: str = "Test memory content.",
) -> Path:
    """Write a memory file with valid YAML frontmatter to the given directory."""
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / filename
    frontmatter = {
        "title": title,
        "category": category.value,
        "valence": valence.value,
        "salience": salience,
        "tier": tier.value,
        "last_reinforced": last_reinforced,
        "recurrence_count": recurrence_count,
        "source_memories": [],
    }
    fm_text = yaml.dump(frontmatter, default_flow_style=False)
    file_path.write_text(f"---\n{fm_text}---\n\n{content}\n")
    return file_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def legacy_entity_dir(tmp_path: Path) -> Path:
    """A minimal legacy entity directory with all memory tiers and a session."""
    entity_dir = tmp_path / "58d36632-bf65-4ba3-8f34-481cf64e9701"
    entity_dir.mkdir()

    # identity.md
    identity_fm = {
        "name": "slack_watcher",
        "role": "Monitors Slack channels",
        "created": "2026-01-01T00:00:00+00:00",
    }
    identity_body = "I am an infrastructure publisher.\n"
    (entity_dir / "identity.md").write_text(
        f"---\n{yaml.dump(identity_fm)}---\n\n{identity_body}"
    )

    # memories/core/ — domain category
    _make_memory_file(
        entity_dir / "memories" / "core",
        "20260101_core_values.md",
        title="Core platform values",
        category=MemoryCategory.DOMAIN,
        tier=MemoryTier.CORE,
        last_reinforced="2026-01-01T00:00:00+00:00",
        content="The platform requires tools to exit 0 to prove themselves.",
    )

    # memories/consolidated/ — domain category
    _make_memory_file(
        entity_dir / "memories" / "consolidated",
        "20260102_domain_pattern.md",
        title="Domain pattern: heartbeat",
        category=MemoryCategory.DOMAIN,
        tier=MemoryTier.CONSOLIDATED,
        last_reinforced="2026-01-02T00:00:00+00:00",
        content="Always initialize heartbeat synchronously before async code.",
    )

    # memories/consolidated/ — skill category
    _make_memory_file(
        entity_dir / "memories" / "consolidated",
        "20260103_skill_pattern.md",
        title="Skill: copy boilerplate",
        category=MemoryCategory.SKILL,
        tier=MemoryTier.CONSOLIDATED,
        last_reinforced="2026-01-03T00:00:00+00:00",
        content="When a tool structure resists proving, copy exact boilerplate from a working tool.",
    )

    # memories/journal/ — correction category
    _make_memory_file(
        entity_dir / "memories" / "journal",
        "20260104_session_note.md",
        title="Session note: edit loop",
        category=MemoryCategory.CORRECTION,
        tier=MemoryTier.JOURNAL,
        last_reinforced="2026-01-04T00:00:00+00:00",
        content="Editing a tool triggers the watcher and kills the running process.",
    )

    # sessions/
    sessions_dir = entity_dir / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "abc123.jsonl").write_text('{"role":"user","content":"hello"}\n')

    return entity_dir


# ---------------------------------------------------------------------------
# TestReadLegacyEntity
# ---------------------------------------------------------------------------


class TestReadLegacyEntity:
    """Tests for read_legacy_entity()."""

    def test_reads_identity_when_present(self, legacy_entity_dir: Path) -> None:
        """Parsed identity matches the fixture's name."""
        identity, _, _ = read_legacy_entity(legacy_entity_dir)
        assert identity is not None
        assert identity.name == "slack_watcher"

    def test_reads_all_memory_tiers(self, legacy_entity_dir: Path) -> None:
        """Returns memories from journal, consolidated, and core tiers."""
        _, _, memories = read_legacy_entity(legacy_entity_dir)
        tiers = {m.tier for m in memories}
        assert MemoryTier.JOURNAL in tiers
        assert MemoryTier.CONSOLIDATED in tiers
        assert MemoryTier.CORE in tiers

    def test_returns_empty_for_missing_memories_dir(self, tmp_path: Path) -> None:
        """No crash and empty memory list when memories/ directory is absent."""
        entity_dir = tmp_path / "empty_entity"
        entity_dir.mkdir()
        # Write minimal identity.md
        (entity_dir / "identity.md").write_text(
            "---\nname: test_entity\ncreated: 2026-01-01T00:00:00+00:00\n---\n\nBody.\n"
        )
        identity, _, memories = read_legacy_entity(entity_dir)
        assert memories == []
        assert identity is not None

    def test_returns_identity_body_text(self, legacy_entity_dir: Path) -> None:
        """Body content after frontmatter is extracted correctly."""
        _, body, _ = read_legacy_entity(legacy_entity_dir)
        assert "infrastructure publisher" in body

    def test_returns_four_memories_from_fixture(self, legacy_entity_dir: Path) -> None:
        """Fixture has exactly 4 memory files (1 core, 2 consolidated, 1 journal)."""
        _, _, memories = read_legacy_entity(legacy_entity_dir)
        assert len(memories) == 4


# ---------------------------------------------------------------------------
# TestClassifyMemories
# ---------------------------------------------------------------------------


def _make_legacy_memory(
    tier: MemoryTier,
    category: MemoryCategory,
    title: str = "Test",
    salience: int = 3,
    last_reinforced: datetime | None = None,
    filename: str = "20260101_test.md",
    tmp_path: Path | None = None,
) -> LegacyMemory:
    """Create a LegacyMemory for testing (no real file required)."""
    if last_reinforced is None:
        last_reinforced = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fm = MemoryFrontmatter(
        title=title,
        category=category,
        valence=MemoryValence.NEUTRAL,
        salience=salience,
        tier=tier,
        last_reinforced=last_reinforced,
        recurrence_count=1,
        source_memories=[],
    )
    file_path = Path(tmp_path or "/tmp") / filename
    return LegacyMemory(tier=tier, frontmatter=fm, content="Content.", file_path=file_path)


class TestClassifyMemories:
    """Tests for classify_memories()."""

    def test_core_tier_memory_goes_to_identity(self) -> None:
        """A CORE-tier memory must appear in classified.identity."""
        mem = _make_legacy_memory(MemoryTier.CORE, MemoryCategory.DOMAIN)
        classified = classify_memories([mem])
        assert mem in classified.identity

    def test_domain_category_goes_to_domain(self) -> None:
        """A DOMAIN-category memory must appear in classified.domain."""
        mem = _make_legacy_memory(MemoryTier.CONSOLIDATED, MemoryCategory.DOMAIN)
        classified = classify_memories([mem])
        assert mem in classified.domain

    def test_skill_category_goes_to_techniques(self) -> None:
        """A SKILL-category memory must appear in classified.techniques."""
        mem = _make_legacy_memory(MemoryTier.CONSOLIDATED, MemoryCategory.SKILL)
        classified = classify_memories([mem])
        assert mem in classified.techniques

    def test_journal_tier_goes_to_log(self) -> None:
        """A JOURNAL-tier memory must appear in classified.log."""
        mem = _make_legacy_memory(MemoryTier.JOURNAL, MemoryCategory.CONFIRMATION)
        classified = classify_memories([mem])
        assert mem in classified.log

    def test_correction_category_goes_to_identity(self) -> None:
        """A CORRECTION-category memory must appear in classified.identity."""
        mem = _make_legacy_memory(MemoryTier.JOURNAL, MemoryCategory.CORRECTION)
        classified = classify_memories([mem])
        assert mem in classified.identity

    def test_autonomy_category_goes_to_identity(self) -> None:
        """An AUTONOMY-category memory must appear in classified.identity."""
        mem = _make_legacy_memory(MemoryTier.CONSOLIDATED, MemoryCategory.AUTONOMY)
        classified = classify_memories([mem])
        assert mem in classified.identity

    def test_coordination_category_goes_to_relationships(self) -> None:
        """A COORDINATION-category memory must appear in classified.relationships."""
        mem = _make_legacy_memory(MemoryTier.CONSOLIDATED, MemoryCategory.COORDINATION)
        classified = classify_memories([mem])
        assert mem in classified.relationships

    def test_core_tier_domain_category_in_both_buckets(self) -> None:
        """A CORE-tier DOMAIN memory appears in BOTH identity and domain."""
        mem = _make_legacy_memory(MemoryTier.CORE, MemoryCategory.DOMAIN)
        classified = classify_memories([mem])
        assert mem in classified.identity
        assert mem in classified.domain

    def test_log_sorted_chronologically(self, tmp_path: Path) -> None:
        """Journal entries in classified.log are sorted by filename."""
        mem_b = _make_legacy_memory(
            MemoryTier.JOURNAL,
            MemoryCategory.SKILL,
            filename="20260102_b.md",
            tmp_path=tmp_path,
        )
        mem_a = _make_legacy_memory(
            MemoryTier.JOURNAL,
            MemoryCategory.SKILL,
            filename="20260101_a.md",
            tmp_path=tmp_path,
        )
        classified = classify_memories([mem_b, mem_a])
        assert classified.log[0].file_path.name == "20260101_a.md"
        assert classified.log[1].file_path.name == "20260102_b.md"

    def test_unclassified_for_confirmation_consolidated(self) -> None:
        """A CONFIRMATION-category, non-journal memory goes to techniques, not unclassified."""
        mem = _make_legacy_memory(MemoryTier.CONSOLIDATED, MemoryCategory.CONFIRMATION)
        classified = classify_memories([mem])
        assert mem in classified.techniques
        assert mem not in classified.unclassified


# ---------------------------------------------------------------------------
# TestFormatLogPage
# ---------------------------------------------------------------------------


class TestFormatLogPage:
    """Tests for format_log_page()."""

    def test_format_log_page_with_entries(self) -> None:
        """Produced content includes session date and memory titles."""
        mem = _make_legacy_memory(
            MemoryTier.JOURNAL,
            MemoryCategory.CORRECTION,
            title="Edit loop lesson",
            last_reinforced=datetime(2026, 1, 4, tzinfo=timezone.utc),
        )
        result = format_log_page([mem], created_date="2026-01-04T00:00:00+00:00")
        assert "2026-01-04" in result
        assert "Edit loop lesson" in result
        assert "title: Session Log" in result

    def test_format_log_page_empty(self) -> None:
        """Returns valid markdown with placeholder text when no log entries."""
        result = format_log_page([], created_date="2026-01-01T00:00:00+00:00")
        assert "Session Log" in result
        # Should have the placeholder comment
        assert "Add session entries below" in result

    def test_format_log_page_has_frontmatter(self) -> None:
        """Log page always starts with YAML frontmatter."""
        result = format_log_page([], created_date="2026-01-01T00:00:00+00:00")
        assert result.startswith("---\n")
        assert "title: Session Log" in result


# ---------------------------------------------------------------------------
# Stub LLM client for mocked tests
# ---------------------------------------------------------------------------


def _make_stub_client(identity_text: str = "", pages_json: str = "[]") -> MagicMock:
    """Build a MagicMock anthropic client that returns fixed content.

    The first call returns identity_text, subsequent calls return pages_json.
    """
    client = MagicMock()
    identity_response = MagicMock()
    identity_response.content = [MagicMock(text=identity_text or _STUB_IDENTITY)]
    pages_response = MagicMock()
    pages_response.content = [MagicMock(text=pages_json)]
    client.messages.create.side_effect = [
        identity_response,
        pages_response,
        pages_response,
    ]
    return client


_STUB_IDENTITY = """\
---
title: Identity
created: 2026-01-01T00:00:00+00:00
updated: 2026-01-01T00:00:00+00:00
---

# Identity

## Who I Am

I am a stub entity for testing.

## Role

Stub role.

## Working Style

Testing.

## Values

Reliability.

## Hard-Won Lessons

Always test your code.
"""

_STUB_DOMAIN_PAGES = '[{"filename": "heartbeat.md", "content": "---\\ntitle: Heartbeat\\ncreated: 2026-01-01\\nupdated: 2026-01-01\\n---\\n\\n# Heartbeat\\n\\nContent."}]'


# ---------------------------------------------------------------------------
# TestMigrateEntityStructure
# ---------------------------------------------------------------------------


class TestMigrateEntityStructure:
    """Integration tests for migrate_entity() with a mocked LLM."""

    def test_migrate_creates_valid_git_repo(
        self, legacy_entity_dir: Path, tmp_path: Path, monkeypatch
    ) -> None:
        """git log shows two commits: initial + migration."""
        import entity_migration

        stub = _make_stub_client(pages_json=_STUB_DOMAIN_PAGES)
        monkeypatch.setattr(entity_migration, "anthropic", MagicMock(Anthropic=lambda: stub))

        dest = tmp_path / "output"
        dest.mkdir()
        result = entity_migration.migrate_entity(
            legacy_entity_dir, dest, "slack-watcher"
        )

        log_result = _git(result.dest_dir, "log", "--oneline")
        assert log_result.returncode == 0
        commits = [l for l in log_result.stdout.strip().splitlines() if l]
        assert len(commits) == 2
        assert any("Initial entity state" in c for c in commits)
        assert any("Migration:" in c for c in commits)

    def test_migrate_wiki_identity_overwritten(
        self, legacy_entity_dir: Path, tmp_path: Path, monkeypatch
    ) -> None:
        """wiki/identity.md contains synthesized content, not just the stub."""
        import entity_migration

        stub = _make_stub_client(pages_json=_STUB_DOMAIN_PAGES)
        monkeypatch.setattr(entity_migration, "anthropic", MagicMock(Anthropic=lambda: stub))

        dest = tmp_path / "output"
        dest.mkdir()
        result = entity_migration.migrate_entity(
            legacy_entity_dir, dest, "slack-watcher"
        )

        identity_page = result.dest_dir / "wiki" / "identity.md"
        assert identity_page.exists()
        content = identity_page.read_text()
        assert "stub entity for testing" in content

    def test_migrate_preserves_memories(
        self, legacy_entity_dir: Path, tmp_path: Path, monkeypatch
    ) -> None:
        """memories/core/*.md exists in the new repo."""
        import entity_migration

        stub = _make_stub_client(pages_json=_STUB_DOMAIN_PAGES)
        monkeypatch.setattr(entity_migration, "anthropic", MagicMock(Anthropic=lambda: stub))

        dest = tmp_path / "output"
        dest.mkdir()
        result = entity_migration.migrate_entity(
            legacy_entity_dir, dest, "slack-watcher"
        )

        core_files = list((result.dest_dir / "memories" / "core").glob("*.md"))
        assert len(core_files) >= 1

    def test_migrate_copies_sessions_to_episodic(
        self, legacy_entity_dir: Path, tmp_path: Path, monkeypatch
    ) -> None:
        """episodic/abc123.jsonl exists in the new repo."""
        import entity_migration

        stub = _make_stub_client(pages_json=_STUB_DOMAIN_PAGES)
        monkeypatch.setattr(entity_migration, "anthropic", MagicMock(Anthropic=lambda: stub))

        dest = tmp_path / "output"
        dest.mkdir()
        result = entity_migration.migrate_entity(
            legacy_entity_dir, dest, "slack-watcher"
        )

        episodic_file = result.dest_dir / "episodic" / "abc123.jsonl"
        assert episodic_file.exists()
        assert result.sessions_migrated == 1

    def test_migrate_returns_correct_result(
        self, legacy_entity_dir: Path, tmp_path: Path, monkeypatch
    ) -> None:
        """MigrationResult.memories_preserved == 3 (fixture has 3 memory files)."""
        import entity_migration

        stub = _make_stub_client(pages_json=_STUB_DOMAIN_PAGES)
        monkeypatch.setattr(entity_migration, "anthropic", MagicMock(Anthropic=lambda: stub))

        dest = tmp_path / "output"
        dest.mkdir()
        result = entity_migration.migrate_entity(
            legacy_entity_dir, dest, "slack-watcher"
        )

        # Fixture has 1 core + 2 consolidated + 1 journal = 4 memory files
        assert result.memories_preserved == 4
        assert result.entity_name == "slack-watcher"
        assert result.sessions_migrated == 1


# ---------------------------------------------------------------------------
# TestMigrateEntityEdgeCases
# ---------------------------------------------------------------------------


class TestMigrateEntityEdgeCases:
    """Edge case tests for migrate_entity() with a mocked LLM."""

    def test_migrate_empty_entity(self, tmp_path: Path, monkeypatch) -> None:
        """Entity with no memories succeeds; wiki/log.md has placeholder."""
        import entity_migration

        stub = _make_stub_client()
        monkeypatch.setattr(entity_migration, "anthropic", MagicMock(Anthropic=lambda: stub))

        # Create an empty entity dir (just an identity.md, no memories)
        entity_dir = tmp_path / "empty_uuid"
        entity_dir.mkdir()
        (entity_dir / "identity.md").write_text(
            "---\nname: empty_entity\ncreated: 2026-01-01T00:00:00+00:00\n---\n\n"
        )

        dest = tmp_path / "output"
        dest.mkdir()
        result = entity_migration.migrate_entity(entity_dir, dest, "empty-entity")

        log_page = result.dest_dir / "wiki" / "log.md"
        assert log_page.exists()
        assert "Add session entries below" in log_page.read_text()

    def test_migrate_only_core_memories(self, tmp_path: Path, monkeypatch) -> None:
        """No domain/technique pages created when only core memories exist."""
        import entity_migration

        # Stub: identity call returns content, pages calls return empty JSON
        stub = MagicMock()
        resp_identity = MagicMock()
        resp_identity.content = [MagicMock(text=_STUB_IDENTITY)]
        resp_empty = MagicMock()
        resp_empty.content = [MagicMock(text="[]")]
        stub.messages.create.side_effect = [resp_identity, resp_empty, resp_empty]
        monkeypatch.setattr(entity_migration, "anthropic", MagicMock(Anthropic=lambda: stub))

        entity_dir = tmp_path / "core_only"
        entity_dir.mkdir()
        _make_memory_file(
            entity_dir / "memories" / "core",
            "20260101_core.md",
            title="Core only memory",
            category=MemoryCategory.AUTONOMY,
            tier=MemoryTier.CORE,
        )

        dest = tmp_path / "output"
        dest.mkdir()
        result = entity_migration.migrate_entity(entity_dir, dest, "core-only")

        # wiki/identity.md should be written
        assert "wiki/identity.md" in result.wiki_pages_created
        # No domain or technique pages
        domain_pages = [p for p in result.wiki_pages_created if "domain/" in p]
        technique_pages = [p for p in result.wiki_pages_created if "techniques/" in p]
        assert domain_pages == []
        assert technique_pages == []

    def test_migrate_invalid_new_name(self, tmp_path: Path) -> None:
        """ValueError on names starting with digit or uppercase."""
        entity_dir = tmp_path / "some_entity"
        entity_dir.mkdir()

        dest = tmp_path / "output"
        dest.mkdir()

        with pytest.raises(ValueError, match="Invalid entity name"):
            migrate_entity(entity_dir, dest, "1invalid")

        with pytest.raises(ValueError, match="Invalid entity name"):
            migrate_entity(entity_dir, dest, "InvalidName")

    def test_migrate_nonexistent_source(self, tmp_path: Path) -> None:
        """ValueError on missing source directory."""
        with pytest.raises(ValueError, match="Source entity directory not found"):
            migrate_entity(
                tmp_path / "does_not_exist",
                tmp_path / "output",
                "valid-name",
            )


# ---------------------------------------------------------------------------
# TestMigrationPromptContent
# ---------------------------------------------------------------------------


class TestMigrationPromptContent:
    """Tests that migration synthesis prompts include required framing.

    The prompt constants are pure strings — no mocking needed.
    """

    def test_identity_prompt_includes_cross_reference_requirement(self) -> None:
        """Identity synthesis prompt should require wikilinks to related pages."""
        assert any(
            kw in _IDENTITY_SYNTHESIS_PROMPT.lower()
            for kw in ("wikilink", "cross-reference")
        )

    def test_identity_prompt_emphasizes_hard_won_lessons(self) -> None:
        """Identity synthesis prompt should elevate Hard-Won Lessons section."""
        assert any(
            kw in _IDENTITY_SYNTHESIS_PROMPT.lower()
            for kw in ("most important", "failures", "failure")
        )

    def test_knowledge_pages_prompt_includes_cross_reference_requirement(self) -> None:
        """Knowledge pages prompt should require intra-batch cross-references."""
        assert any(
            kw in _KNOWLEDGE_PAGES_PROMPT.lower()
            for kw in ("cross-reference", "wikilink")
        )


# ---------------------------------------------------------------------------
# TestMigrateEntityAtomicity
# ---------------------------------------------------------------------------


class TestMigrateEntityAtomicity:
    """Tests that migrate_entity() cleans up on failure (atomicity).

    Chunk: docs/chunks/entity_migration_retry - atomicity on failure
    """

    def test_failed_migration_leaves_no_directory_and_retries_successfully(
        self, legacy_entity_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failed migration must not leave a partial directory on disk.

        A second invocation after the failure is resolved must succeed
        without the operator manually deleting any directory.
        """
        import entity_migration

        dest = tmp_path / "output"
        dest.mkdir()

        # Patch anthropic to a mock (so anthropic.Anthropic() doesn't fail on
        # auth at construction time) and patch synthesize_identity_page to
        # simulate an LLM failure mid-migration.
        monkeypatch.setattr(
            entity_migration,
            "anthropic",
            MagicMock(Anthropic=MagicMock()),
        )
        monkeypatch.setattr(
            entity_migration,
            "synthesize_identity_page",
            MagicMock(side_effect=RuntimeError("simulated LLM failure")),
        )

        with pytest.raises(RuntimeError, match="simulated LLM failure"):
            migrate_entity(legacy_entity_dir, dest, "slack-watcher")

        # After a failed migration the destination must NOT exist.
        assert not (dest / "slack-watcher").exists(), (
            "Partial migration directory must be cleaned up on failure"
        )

        # A second attempt with the failure removed must succeed.
        # Set anthropic=None to stay hermetic (skips LLM synthesis entirely,
        # uses the mechanical fallback path — no real API calls needed).
        monkeypatch.setattr(entity_migration, "anthropic", None)

        result = migrate_entity(legacy_entity_dir, dest, "slack-watcher")

        assert result.entity_name == "slack-watcher"
        assert (dest / "slack-watcher").exists()
