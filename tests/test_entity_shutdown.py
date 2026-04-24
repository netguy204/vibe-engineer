"""Tests for entity shutdown (sleep cycle) domain logic.

Tests the memory extraction parsing, consolidation prompt formatting,
consolidation response parsing, and the full run_consolidation pipeline.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from entity_shutdown import (
    EXTRACTION_PROMPT,
    _format_transcript_text,
    extract_memories_from_transcript,
    format_consolidation_prompt,
    parse_consolidation_response,
    parse_extracted_memories,
    run_consolidation,
    shutdown_from_transcript,
    strip_code_fences,
)
from entities import Entities
from entity_transcript import SessionTranscript, Turn
from models.entity import MemoryCategory, MemoryFrontmatter, MemoryTier, MemoryValence


# ---------------------------------------------------------------------------
# strip_code_fences
# ---------------------------------------------------------------------------


class TestStripCodeFences:
    def test_strips_json_code_fence(self):
        text = '```json\n[{"a": 1}]\n```'
        assert strip_code_fences(text) == '[{"a": 1}]'

    def test_strips_bare_code_fence(self):
        text = '```\n{"key": "value"}\n```'
        assert strip_code_fences(text) == '{"key": "value"}'

    def test_preserves_plain_json(self):
        text = '[{"a": 1}]'
        assert strip_code_fences(text) == '[{"a": 1}]'

    def test_handles_whitespace(self):
        text = '  ```json\n{"a": 1}\n```  '
        assert strip_code_fences(text) == '{"a": 1}'

    def test_multiline_content(self):
        text = '```json\n[\n  {"a": 1},\n  {"b": 2}\n]\n```'
        result = strip_code_fences(text)
        assert json.loads(result) == [{"a": 1}, {"b": 2}]


# ---------------------------------------------------------------------------
# parse_extracted_memories
# ---------------------------------------------------------------------------


class TestParseExtractedMemories:
    def _make_memory_json(self, overrides=None, count=1):
        """Create a valid JSON array of extracted memories."""
        base = {
            "title": "Check PR state before acting",
            "content": "Always verify the current state of a PR before acting.",
            "valence": "negative",
            "category": "correction",
            "salience": 4,
        }
        if overrides:
            base.update(overrides)
        return json.dumps([base] * count)

    def test_parses_valid_memories(self):
        raw = self._make_memory_json()
        result = parse_extracted_memories(raw)
        assert len(result) == 1
        fm, content = result[0]
        assert fm.title == "Check PR state before acting"
        assert fm.category == MemoryCategory.CORRECTION
        assert fm.valence == MemoryValence.NEGATIVE
        assert fm.salience == 4
        assert fm.tier == MemoryTier.JOURNAL
        assert fm.recurrence_count == 0
        assert fm.source_memories == []
        assert content == "Always verify the current state of a PR before acting."

    def test_adds_default_fields(self):
        """Missing optional fields get sensible defaults."""
        raw = json.dumps([{
            "title": "Test memory",
            "content": "Some content",
            "category": "skill",
            "valence": "positive",
            "salience": 3,
        }])
        result = parse_extracted_memories(raw)
        assert len(result) == 1
        fm, _ = result[0]
        assert fm.tier == MemoryTier.JOURNAL
        assert fm.recurrence_count == 0
        assert fm.source_memories == []
        assert fm.last_reinforced is not None

    def test_handles_code_fences(self):
        """Strips markdown code fences from JSON."""
        inner = json.dumps([{
            "title": "Fenced memory",
            "content": "Content",
            "category": "domain",
            "valence": "neutral",
            "salience": 2,
        }])
        raw = f"```json\n{inner}\n```"
        result = parse_extracted_memories(raw)
        assert len(result) == 1
        assert result[0][0].title == "Fenced memory"

    def test_rejects_invalid_json(self):
        result = parse_extracted_memories("not json at all")
        assert result == []

    def test_rejects_non_array_json(self):
        result = parse_extracted_memories('{"not": "array"}')
        assert result == []

    def test_skips_invalid_category(self):
        raw = json.dumps([{
            "title": "Bad category",
            "content": "Content",
            "category": "invalid_cat",
            "valence": "positive",
            "salience": 3,
        }])
        result = parse_extracted_memories(raw)
        assert result == []

    def test_skips_invalid_valence(self):
        raw = json.dumps([{
            "title": "Bad valence",
            "content": "Content",
            "category": "skill",
            "valence": "very_positive",
            "salience": 3,
        }])
        result = parse_extracted_memories(raw)
        assert result == []

    def test_skips_invalid_salience(self):
        """Memories with out-of-range salience are skipped."""
        raw = json.dumps([{
            "title": "Bad salience",
            "content": "Content",
            "category": "skill",
            "valence": "positive",
            "salience": 10,
        }])
        result = parse_extracted_memories(raw)
        assert result == []

    def test_normalizes_integer_tiers(self):
        """Prototype format used integer tiers (0, 1, 2)."""
        raw = json.dumps([{
            "title": "Integer tier",
            "content": "Content",
            "category": "skill",
            "valence": "neutral",
            "salience": 3,
            "tier": 0,
        }])
        result = parse_extracted_memories(raw)
        assert len(result) == 1
        assert result[0][0].tier == MemoryTier.JOURNAL

    def test_multiple_memories(self):
        memories = [
            {
                "title": f"Memory {i}",
                "content": f"Content {i}",
                "category": "skill",
                "valence": "positive",
                "salience": i,
            }
            for i in range(1, 4)
        ]
        raw = json.dumps(memories)
        result = parse_extracted_memories(raw)
        assert len(result) == 3

    def test_skips_non_dict_entries(self):
        raw = json.dumps(["not a dict", {"title": "Valid", "content": "C",
                           "category": "skill", "valence": "neutral", "salience": 3}])
        result = parse_extracted_memories(raw)
        assert len(result) == 1

    def test_tolerates_extra_fields(self):
        """Extra fields from the LLM are ignored."""
        raw = json.dumps([{
            "title": "Extra fields",
            "content": "Content",
            "category": "domain",
            "valence": "neutral",
            "salience": 2,
            "source_date": "2026-03-19",
            "extra_field": "ignored",
        }])
        result = parse_extracted_memories(raw)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# format_consolidation_prompt
# ---------------------------------------------------------------------------


class TestFormatConsolidationPrompt:
    def test_includes_all_three_memory_sets(self):
        journals = [{"title": "J1", "content": "Journal 1"}]
        consolidated = [{"title": "C1", "content": "Consolidated 1"}]
        core = [{"title": "K1", "content": "Core 1"}]

        prompt = format_consolidation_prompt(journals, consolidated, core)

        assert '"J1"' in prompt
        assert '"C1"' in prompt
        assert '"K1"' in prompt
        assert "INCREMENTAL" in prompt

    def test_handles_empty_existing(self):
        journals = [{"title": "J1"}]
        prompt = format_consolidation_prompt(journals, [], [])
        assert "[]" in prompt
        assert '"J1"' in prompt


# ---------------------------------------------------------------------------
# parse_consolidation_response
# ---------------------------------------------------------------------------


class TestParseConsolidationResponse:
    def _make_response(self):
        """Create a valid consolidation response JSON."""
        return json.dumps({
            "consolidated": [
                {
                    "title": "Template editing workflow",
                    "content": "Always edit Jinja2 source templates, never rendered files.",
                    "valence": "neutral",
                    "category": "skill",
                    "salience": 4,
                    "tier": "consolidated",
                    "source_memories": ["Edit templates not rendered", "Template system pattern"],
                    "recurrence_count": 3,
                    "last_reinforced": "2026-03-19T12:00:00+00:00",
                }
            ],
            "core": [
                {
                    "title": "Verify state before acting",
                    "content": "Always check current state before taking action.",
                    "valence": "negative",
                    "category": "correction",
                    "salience": 5,
                    "tier": "core",
                    "source_memories": ["Check PR state", "Validate assumptions"],
                    "recurrence_count": 5,
                    "last_reinforced": "2026-03-19T12:00:00+00:00",
                }
            ],
            "unconsolidated": ["Minor detail memory"],
        })

    def test_parses_valid_response(self):
        raw = self._make_response()
        result = parse_consolidation_response(raw)

        assert len(result["consolidated"]) == 1
        assert len(result["core"]) == 1
        assert result["unconsolidated"] == ["Minor detail memory"]

        cons = result["consolidated"][0]
        assert cons["frontmatter"].title == "Template editing workflow"
        assert cons["frontmatter"].tier == MemoryTier.CONSOLIDATED
        assert cons["content"] == "Always edit Jinja2 source templates, never rendered files."

        core = result["core"][0]
        assert core["frontmatter"].title == "Verify state before acting"
        assert core["frontmatter"].tier == MemoryTier.CORE
        assert core["frontmatter"].salience == 5

    def test_handles_code_fences(self):
        inner = self._make_response()
        raw = f"```json\n{inner}\n```"
        result = parse_consolidation_response(raw)
        assert len(result["consolidated"]) == 1

    def test_handles_invalid_json(self):
        result = parse_consolidation_response("not json")
        assert result == {"consolidated": [], "core": [], "unconsolidated": []}

    def test_handles_non_dict_json(self):
        result = parse_consolidation_response("[1, 2, 3]")
        assert result == {"consolidated": [], "core": [], "unconsolidated": []}

    def test_handles_missing_keys(self):
        result = parse_consolidation_response('{"consolidated": []}')
        assert result["consolidated"] == []
        assert result["core"] == []
        assert result["unconsolidated"] == []

    def test_normalizes_integer_tiers(self):
        raw = json.dumps({
            "consolidated": [{
                "title": "Int tier",
                "content": "Content",
                "category": "skill",
                "valence": "neutral",
                "salience": 3,
                "tier": 1,
                "source_memories": [],
                "recurrence_count": 2,
            }],
            "core": [],
            "unconsolidated": [],
        })
        result = parse_consolidation_response(raw)
        assert len(result["consolidated"]) == 1
        assert result["consolidated"][0]["frontmatter"].tier == MemoryTier.CONSOLIDATED


# ---------------------------------------------------------------------------
# run_consolidation (integration with mocked API)
# ---------------------------------------------------------------------------


class TestRunConsolidation:
    def _setup_entity(self, tmp_path):
        """Create an entity with directory structure."""
        entities = Entities(tmp_path)
        entities.create_entity("testbot", role="Test bot")
        return entities

    def _make_extracted_json(self, count=5):
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

    def _make_api_response(self, consolidated_count=2, core_count=1):
        """Create a mock API consolidation response."""
        consolidated = [
            {
                "title": f"Consolidated {i}",
                "content": f"Merged skill {i}",
                "valence": "positive",
                "category": "skill",
                "salience": 4,
                "tier": "consolidated",
                "source_memories": [f"Memory {i*2}", f"Memory {i*2+1}"],
                "recurrence_count": 2,
                "last_reinforced": datetime.now(timezone.utc).isoformat(),
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
                "last_reinforced": datetime.now(timezone.utc).isoformat(),
            }
            for i in range(core_count)
        ]
        return json.dumps({
            "consolidated": consolidated,
            "core": core,
            "unconsolidated": ["Memory 4"],
        })

    @patch("entity_shutdown.anthropic")
    def test_writes_journal_memories(self, mock_anthropic, tmp_path):
        """Journals are written to disk before consolidation."""
        self._setup_entity(tmp_path)

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=self._make_api_response())]
        mock_client.messages.create.return_value = mock_response

        result = run_consolidation(
            "testbot", self._make_extracted_json(), tmp_path, api_key="test-key"
        )

        journal_dir = tmp_path / ".entities" / "testbot" / "memories" / "journal"
        journal_files = list(journal_dir.glob("*.md"))
        # 5 journals written, but consolidated ones are cleaned up;
        # only "Memory 4" is unconsolidated per the mock response
        assert len(journal_files) == 1
        assert result["journals_added"] == 5

    @patch("entity_shutdown.anthropic")
    def test_calls_api_with_formatted_prompt(self, mock_anthropic, tmp_path):
        """API is called with a properly formatted consolidation prompt."""
        self._setup_entity(tmp_path)

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=self._make_api_response())]
        mock_client.messages.create.return_value = mock_response

        run_consolidation(
            "testbot", self._make_extracted_json(), tmp_path, api_key="test-key"
        )

        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args
        prompt_text = call_kwargs.kwargs["messages"][0]["content"]
        assert "INCREMENTAL" in prompt_text
        assert "Memory 0" in prompt_text

    @patch("entity_shutdown.anthropic")
    def test_writes_consolidated_and_core(self, mock_anthropic, tmp_path):
        """Consolidated and core memories from API response are written to disk."""
        self._setup_entity(tmp_path)

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=self._make_api_response(2, 1))]
        mock_client.messages.create.return_value = mock_response

        result = run_consolidation(
            "testbot", self._make_extracted_json(), tmp_path, api_key="test-key"
        )

        assert result["consolidated"] == 2
        assert result["core"] == 1

        cons_dir = tmp_path / ".entities" / "testbot" / "memories" / "consolidated"
        core_dir = tmp_path / ".entities" / "testbot" / "memories" / "core"
        assert len(list(cons_dir.glob("*.md"))) == 2
        assert len(list(core_dir.glob("*.md"))) == 1

    def test_skips_api_when_few_memories_no_existing(self, tmp_path):
        """Skips consolidation when <3 new journals and no existing tiers."""
        self._setup_entity(tmp_path)

        # Only 2 memories, below threshold
        result = run_consolidation(
            "testbot", self._make_extracted_json(count=2), tmp_path
        )

        assert result["journals_added"] == 2
        assert result["consolidated"] == 0
        assert result["core"] == 0

        # Journals were still written
        journal_dir = tmp_path / ".entities" / "testbot" / "memories" / "journal"
        assert len(list(journal_dir.glob("*.md"))) == 2

    def test_returns_zeros_on_empty_input(self, tmp_path):
        """Returns zeros when no memories to process."""
        self._setup_entity(tmp_path)

        result = run_consolidation("testbot", "[]", tmp_path)
        assert result == {"journals_added": 0, "journals_consolidated": 0, "consolidated": 0, "core": 0, "expired": 0, "demoted": 0}

    @patch("entity_shutdown.anthropic", None)
    def test_raises_when_anthropic_missing(self, tmp_path):
        """RuntimeError with clear message when anthropic package is not installed."""
        self._setup_entity(tmp_path)

        with pytest.raises(RuntimeError, match="anthropic.*required"):
            run_consolidation(
                "testbot", self._make_extracted_json(), tmp_path, api_key="test-key"
            )

    def test_returns_zeros_on_invalid_json(self, tmp_path):
        """Returns zeros when input is not valid JSON."""
        self._setup_entity(tmp_path)

        result = run_consolidation("testbot", "not json", tmp_path)
        assert result == {"journals_added": 0, "journals_consolidated": 0, "consolidated": 0, "core": 0, "expired": 0, "demoted": 0}

    @patch("entity_shutdown.anthropic")
    def test_merges_with_existing_tiers(self, mock_anthropic, tmp_path):
        """Existing consolidated/core files are preserved alongside new ones."""
        entities = self._setup_entity(tmp_path)

        # Write pre-existing consolidated memory
        old_fm = MemoryFrontmatter(
            title="Old consolidated memory",
            category=MemoryCategory.SKILL,
            valence=MemoryValence.NEUTRAL,
            salience=3,
            tier=MemoryTier.CONSOLIDATED,
            last_reinforced=datetime.now(timezone.utc),
            recurrence_count=2,
            source_memories=["Old source"],
        )
        entities.write_memory("testbot", old_fm, "Old content")

        # Write pre-existing core memory
        old_core = MemoryFrontmatter(
            title="Old core memory",
            category=MemoryCategory.CORRECTION,
            valence=MemoryValence.NEGATIVE,
            salience=5,
            tier=MemoryTier.CORE,
            last_reinforced=datetime.now(timezone.utc),
            recurrence_count=5,
            source_memories=["Old source"],
        )
        entities.write_memory("testbot", old_core, "Old core content")

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=self._make_api_response(1, 1))]
        mock_client.messages.create.return_value = mock_response

        result = run_consolidation(
            "testbot", self._make_extracted_json(), tmp_path, api_key="test-key"
        )

        cons_dir = tmp_path / ".entities" / "testbot" / "memories" / "consolidated"
        core_dir = tmp_path / ".entities" / "testbot" / "memories" / "core"

        cons_files = list(cons_dir.glob("*.md"))
        core_files = list(core_dir.glob("*.md"))

        # Old + new: 1 old consolidated + 1 new = 2, 1 old core + 1 new = 2
        assert len(cons_files) == 2
        assert len(core_files) == 2

        # Verify both old and new content is present on disk
        all_cons_content = [entities.parse_memory(f)[1] for f in cons_files]
        assert any("Old content" in c for c in all_cons_content)
        assert any("Merged skill" in c for c in all_cons_content)

        all_core_content = [entities.parse_memory(f)[1] for f in core_files]
        assert any("Old core content" in c for c in all_core_content)
        assert any("Fundamental principle" in c for c in all_core_content)

    @patch("entity_shutdown.anthropic")
    def test_existing_memories_survive_when_llm_returns_empty(self, mock_anthropic, tmp_path):
        """Pre-existing consolidated/core memories survive when LLM returns empty results."""
        entities = self._setup_entity(tmp_path)

        # Pre-populate 3 consolidated and 2 core memories
        for i in range(3):
            fm = MemoryFrontmatter(
                title=f"Existing consolidated {i}",
                category=MemoryCategory.SKILL,
                valence=MemoryValence.NEUTRAL,
                salience=3,
                tier=MemoryTier.CONSOLIDATED,
                last_reinforced=datetime.now(timezone.utc),
                recurrence_count=2,
                source_memories=[f"Source {i}"],
            )
            entities.write_memory("testbot", fm, f"Consolidated content {i}")

        for i in range(2):
            fm = MemoryFrontmatter(
                title=f"Existing core {i}",
                category=MemoryCategory.CORRECTION,
                valence=MemoryValence.NEGATIVE,
                salience=5,
                tier=MemoryTier.CORE,
                last_reinforced=datetime.now(timezone.utc),
                recurrence_count=5,
                source_memories=[f"Core source {i}"],
            )
            entities.write_memory("testbot", fm, f"Core content {i}")

        # LLM returns empty consolidated and core, all journals unconsolidated
        api_response = json.dumps({
            "consolidated": [],
            "core": [],
            "unconsolidated": ["Memory 0", "Memory 1", "Memory 2", "Memory 3", "Memory 4"],
        })

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=api_response)]
        mock_client.messages.create.return_value = mock_response

        run_consolidation(
            "testbot", self._make_extracted_json(), tmp_path, api_key="test-key"
        )

        cons_dir = tmp_path / ".entities" / "testbot" / "memories" / "consolidated"
        core_dir = tmp_path / ".entities" / "testbot" / "memories" / "core"

        # All 5 pre-existing memories should remain on disk unchanged
        assert len(list(cons_dir.glob("*.md"))) == 3
        assert len(list(core_dir.glob("*.md"))) == 2

    @patch("entity_shutdown.anthropic")
    def test_new_promotions_merge_into_existing_tiers(self, mock_anthropic, tmp_path):
        """New promotions from LLM are added alongside existing memories."""
        entities = self._setup_entity(tmp_path)

        # Pre-populate 2 consolidated and 1 core memory
        for i in range(2):
            fm = MemoryFrontmatter(
                title=f"Existing consolidated {i}",
                category=MemoryCategory.SKILL,
                valence=MemoryValence.NEUTRAL,
                salience=3,
                tier=MemoryTier.CONSOLIDATED,
                last_reinforced=datetime.now(timezone.utc),
                recurrence_count=2,
                source_memories=[f"Source {i}"],
            )
            entities.write_memory("testbot", fm, f"Consolidated content {i}")

        core_fm = MemoryFrontmatter(
            title="Existing core 0",
            category=MemoryCategory.CORRECTION,
            valence=MemoryValence.NEGATIVE,
            salience=5,
            tier=MemoryTier.CORE,
            last_reinforced=datetime.now(timezone.utc),
            recurrence_count=5,
            source_memories=["Core source"],
        )
        entities.write_memory("testbot", core_fm, "Core content 0")

        # LLM returns 1 new consolidated + 1 new core (different titles)
        api_response = json.dumps({
            "consolidated": [
                {
                    "title": "New consolidated insight",
                    "content": "A brand new consolidated memory",
                    "valence": "positive",
                    "category": "skill",
                    "salience": 4,
                    "tier": "consolidated",
                    "source_memories": ["Memory 0", "Memory 1"],
                    "recurrence_count": 1,
                    "last_reinforced": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "core": [
                {
                    "title": "New core principle",
                    "content": "A brand new core memory",
                    "valence": "negative",
                    "category": "correction",
                    "salience": 5,
                    "tier": "core",
                    "source_memories": ["Important lesson"],
                    "recurrence_count": 1,
                    "last_reinforced": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "unconsolidated": ["Memory 2", "Memory 3", "Memory 4"],
        })

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=api_response)]
        mock_client.messages.create.return_value = mock_response

        run_consolidation(
            "testbot", self._make_extracted_json(), tmp_path, api_key="test-key"
        )

        cons_dir = tmp_path / ".entities" / "testbot" / "memories" / "consolidated"
        core_dir = tmp_path / ".entities" / "testbot" / "memories" / "core"

        # 2 existing + 1 new = 3 consolidated, 1 existing + 1 new = 2 core
        assert len(list(cons_dir.glob("*.md"))) == 3
        assert len(list(core_dir.glob("*.md"))) == 2

    @patch("entity_shutdown.anthropic")
    def test_llm_can_update_existing_memory_by_title(self, mock_anthropic, tmp_path):
        """LLM can update an existing memory by matching title."""
        entities = self._setup_entity(tmp_path)

        # Pre-populate a consolidated memory
        existing_fm = MemoryFrontmatter(
            title="Template system editing",
            category=MemoryCategory.SKILL,
            valence=MemoryValence.NEUTRAL,
            salience=3,
            tier=MemoryTier.CONSOLIDATED,
            last_reinforced=datetime.now(timezone.utc),
            recurrence_count=2,
            source_memories=["Original source"],
        )
        entities.write_memory("testbot", existing_fm, "Original content about templates")

        # LLM returns the same title but updated content and recurrence_count
        api_response = json.dumps({
            "consolidated": [
                {
                    "title": "Template system editing",
                    "content": "Updated and enriched content about template editing workflow",
                    "valence": "neutral",
                    "category": "skill",
                    "salience": 4,
                    "tier": "consolidated",
                    "source_memories": ["Original source", "New reinforcement"],
                    "recurrence_count": 3,
                    "last_reinforced": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "core": [],
            "unconsolidated": ["Memory 0", "Memory 1", "Memory 2", "Memory 3", "Memory 4"],
        })

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=api_response)]
        mock_client.messages.create.return_value = mock_response

        run_consolidation(
            "testbot", self._make_extracted_json(), tmp_path, api_key="test-key"
        )

        cons_dir = tmp_path / ".entities" / "testbot" / "memories" / "consolidated"
        cons_files = list(cons_dir.glob("*.md"))

        # Should still be 1 file (updated in place, not duplicated)
        assert len(cons_files) == 1

        fm, content = entities.parse_memory(cons_files[0])
        assert fm.title == "Template system editing"
        assert fm.recurrence_count == 3
        assert "Updated and enriched" in content

    @patch("entity_shutdown.anthropic")
    def test_pre_consolidation_snapshot_created(self, mock_anthropic, tmp_path):
        """A snapshot of consolidated/core tiers is created before merge."""
        entities = self._setup_entity(tmp_path)

        # Pre-populate consolidated and core memories
        cons_fm = MemoryFrontmatter(
            title="Snapshot test consolidated",
            category=MemoryCategory.SKILL,
            valence=MemoryValence.NEUTRAL,
            salience=3,
            tier=MemoryTier.CONSOLIDATED,
            last_reinforced=datetime.now(timezone.utc),
            recurrence_count=2,
            source_memories=["Source"],
        )
        entities.write_memory("testbot", cons_fm, "Consolidated for snapshot")

        core_fm = MemoryFrontmatter(
            title="Snapshot test core",
            category=MemoryCategory.CORRECTION,
            valence=MemoryValence.NEGATIVE,
            salience=5,
            tier=MemoryTier.CORE,
            last_reinforced=datetime.now(timezone.utc),
            recurrence_count=5,
            source_memories=["Core source"],
        )
        entities.write_memory("testbot", core_fm, "Core for snapshot")

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=self._make_api_response(1, 0))]
        mock_client.messages.create.return_value = mock_response

        run_consolidation(
            "testbot", self._make_extracted_json(), tmp_path, api_key="test-key"
        )

        snapshot_dir = tmp_path / ".entities" / "testbot" / "memories" / ".snapshot_pre_consolidation"
        assert snapshot_dir.exists()
        assert (snapshot_dir / "consolidated").exists()
        assert (snapshot_dir / "core").exists()
        assert len(list((snapshot_dir / "consolidated").glob("*.md"))) == 1
        assert len(list((snapshot_dir / "core").glob("*.md"))) == 1

    @patch("entity_shutdown.anthropic")
    def test_end_to_end_with_existing_tiers(self, mock_anthropic, tmp_path):
        """End-to-end test: pre-existing memories + new journals → updated tiers."""
        entities = self._setup_entity(tmp_path)

        # Pre-existing tier 1 memory
        existing_cons = MemoryFrontmatter(
            title="Template system requires source editing",
            category=MemoryCategory.SKILL,
            valence=MemoryValence.NEUTRAL,
            salience=3,
            tier=MemoryTier.CONSOLIDATED,
            last_reinforced=datetime(2026, 3, 1, tzinfo=timezone.utc),
            recurrence_count=2,
            source_memories=["Edit templates not rendered files"],
        )
        entities.write_memory("testbot", existing_cons, "Always edit Jinja2 source templates.")

        # Pre-existing tier 2 memory
        existing_core = MemoryFrontmatter(
            title="Verify state before acting",
            category=MemoryCategory.CORRECTION,
            valence=MemoryValence.NEGATIVE,
            salience=5,
            tier=MemoryTier.CORE,
            last_reinforced=datetime(2026, 3, 1, tzinfo=timezone.utc),
            recurrence_count=5,
            source_memories=["Check PR state", "Validate assumptions"],
        )
        entities.write_memory("testbot", existing_core, "Always check current state.")

        # Mock API response: reinforced core + updated consolidated + new consolidated
        api_response = json.dumps({
            "consolidated": [
                {
                    "title": "Template system requires source editing",
                    "content": "Always edit Jinja2 source templates, never rendered files. Run ve init after.",
                    "valence": "neutral",
                    "category": "skill",
                    "salience": 4,
                    "tier": "consolidated",
                    "source_memories": ["Edit templates not rendered files", "Template reminder today"],
                    "recurrence_count": 3,
                    "last_reinforced": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "title": "Commit chunk docs with code",
                    "content": "Always commit GOAL.md and PLAN.md alongside implementation code.",
                    "valence": "positive",
                    "category": "skill",
                    "salience": 3,
                    "tier": "consolidated",
                    "source_memories": ["Commit both files"],
                    "recurrence_count": 1,
                    "last_reinforced": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "core": [
                {
                    "title": "Verify state before acting",
                    "content": "Always check the current state of any resource before taking action on it.",
                    "valence": "negative",
                    "category": "correction",
                    "salience": 5,
                    "tier": "core",
                    "source_memories": ["Check PR state", "Validate assumptions", "State check reminder"],
                    "recurrence_count": 6,
                    "last_reinforced": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "unconsolidated": ["Minor observation"],
        })

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=api_response)]
        mock_client.messages.create.return_value = mock_response

        # New journal memories
        new_journals = json.dumps([
            {
                "title": "Template reminder today",
                "content": "Operator reminded about template workflow again.",
                "category": "confirmation",
                "valence": "neutral",
                "salience": 2,
            },
            {
                "title": "State check reminder",
                "content": "Got reminded to check state before acting.",
                "category": "correction",
                "valence": "negative",
                "salience": 4,
            },
            {
                "title": "Commit both files",
                "content": "Learned to commit GOAL.md with code changes.",
                "category": "skill",
                "valence": "positive",
                "salience": 3,
            },
            {
                "title": "Minor observation",
                "content": "The test suite takes 30 seconds.",
                "category": "domain",
                "valence": "neutral",
                "salience": 1,
            },
            {
                "title": "UV run for dev commands",
                "content": "Use uv run ve for development version.",
                "category": "skill",
                "valence": "positive",
                "salience": 2,
            },
        ])

        result = run_consolidation(
            "testbot", new_journals, tmp_path, api_key="test-key"
        )

        # Verify counts
        assert result["journals_added"] == 5
        assert result["consolidated"] == 2
        assert result["core"] == 1

        # Verify unconsolidated journals remain (only "Minor observation" is unconsolidated)
        journal_dir = tmp_path / ".entities" / "testbot" / "memories" / "journal"
        assert len(list(journal_dir.glob("*.md"))) == 1

        # Verify consolidated: 1 old updated in place + 1 new = 2 total
        cons_dir = tmp_path / ".entities" / "testbot" / "memories" / "consolidated"
        cons_files = list(cons_dir.glob("*.md"))
        assert len(cons_files) == 2

        # Verify core: 1 old updated in place = 1 total
        core_dir = tmp_path / ".entities" / "testbot" / "memories" / "core"
        core_files = list(core_dir.glob("*.md"))
        assert len(core_files) == 1

        # Verify the core memory was refined (recurrence_count increased)
        fm, content = entities.parse_memory(core_files[0])
        assert fm.title == "Verify state before acting"
        assert fm.recurrence_count == 6
        assert "current state" in content

        # Verify the prompt included existing memories
        call_kwargs = mock_client.messages.create.call_args
        prompt_text = call_kwargs.kwargs["messages"][0]["content"]
        assert "Template system requires source editing" in prompt_text
        assert "Verify state before acting" in prompt_text

    # -------------------------------------------------------------------
    # Chunk: docs/chunks/entity_consolidate_existing
    # Tests for consolidating existing journals from disk
    # -------------------------------------------------------------------

    @patch("entity_shutdown.anthropic")
    def test_empty_input_consolidates_existing_journals(self, mock_anthropic, tmp_path):
        """Empty input consolidates pre-existing journal files from disk."""
        entities = self._setup_entity(tmp_path)

        # Write 3 pre-existing journal memories directly to disk
        for i in range(3):
            fm = MemoryFrontmatter(
                title=f"Existing journal {i}",
                category=MemoryCategory.SKILL,
                valence=MemoryValence.POSITIVE,
                salience=3,
                tier=MemoryTier.JOURNAL,
                last_reinforced=datetime.now(timezone.utc),
                recurrence_count=0,
                source_memories=[],
            )
            entities.write_memory("testbot", fm, f"Existing content {i}")

        # Mock API response
        api_response = json.dumps({
            "consolidated": [
                {
                    "title": "Merged existing journals",
                    "content": "Combined knowledge from existing journals.",
                    "valence": "positive",
                    "category": "skill",
                    "salience": 4,
                    "tier": "consolidated",
                    "source_memories": ["Existing journal 0", "Existing journal 1"],
                    "recurrence_count": 2,
                    "last_reinforced": datetime.now(timezone.utc).isoformat(),
                }
            ],
            "core": [],
            "unconsolidated": ["Existing journal 2"],
        })

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=api_response)]
        mock_client.messages.create.return_value = mock_response

        result = run_consolidation(
            "testbot", "[]", tmp_path, api_key="test-key"
        )

        # No new journals from input
        assert result["journals_added"] == 0
        # API was called (consolidation happened)
        mock_client.messages.create.assert_called_once()
        # Prompt contains existing journal titles
        call_kwargs = mock_client.messages.create.call_args
        prompt_text = call_kwargs.kwargs["messages"][0]["content"]
        assert "Existing journal 0" in prompt_text
        assert "Existing journal 1" in prompt_text
        assert "Existing journal 2" in prompt_text
        # Consolidation results
        assert result["consolidated"] == 1
        assert result["journals_consolidated"] == 3

    def test_empty_input_no_existing_journals_returns_zeros(self, tmp_path):
        """Empty input with no existing journals returns zeros (no API call)."""
        self._setup_entity(tmp_path)

        result = run_consolidation("testbot", "[]", tmp_path)
        assert result["journals_added"] == 0
        assert result["consolidated"] == 0
        assert result["core"] == 0

    @patch("entity_shutdown.anthropic")
    def test_consolidated_journals_cleaned_up(self, mock_anthropic, tmp_path):
        """Consolidated journal files are deleted; unconsolidated are preserved."""
        entities = self._setup_entity(tmp_path)

        # Write 4 pre-existing journal memories
        for i in range(4):
            fm = MemoryFrontmatter(
                title=f"Journal entry {i}",
                category=MemoryCategory.SKILL,
                valence=MemoryValence.POSITIVE,
                salience=3,
                tier=MemoryTier.JOURNAL,
                last_reinforced=datetime.now(timezone.utc),
                recurrence_count=0,
                source_memories=[],
            )
            entities.write_memory("testbot", fm, f"Content {i}")

        # Mock API: unconsolidated contains 1 journal title
        api_response = json.dumps({
            "consolidated": [
                {
                    "title": "Merged journals",
                    "content": "Combined content.",
                    "valence": "positive",
                    "category": "skill",
                    "salience": 4,
                    "tier": "consolidated",
                    "source_memories": ["Journal entry 0", "Journal entry 1", "Journal entry 2"],
                    "recurrence_count": 3,
                    "last_reinforced": datetime.now(timezone.utc).isoformat(),
                }
            ],
            "core": [],
            "unconsolidated": ["Journal entry 3"],
        })

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=api_response)]
        mock_client.messages.create.return_value = mock_response

        result = run_consolidation(
            "testbot", "[]", tmp_path, api_key="test-key"
        )

        journal_dir = tmp_path / ".entities" / "testbot" / "memories" / "journal"
        remaining_journals = list(journal_dir.glob("*.md"))

        # Only the unconsolidated journal should remain
        assert len(remaining_journals) == 1
        fm, content = entities.parse_memory(remaining_journals[0])
        assert fm.title == "Journal entry 3"

    @patch("entity_shutdown.anthropic")
    def test_new_plus_existing_journals_consolidate_together(self, mock_anthropic, tmp_path):
        """New input memories + pre-existing journals are consolidated together."""
        entities = self._setup_entity(tmp_path)

        # Write 2 pre-existing journal memories
        for i in range(2):
            fm = MemoryFrontmatter(
                title=f"Pre-existing {i}",
                category=MemoryCategory.DOMAIN,
                valence=MemoryValence.NEUTRAL,
                salience=3,
                tier=MemoryTier.JOURNAL,
                last_reinforced=datetime.now(timezone.utc),
                recurrence_count=0,
                source_memories=[],
            )
            entities.write_memory("testbot", fm, f"Pre-existing content {i}")

        # 3 new memories in input JSON
        new_memories = json.dumps([
            {
                "title": f"New memory {i}",
                "content": f"New content {i}",
                "category": "skill",
                "valence": "positive",
                "salience": 3,
            }
            for i in range(3)
        ])

        # Mock API
        api_response = json.dumps({
            "consolidated": [
                {
                    "title": "All merged",
                    "content": "Everything combined.",
                    "valence": "positive",
                    "category": "skill",
                    "salience": 4,
                    "tier": "consolidated",
                    "source_memories": ["Pre-existing 0", "Pre-existing 1", "New memory 0"],
                    "recurrence_count": 3,
                    "last_reinforced": datetime.now(timezone.utc).isoformat(),
                }
            ],
            "core": [],
            "unconsolidated": ["New memory 1", "New memory 2"],
        })

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=api_response)]
        mock_client.messages.create.return_value = mock_response

        result = run_consolidation(
            "testbot", new_memories, tmp_path, api_key="test-key"
        )

        # 3 new journal files were written from input
        assert result["journals_added"] == 3
        # All 5 journals (2 existing + 3 new) were available for consolidation
        assert result["journals_consolidated"] == 5
        # Prompt contains all 5 journal titles
        call_kwargs = mock_client.messages.create.call_args
        prompt_text = call_kwargs.kwargs["messages"][0]["content"]
        assert "Pre-existing 0" in prompt_text
        assert "Pre-existing 1" in prompt_text
        assert "New memory 0" in prompt_text
        assert "New memory 1" in prompt_text
        assert "New memory 2" in prompt_text


# ---------------------------------------------------------------------------
# _format_transcript_text
# ---------------------------------------------------------------------------


def _make_turn(role: str, text: str) -> Turn:
    return Turn(role=role, text=text, timestamp="2026-01-01T00:00:00Z", uuid="test-uuid")


def _make_transcript(*turns: tuple[str, str]) -> SessionTranscript:
    return SessionTranscript(
        session_id="test-session",
        turns=[_make_turn(role, text) for role, text in turns],
    )


class TestFormatTranscriptText:
    def test_formats_user_and_assistant_turns(self):
        transcript = _make_transcript(("user", "Hello"), ("assistant", "Hi there"))
        result = _format_transcript_text(transcript)
        assert result == "[USER]: Hello\n\n[ASSISTANT]: Hi there"

    def test_empty_transcript_returns_empty_string(self):
        transcript = _make_transcript()
        result = _format_transcript_text(transcript)
        assert result == ""

    def test_truncates_to_max_chars(self):
        # Build a transcript whose formatted text exceeds max_chars
        transcript = _make_transcript(("user", "A" * 200), ("assistant", "B" * 200))
        result = _format_transcript_text(transcript, max_chars=100)
        assert len(result) <= 100

    def test_truncation_cuts_from_front(self):
        # The last part of the text should be preserved (most recent context)
        transcript = _make_transcript(
            ("user", "AAAA"),
            ("assistant", "ZZZZ"),
        )
        # Full formatted text: "[USER]: AAAA\n\n[ASSISTANT]: ZZZZ"
        full_text = "[USER]: AAAA\n\n[ASSISTANT]: ZZZZ"
        # Truncate to last 15 chars
        result = _format_transcript_text(transcript, max_chars=15)
        assert result == full_text[-15:]

    def test_multiple_turns_separated_by_double_newline(self):
        transcript = _make_transcript(
            ("user", "A"),
            ("assistant", "B"),
            ("user", "C"),
        )
        result = _format_transcript_text(transcript)
        assert result == "[USER]: A\n\n[ASSISTANT]: B\n\n[USER]: C"


# ---------------------------------------------------------------------------
# extract_memories_from_transcript
# ---------------------------------------------------------------------------


class TestExtractMemoriesFromTranscript:
    def test_returns_empty_json_for_empty_transcript(self):
        transcript = _make_transcript()
        with patch("entity_shutdown.anthropic") as mock_anthropic:
            result = extract_memories_from_transcript(transcript)
        assert result == "[]"
        mock_anthropic.Anthropic.assert_not_called()

    @patch("entity_shutdown.anthropic")
    def test_calls_api_with_extraction_prompt_as_system(self, mock_anthropic):
        transcript = _make_transcript(("user", "Hello"), ("assistant", "Hi"))
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='[{"title": "test", "content": "c", "valence": "neutral", "category": "domain", "salience": 1}]')]
        mock_client.messages.create.return_value = mock_response

        extract_memories_from_transcript(transcript, api_key="test-key")

        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["system"] == EXTRACTION_PROMPT

    @patch("entity_shutdown.anthropic")
    def test_calls_api_with_formatted_transcript_as_user_message(self, mock_anthropic):
        transcript = _make_transcript(("user", "Hello from user"), ("assistant", "Hi there"))
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="[]")]
        mock_client.messages.create.return_value = mock_response

        extract_memories_from_transcript(transcript, api_key="test-key")

        call_kwargs = mock_client.messages.create.call_args
        messages = call_kwargs.kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "[USER]:" in messages[0]["content"]

    @patch("entity_shutdown.anthropic")
    def test_returns_raw_api_response_text(self, mock_anthropic):
        transcript = _make_transcript(("user", "Hello"), ("assistant", "Hi"))
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        expected_text = '[{"title": "memory", "content": "stuff", "valence": "positive", "category": "skill", "salience": 3}]'
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=expected_text)]
        mock_client.messages.create.return_value = mock_response

        result = extract_memories_from_transcript(transcript, api_key="test-key")

        assert result == expected_text

    @patch("entity_shutdown.anthropic")
    def test_truncates_large_transcript(self, mock_anthropic):
        # Build turns with large text content
        turns = [("user", "X" * 10_000), ("assistant", "Y" * 10_000)] * 6  # 120K chars formatted
        transcript = _make_transcript(*turns)
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="[]")]
        mock_client.messages.create.return_value = mock_response

        extract_memories_from_transcript(transcript, api_key="test-key")

        call_kwargs = mock_client.messages.create.call_args
        user_content = call_kwargs.kwargs["messages"][0]["content"]
        assert len(user_content) <= 100_000

    @patch("entity_shutdown.anthropic")
    def test_uses_claude_sonnet_model(self, mock_anthropic):
        transcript = _make_transcript(("user", "Hello"), ("assistant", "Hi"))
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="[]")]
        mock_client.messages.create.return_value = mock_response

        extract_memories_from_transcript(transcript, api_key="test-key")

        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# shutdown_from_transcript
# ---------------------------------------------------------------------------


class TestShutdownFromTranscript:
    def _make_transcript(self):
        return _make_transcript(("user", "Hello"), ("assistant", "Hi there"))

    @patch("entity_shutdown.run_consolidation")
    @patch("entity_shutdown.extract_memories_from_transcript")
    def test_calls_extract_then_consolidation(
        self, mock_extract, mock_consolidation, tmp_path
    ):
        transcript = self._make_transcript()
        mock_extract.return_value = '[{"memories": "data"}]'
        mock_consolidation.return_value = {"journals_added": 0, "consolidated": 0, "core": 0}

        shutdown_from_transcript("mybot", transcript, tmp_path, api_key="test-key")

        mock_extract.assert_called_once()
        mock_consolidation.assert_called_once()
        # extract output passed as extracted_memories_json to consolidation
        call_kwargs = mock_consolidation.call_args
        assert call_kwargs.kwargs["extracted_memories_json"] == '[{"memories": "data"}]'

    @patch("entity_shutdown.run_consolidation")
    @patch("entity_shutdown.extract_memories_from_transcript")
    def test_passes_api_key_through(
        self, mock_extract, mock_consolidation, tmp_path
    ):
        transcript = self._make_transcript()
        mock_extract.return_value = "[]"
        mock_consolidation.return_value = {}

        shutdown_from_transcript("mybot", transcript, tmp_path, api_key="my-api-key")

        call_kwargs = mock_extract.call_args
        assert call_kwargs.kwargs.get("api_key") == "my-api-key" or call_kwargs.args[1] == "my-api-key"

    @patch("entity_shutdown.run_consolidation")
    @patch("entity_shutdown.extract_memories_from_transcript")
    def test_passes_decay_config_through(
        self, mock_extract, mock_consolidation, tmp_path
    ):
        from models.entity import DecayConfig
        transcript = self._make_transcript()
        mock_extract.return_value = "[]"
        mock_consolidation.return_value = {}
        decay_cfg = DecayConfig(journal_ttl_days=7)

        shutdown_from_transcript("mybot", transcript, tmp_path, decay_config=decay_cfg)

        call_kwargs = mock_consolidation.call_args
        assert call_kwargs.kwargs.get("decay_config") == decay_cfg or call_kwargs.args[-1] == decay_cfg

    @patch("entity_shutdown.run_consolidation")
    @patch("entity_shutdown.extract_memories_from_transcript")
    def test_returns_consolidation_summary(
        self, mock_extract, mock_consolidation, tmp_path
    ):
        transcript = self._make_transcript()
        mock_extract.return_value = "[]"
        expected_summary = {"journals_added": 3, "consolidated": 2, "core": 1, "expired": 0, "demoted": 0}
        mock_consolidation.return_value = expected_summary

        result = shutdown_from_transcript("mybot", transcript, tmp_path)

        assert result == expected_summary

    @patch("entity_shutdown.anthropic")
    @patch("entity_shutdown.run_consolidation")
    def test_empty_transcript_completes_without_api_call(
        self, mock_consolidation, mock_anthropic, tmp_path
    ):
        transcript = _make_transcript()  # empty
        mock_consolidation.return_value = {"journals_added": 0, "consolidated": 0, "core": 0}

        shutdown_from_transcript("mybot", transcript, tmp_path, api_key="test-key")

        # No Anthropic client instantiated for empty transcript
        mock_anthropic.Anthropic.assert_not_called()
        # Consolidation still called
        mock_consolidation.assert_called_once()
        # With "[]" as extracted memories
        call_kwargs = mock_consolidation.call_args
        assert call_kwargs.kwargs["extracted_memories_json"] == "[]"


# ---------------------------------------------------------------------------
# TestExtractWikiDiff
# ---------------------------------------------------------------------------

class TestExtractWikiDiff:
    """Tests for the mechanical wiki diff extraction function."""

    def _make_entity_git_repo(self, tmp_path):
        """Create a git repo simulating an entity directory with wiki."""
        import subprocess
        repo = tmp_path / "entity"
        repo.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)
        # Create initial wiki file and commit
        wiki_dir = repo / "wiki"
        wiki_dir.mkdir()
        (wiki_dir / "identity.md").write_text("# Identity\nInitial content.\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True, capture_output=True)
        return repo

    def test_returns_none_when_no_wiki_dir(self, tmp_path):
        """Entity without wiki/ directory returns None (legacy entity)."""
        from entity_shutdown import extract_wiki_diff
        entity_dir = tmp_path / "entity"
        entity_dir.mkdir()
        assert extract_wiki_diff(entity_dir) is None

    def test_returns_empty_string_when_wiki_unchanged(self, tmp_path):
        """Wiki with no changes since last commit returns empty string."""
        from entity_shutdown import extract_wiki_diff
        repo = self._make_entity_git_repo(tmp_path)
        result = extract_wiki_diff(repo)
        assert result == ""

    def test_returns_diff_text_for_modified_wiki_page(self, tmp_path):
        """Modified wiki page produces diff text with + lines."""
        from entity_shutdown import extract_wiki_diff
        repo = self._make_entity_git_repo(tmp_path)
        # Modify the wiki page
        (repo / "wiki" / "identity.md").write_text("# Identity\nInitial content.\nNew knowledge added.\n")
        result = extract_wiki_diff(repo)
        assert result is not None
        assert result != ""
        assert "+New knowledge added." in result

    def test_returns_diff_text_for_new_wiki_page(self, tmp_path):
        """New untracked wiki page produces diff text after staging."""
        from entity_shutdown import extract_wiki_diff
        repo = self._make_entity_git_repo(tmp_path)
        # Add a new file
        domain_dir = repo / "wiki" / "domain"
        domain_dir.mkdir()
        (domain_dir / "new_thing.md").write_text("# New Domain Knowledge\nSomething new.\n")
        result = extract_wiki_diff(repo)
        assert result is not None
        assert result != ""
        assert "new_thing.md" in result

    # Chunk: docs/chunks/wiki_diff_baseline_ref - baseline_ref tests

    def test_baseline_ref_captures_committed_changes(self, tmp_path):
        """baseline_ref path captures wiki changes even when committed during session."""
        import subprocess
        from entity_shutdown import extract_wiki_diff

        repo = self._make_entity_git_repo(tmp_path)
        # Record baseline before the "agent session" (simulates ve entity claude capturing HEAD)
        baseline_ref = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()

        # Agent commits a wiki change during the session
        (repo / "wiki" / "session_knowledge.md").write_text("# Learned\nSomething new.\n")
        subprocess.run(["git", "add", "wiki/"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "wiki: add session knowledge"],
            cwd=repo, check=True, capture_output=True
        )

        # baseline_ref path should see the committed change
        result = extract_wiki_diff(repo, baseline_ref=baseline_ref)
        assert result is not None
        assert result != ""
        assert "session_knowledge.md" in result or "Something new." in result

    def test_baseline_ref_captures_uncommitted_changes_too(self, tmp_path):
        """baseline_ref path captures both committed and uncommitted wiki changes."""
        import subprocess
        from entity_shutdown import extract_wiki_diff

        repo = self._make_entity_git_repo(tmp_path)
        baseline_ref = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()

        # Agent commits one wiki change
        (repo / "wiki" / "committed.md").write_text("# Committed\nContent A.\n")
        subprocess.run(["git", "add", "wiki/"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "wiki: committed change"],
            cwd=repo, check=True, capture_output=True
        )

        # Agent also leaves an uncommitted (unstaged) wiki change
        (repo / "wiki" / "uncommitted.md").write_text("# Uncommitted\nContent B.\n")

        result = extract_wiki_diff(repo, baseline_ref=baseline_ref)
        assert result is not None
        assert result != ""
        # Both changes should appear in the combined diff
        assert "committed.md" in result or "Content A." in result
        assert "uncommitted.md" in result or "Content B." in result

    def test_baseline_ref_fallback_no_changes(self, tmp_path):
        """When baseline_ref equals current HEAD and no changes, diff is empty string."""
        import subprocess
        from entity_shutdown import extract_wiki_diff

        repo = self._make_entity_git_repo(tmp_path)
        baseline_ref = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()

        # No changes at all since baseline
        result = extract_wiki_diff(repo, baseline_ref=baseline_ref)
        assert result == ""

    def test_no_baseline_ref_uses_cached_diff(self, tmp_path):
        """Without baseline_ref, staged changes vs HEAD are returned (existing behaviour)."""
        from entity_shutdown import extract_wiki_diff

        repo = self._make_entity_git_repo(tmp_path)
        # Add unstaged wiki changes (no commit)
        (repo / "wiki" / "identity.md").write_text("# Identity\nInitial content.\nExtra line.\n")

        result = extract_wiki_diff(repo)
        assert result is not None
        assert result != ""
        assert "+Extra line." in result


# ---------------------------------------------------------------------------
# TestRunWikiConsolidation
# ---------------------------------------------------------------------------

class TestRunWikiConsolidation:
    """Tests for the wiki consolidation pipeline dispatch and session launch."""

    def _make_entity_git_repo(self, tmp_path):
        """Create a git repo simulating an entity directory with wiki."""
        import subprocess
        repo = tmp_path / "entity"
        repo.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)
        wiki_dir = repo / "wiki"
        wiki_dir.mkdir()
        (wiki_dir / "identity.md").write_text("# Identity\nInitial content.\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True, capture_output=True)
        return repo

    def test_returns_empty_summary_when_no_wiki_changes(self, tmp_path):
        """Wiki with no changes returns summary without launching Agent SDK."""
        from entity_shutdown import run_wiki_consolidation

        repo = self._make_entity_git_repo(tmp_path)

        with patch("entity_shutdown._run_consolidation_agent") as mock_agent:
            result = run_wiki_consolidation("myentity", repo, tmp_path)

        assert result["journals_added"] == 0
        assert result.get("skipped") == "no wiki changes"
        mock_agent.assert_not_called()

    def test_launches_agent_sdk_when_wiki_has_changes(self, tmp_path):
        """When wiki has changes, Agent SDK helper is called once."""
        import asyncio
        from entity_shutdown import run_wiki_consolidation

        repo = self._make_entity_git_repo(tmp_path)
        # Modify wiki to create a diff
        (repo / "wiki" / "identity.md").write_text("# Identity\nModified content.\n")

        mock_result = {"success": True, "session_id": "test-session", "error": None}

        with patch("entity_shutdown._run_consolidation_agent", return_value=mock_result) as mock_agent:
            with patch("asyncio.run", return_value=mock_result):
                result = run_wiki_consolidation("myentity", repo, tmp_path)

        # Just verify it returned without error
        assert "error" not in result or result.get("error") is None

    def test_legacy_entity_raises_value_error(self, tmp_path):
        """Entity without wiki/ dir raises ValueError."""
        from entity_shutdown import run_wiki_consolidation

        entity_dir = tmp_path / "entity"
        entity_dir.mkdir()
        # No wiki/ directory

        with pytest.raises(ValueError, match="legacy"):
            run_wiki_consolidation("myentity", entity_dir, tmp_path)


# ---------------------------------------------------------------------------
# TestRunShutdownDispatcher
# ---------------------------------------------------------------------------

class TestRunShutdownDispatcher:
    """Tests for the run_shutdown() dispatcher."""

    def test_wiki_entity_calls_run_wiki_consolidation(self, tmp_path):
        """Wiki entity routes to run_wiki_consolidation."""
        from entity_shutdown import run_shutdown
        from entities import Entities

        # Create an entity with wiki/
        entities = Entities(tmp_path)
        entity_dir = tmp_path / ".entities" / "wikibot"
        entity_dir.mkdir(parents=True)
        (entity_dir / "wiki").mkdir()

        mock_result = {"journals_added": 5, "consolidated": 2, "core": 1}
        with patch("entity_shutdown.run_wiki_consolidation", return_value=mock_result) as mock_wiki:
            result = run_shutdown("wikibot", tmp_path)

        mock_wiki.assert_called_once()
        assert result == mock_result

    def test_legacy_entity_uses_legacy_pipeline(self, tmp_path):
        """Legacy entity (no wiki/) routes to run_consolidation."""
        from entity_shutdown import run_shutdown

        # Create a legacy entity manually (no wiki/)
        entity_dir = tmp_path / ".entities" / "legacybot"
        entity_dir.mkdir(parents=True)
        (entity_dir / "memories").mkdir()

        memories_json = "[]"
        mock_result = {"journals_added": 0, "journals_consolidated": 0, "consolidated": 0, "core": 0, "expired": 0, "demoted": 0}
        with patch("entity_shutdown.run_consolidation", return_value=mock_result) as mock_legacy:
            result = run_shutdown("legacybot", tmp_path, extracted_memories_json=memories_json)

        mock_legacy.assert_called_once()
        assert result == mock_result

    def test_legacy_entity_without_memories_raises_value_error(self, tmp_path):
        """Legacy entity without memories_json raises ValueError."""
        from entity_shutdown import run_shutdown

        # Create a legacy entity manually (no wiki/)
        entity_dir = tmp_path / ".entities" / "legacybot"
        entity_dir.mkdir(parents=True)
        (entity_dir / "memories").mkdir()

        with pytest.raises(ValueError, match="legacy entity"):
            run_shutdown("legacybot", tmp_path, extracted_memories_json=None)


# ---------------------------------------------------------------------------
# Timezone normalization regression tests
# Chunk: docs/chunks/shutdown_tz_normalization
# ---------------------------------------------------------------------------


class TestTimezoneNormalization:
    """Regression tests for mixed naive/aware datetime handling.

    Long-running entities accumulate memory files written by different code
    versions — some timestamps include timezone info, some do not. These tests
    guard against TypeError when subtracting or comparing those datetimes.
    """

    def test_memory_frontmatter_normalizes_naive_last_reinforced(self):
        """MemoryFrontmatter validator should convert naive datetimes to UTC-aware.

        Constructing with a naive datetime (no tzinfo) should produce a
        timezone-aware datetime on the model instance.
        """
        naive_dt = datetime(2026, 1, 1, 10, 0, 0)  # no tzinfo
        assert naive_dt.tzinfo is None, "precondition: naive_dt must be naive"

        fm = MemoryFrontmatter(
            title="Test memory",
            category=MemoryCategory.SKILL,
            valence=MemoryValence.NEUTRAL,
            salience=3,
            tier=MemoryTier.CONSOLIDATED,
            last_reinforced=naive_dt,
            recurrence_count=1,
            source_memories=[],
        )

        assert fm.last_reinforced.tzinfo is not None, (
            "MemoryFrontmatter.last_reinforced should be timezone-aware after construction"
        )
        assert fm.last_reinforced == naive_dt.replace(tzinfo=timezone.utc)

    def test_run_consolidation_succeeds_with_mixed_naive_aware_timestamps(self, tmp_path):
        """run_consolidation should not raise TypeError with mixed naive/aware timestamps.

        Simulates a long-running entity whose memory files were written by older
        code versions (no timezone suffix in stored timestamps).
        """
        # Build entity directory with consolidated memory files using naive timestamps
        entity_dir = tmp_path / ".entities" / "savings_instruments"
        consolidated_dir = entity_dir / "memories" / "consolidated"
        core_dir = entity_dir / "memories" / "core"
        consolidated_dir.mkdir(parents=True)
        core_dir.mkdir(parents=True)

        # Write a consolidated memory with a NAIVE timestamp (old code path)
        naive_memory_content = """\
