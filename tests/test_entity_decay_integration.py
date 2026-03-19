"""Integration tests for entity memory decay through the consolidation pipeline.

# Chunk: docs/chunks/entity_memory_decay

Tests the full flow through run_consolidation() with decay enabled,
using mocked Anthropic API and real filesystem via tmp_path.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from entities import Entities
from entity_shutdown import run_consolidation
from models.entity import (
    DecayConfig,
    MemoryCategory,
    MemoryFrontmatter,
    MemoryTier,
    MemoryValence,
)


class TestConsolidationWithDecay:
    """Integration tests exercising the full consolidation + decay pipeline."""

    def _setup_entity(self, tmp_path: Path) -> Entities:
        """Create an entity with directory structure."""
        entities = Entities(tmp_path)
        entities.create_entity("testbot", role="Test bot")
        return entities

    def _make_extracted_json(self, count: int = 5) -> str:
        """Create extracted memories JSON."""
        memories = [
            {
                "title": f"Memory {i}",
                "content": f"Learned something {i}",
                "category": "skill",
                "valence": "positive",
                "salience": 3,
            }
            for i in range(count)
        ]
        return json.dumps(memories)

    def _make_api_response(
        self,
        consolidated_count: int = 2,
        core_count: int = 1,
        now: datetime | None = None,
    ) -> str:
        """Create a mock API consolidation response."""
        if now is None:
            now = datetime.now(timezone.utc)
        consolidated = [
            {
                "title": f"Consolidated {i}",
                "content": f"Merged skill {i}",
                "valence": "positive",
                "category": "skill",
                "salience": 4,
                "tier": "consolidated",
                "source_memories": [f"Memory {i * 2}", f"Memory {i * 2 + 1}"],
                "recurrence_count": 2,
                "last_reinforced": now.isoformat(),
            }
            for i in range(consolidated_count)
        ]
        core = [
            {
                "title": f"Core principle {i}",
                "content": f"Fundamental principle {i}",
                "valence": "positive",
                "category": "correction",
                "salience": 5,
                "tier": "core",
                "source_memories": [f"Consolidated {i}"],
                "recurrence_count": 5,
                "last_reinforced": now.isoformat(),
            }
            for i in range(core_count)
        ]
        return json.dumps({
            "consolidated": consolidated,
            "core": core,
            "unconsolidated": ["Memory 4"],
        })

    @patch("entity_shutdown.anthropic")
    def test_consolidation_with_decay_removes_old_journals(
        self, mock_anthropic, tmp_path
    ):
        """Old journal memories are expired by decay after consolidation."""
        entities = self._setup_entity(tmp_path)

        # Pre-populate old journal memories (simulating previous cycles)
        old_time = datetime(2026, 3, 1, tzinfo=timezone.utc)
        for i in range(3):
            old_fm = MemoryFrontmatter(
                title=f"Old journal {i}",
                category=MemoryCategory.DOMAIN,
                valence=MemoryValence.NEUTRAL,
                salience=2,
                tier=MemoryTier.JOURNAL,
                last_reinforced=old_time,
                recurrence_count=0,
            )
            entities.write_memory("testbot", old_fm, f"Old content {i}")

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=self._make_api_response())]
        mock_client.messages.create.return_value = mock_response

        # Use aggressive decay config: expire journals after 5 days
        config = DecayConfig(tier0_expiry_cycles=5)

        result = run_consolidation(
            "testbot",
            self._make_extracted_json(),
            tmp_path,
            api_key="test-key",
            decay_config=config,
        )

        # Old journals (18+ days old) should be expired
        assert result["expired"] >= 3

        # New journals (just written) should survive
        journal_dir = tmp_path / ".entities" / "testbot" / "memories" / "journal"
        remaining = list(journal_dir.glob("*.md"))
        # 5 new journals were written, 3 old ones should be gone
        assert len(remaining) == 5

    @patch("entity_shutdown.anthropic")
    def test_consolidation_with_decay_demotes_unreinforced_core(
        self, mock_anthropic, tmp_path
    ):
        """Core memories with old last_reinforced are demoted to consolidated."""
        entities = self._setup_entity(tmp_path)

        # Pre-populate an old core memory
        old_time = datetime(2026, 2, 1, tzinfo=timezone.utc)
        old_core = MemoryFrontmatter(
            title="Stale core skill",
            category=MemoryCategory.SKILL,
            valence=MemoryValence.POSITIVE,
            salience=5,
            tier=MemoryTier.CORE,
            last_reinforced=old_time,
            recurrence_count=5,
        )
        entities.write_memory("testbot", old_core, "A skill no longer used")

        # API returns just the old core memory unchanged (not reinforced)
        now = datetime.now(timezone.utc)
        api_response = json.dumps({
            "consolidated": [],
            "core": [
                {
                    "title": "Stale core skill",
                    "content": "A skill no longer used",
                    "valence": "positive",
                    "category": "skill",
                    "salience": 5,
                    "tier": "core",
                    "source_memories": [],
                    "recurrence_count": 5,
                    "last_reinforced": old_time.isoformat(),
                }
            ],
            "unconsolidated": [],
        })

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=api_response)]
        mock_client.messages.create.return_value = mock_response

        config = DecayConfig(tier2_demote_cycles=10)

        result = run_consolidation(
            "testbot",
            self._make_extracted_json(),
            tmp_path,
            api_key="test-key",
            decay_config=config,
        )

        assert result["demoted"] >= 1

        # The core directory should be empty (old file removed, demoted to consolidated)
        core_dir = tmp_path / ".entities" / "testbot" / "memories" / "core"
        core_files = list(core_dir.glob("*.md"))
        assert len(core_files) == 0

        # The consolidated directory should have the demoted memory
        cons_dir = tmp_path / ".entities" / "testbot" / "memories" / "consolidated"
        cons_files = list(cons_dir.glob("*.md"))
        # At least one demoted memory should be there
        titles = []
        for f in cons_files:
            fm, _ = entities.parse_memory(f)
            if fm:
                titles.append(fm.title)
        assert "Stale core skill" in titles

    @patch("entity_shutdown.anthropic")
    def test_decay_log_written(self, mock_anthropic, tmp_path):
        """After consolidation with decay, decay_log.jsonl contains events."""
        entities = self._setup_entity(tmp_path)

        # Pre-populate old journal to trigger expiry
        old_time = datetime(2026, 2, 1, tzinfo=timezone.utc)
        old_fm = MemoryFrontmatter(
            title="Very old journal",
            category=MemoryCategory.DOMAIN,
            valence=MemoryValence.NEUTRAL,
            salience=2,
            tier=MemoryTier.JOURNAL,
            last_reinforced=old_time,
            recurrence_count=0,
        )
        entities.write_memory("testbot", old_fm, "Ancient memory")

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=self._make_api_response())]
        mock_client.messages.create.return_value = mock_response

        config = DecayConfig(tier0_expiry_cycles=5)

        run_consolidation(
            "testbot",
            self._make_extracted_json(),
            tmp_path,
            api_key="test-key",
            decay_config=config,
        )

        # Verify decay log exists and has events
        events = entities.read_decay_log("testbot")
        assert len(events) >= 1

        # Check the expired event
        expired_events = [e for e in events if e.action == "expired"]
        assert len(expired_events) >= 1
        assert expired_events[0].memory_title == "Very old journal"
        assert "unreinforced" in expired_events[0].reason

    @patch("entity_shutdown.anthropic")
    def test_consolidation_summary_includes_decay_stats(
        self, mock_anthropic, tmp_path
    ):
        """The return dict from run_consolidation() includes decay statistics."""
        self._setup_entity(tmp_path)

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=self._make_api_response())]
        mock_client.messages.create.return_value = mock_response

        result = run_consolidation(
            "testbot",
            self._make_extracted_json(),
            tmp_path,
            api_key="test-key",
        )

        # Result must include decay stats
        assert "expired" in result
        assert "demoted" in result
        assert isinstance(result["expired"], int)
        assert isinstance(result["demoted"], int)

    @patch("entity_shutdown.anthropic")
    def test_fresh_memories_survive_decay(self, mock_anthropic, tmp_path):
        """Freshly consolidated and core memories are not decayed."""
        self._setup_entity(tmp_path)

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=self._make_api_response(2, 1))]
        mock_client.messages.create.return_value = mock_response

        result = run_consolidation(
            "testbot",
            self._make_extracted_json(),
            tmp_path,
            api_key="test-key",
        )

        # No decay should happen on fresh memories
        assert result["expired"] == 0
        assert result["demoted"] == 0
        assert result["consolidated"] == 2
        assert result["core"] == 1
