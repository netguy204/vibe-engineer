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
    format_consolidation_prompt,
    parse_consolidation_response,
    parse_extracted_memories,
    run_consolidation,
    strip_code_fences,
)
from entities import Entities
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
        assert len(journal_files) == 5
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
        assert result == {"journals_added": 0, "consolidated": 0, "core": 0, "expired": 0, "demoted": 0}

    def test_returns_zeros_on_invalid_json(self, tmp_path):
        """Returns zeros when input is not valid JSON."""
        self._setup_entity(tmp_path)

        result = run_consolidation("testbot", "not json", tmp_path)
        assert result == {"journals_added": 0, "consolidated": 0, "core": 0, "expired": 0, "demoted": 0}

    @patch("entity_shutdown.anthropic")
    def test_replaces_existing_tiers(self, mock_anthropic, tmp_path):
        """Existing consolidated/core files are replaced, not appended."""
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

        # Old files should be replaced
        cons_dir = tmp_path / ".entities" / "testbot" / "memories" / "consolidated"
        core_dir = tmp_path / ".entities" / "testbot" / "memories" / "core"

        cons_files = list(cons_dir.glob("*.md"))
        core_files = list(core_dir.glob("*.md"))

        # Only the new ones from API response
        assert len(cons_files) == 1
        assert len(core_files) == 1

        # Verify content is from the new response, not old
        _, content = entities.parse_memory(cons_files[0])
        assert "Merged skill" in content

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

        # Verify journals exist
        journal_dir = tmp_path / ".entities" / "testbot" / "memories" / "journal"
        assert len(list(journal_dir.glob("*.md"))) == 5

        # Verify consolidated: old single file replaced by 2 new ones
        cons_dir = tmp_path / ".entities" / "testbot" / "memories" / "consolidated"
        cons_files = list(cons_dir.glob("*.md"))
        assert len(cons_files) == 2

        # Verify core: old single file replaced by 1 updated one
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