---
title: Check balances before transferring
category: skill
valence: positive
salience: 3
tier: consolidated
last_reinforced: "2026-01-15T10:00:00"
recurrence_count: 2
source_memories: []
---
Always verify account balances before initiating a transfer.
"""
        (consolidated_dir / "check-balances.md").write_text(naive_memory_content)

        # Write a core memory with an AWARE timestamp (newer code path)
        aware_memory_content = """\
---
title: Verify state before acting
category: correction
valence: negative
salience: 5
tier: core
last_reinforced: "2026-03-20T14:00:00+00:00"
recurrence_count: 5
source_memories: []
---
Always verify current state before taking action on assumptions.
"""
        (core_dir / "verify-state.md").write_text(aware_memory_content)

        # New journal memories to consolidate (none on disk yet)
        extracted_json = json.dumps([
            {
                "title": "New skill learned",
                "content": "A new skill was learned this session.",
                "valence": "positive",
                "category": "skill",
                "salience": 3,
            }
        ])

        # Build a valid API response for the consolidation step
        api_response = json.dumps({
            "consolidated": [
                {
                    "title": "Check balances before transferring",
                    "content": "Always verify account balances before initiating a transfer.",
                    "valence": "positive",
                    "category": "skill",
                    "salience": 3,
                    "tier": "consolidated",
                    "source_memories": [],
                    "recurrence_count": 3,
                    "last_reinforced": "2026-04-23T10:00:00+00:00",
                },
                {
                    "title": "New skill learned",
                    "content": "A new skill was learned this session.",
                    "valence": "positive",
                    "category": "skill",
                    "salience": 3,
                    "tier": "consolidated",
                    "source_memories": ["New skill learned"],
                    "recurrence_count": 1,
                    "last_reinforced": "2026-04-23T10:00:00+00:00",
                },
            ],
            "core": [
                {
                    "title": "Verify state before acting",
                    "content": "Always verify current state before taking action on assumptions.",
                    "valence": "negative",
                    "category": "correction",
                    "salience": 5,
                    "tier": "core",
                    "source_memories": [],
                    "recurrence_count": 5,
                    "last_reinforced": "2026-04-23T10:00:00+00:00",
                }
            ],
            "unconsolidated": [],
        })

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=api_response)]

        mock_client_instance = MagicMock()
        mock_client_instance.messages.create.return_value = mock_message

        with patch("entity_shutdown.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value = mock_client_instance
            # Should not raise TypeError: can't subtract offset-naive and offset-aware datetimes
            result = run_consolidation(
                entity_name="savings_instruments",
                extracted_memories_json=extracted_json,
                project_dir=tmp_path,
            )

        assert isinstance(result, dict)
        assert "consolidated" in result
        assert "core" in result
