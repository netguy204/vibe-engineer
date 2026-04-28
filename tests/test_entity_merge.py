"""Unit tests for entity_merge: parse_conflict_markers and resolve_wiki_conflict.

# Chunk: docs/chunks/entity_fork_merge - entity_merge unit tests
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import entity_merge
from entity_merge import ConflictHunk, parse_conflict_markers


SIMPLE_CONFLICT = """\
Before the conflict.
<<<<<<< HEAD
ours content here
=======
theirs content here
>>>>>>> branch-b
After the conflict.
"""

TWO_CONFLICTS = """\
Start.
<<<<<<< HEAD
first ours
=======
first theirs
>>>>>>> branch-b
Middle.
<<<<<<< HEAD
second ours
=======
second theirs
>>>>>>> branch-b
End.
"""

NO_CONFLICT = """\
# Clean File

No conflict markers here.
Just regular content.
"""


class TestParseConflictMarkers:
    def test_parses_single_conflict(self):
        hunks = parse_conflict_markers(SIMPLE_CONFLICT)
        assert len(hunks) == 1

    def test_ours_and_theirs_content_correct(self):
        hunks = parse_conflict_markers(SIMPLE_CONFLICT)
        assert hunks[0].ours == "ours content here"
        assert hunks[0].theirs == "theirs content here"

    def test_parses_multiple_conflicts(self):
        hunks = parse_conflict_markers(TWO_CONFLICTS)
        assert len(hunks) == 2

    def test_multiple_conflicts_content_correct(self):
        hunks = parse_conflict_markers(TWO_CONFLICTS)
        assert hunks[0].ours == "first ours"
        assert hunks[0].theirs == "first theirs"
        assert hunks[1].ours == "second ours"
        assert hunks[1].theirs == "second theirs"

    def test_returns_empty_for_clean_file(self):
        hunks = parse_conflict_markers(NO_CONFLICT)
        assert hunks == []

    def test_returns_list_of_conflict_hunk(self):
        hunks = parse_conflict_markers(SIMPLE_CONFLICT)
        assert isinstance(hunks[0], ConflictHunk)


class TestResolveWikiConflict:
    def _make_mock_anthropic(self, response_text: str):
        """Build a mock anthropic module that returns response_text."""
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=response_text)]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        return mock_anthropic_module, mock_client

    def test_returns_synthesized_content(self):
        mock_anthropic_module, _ = self._make_mock_anthropic("synthesized result")

        with patch.object(entity_merge, "ClaudeSDKClient", None):
            with patch.object(entity_merge, "anthropic", mock_anthropic_module):
                result = entity_merge.resolve_wiki_conflict(
                    "wiki/domain/test.md",
                    SIMPLE_CONFLICT,
                    "my-specialist",
                )

        assert result == "synthesized result"

    def test_calls_anthropic_messages_create(self):
        mock_anthropic_module, mock_client = self._make_mock_anthropic("synthesized")

        with patch.object(entity_merge, "ClaudeSDKClient", None):
            with patch.object(entity_merge, "anthropic", mock_anthropic_module):
                entity_merge.resolve_wiki_conflict(
                    "wiki/domain/test.md",
                    SIMPLE_CONFLICT,
                    "my-specialist",
                )

        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args
        # Verify both ours and theirs content appear in the prompt
        prompt_content = str(call_kwargs)
        assert "ours content here" in prompt_content or SIMPLE_CONFLICT in prompt_content

    def test_prompt_includes_filename(self):
        mock_anthropic_module, mock_client = self._make_mock_anthropic("result")

        with patch.object(entity_merge, "ClaudeSDKClient", None):
            with patch.object(entity_merge, "anthropic", mock_anthropic_module):
                entity_merge.resolve_wiki_conflict(
                    "wiki/domain/databases.md",
                    SIMPLE_CONFLICT,
                    "db-specialist",
                )

        call_kwargs = mock_client.messages.create.call_args
        prompt = str(call_kwargs)
        assert "databases.md" in prompt

    def test_prompt_includes_entity_name(self):
        mock_anthropic_module, mock_client = self._make_mock_anthropic("result")

        with patch.object(entity_merge, "ClaudeSDKClient", None):
            with patch.object(entity_merge, "anthropic", mock_anthropic_module):
                entity_merge.resolve_wiki_conflict(
                    "wiki/test.md",
                    SIMPLE_CONFLICT,
                    "my-cool-specialist",
                )

        call_kwargs = mock_client.messages.create.call_args
        prompt = str(call_kwargs)
        assert "my-cool-specialist" in prompt

    def test_raises_if_anthropic_not_available(self):
        with patch.object(entity_merge, "ClaudeSDKClient", None):
            with patch.object(entity_merge, "anthropic", None):
                with pytest.raises(RuntimeError, match="anthropic"):
                    entity_merge.resolve_wiki_conflict(
                        "wiki/test.md",
                        SIMPLE_CONFLICT,
                        "my-specialist",
                    )

    # -----------------------------------------------------------------------
    # Agent SDK path tests
    # -----------------------------------------------------------------------

    def test_model_constant_is_not_haiku_latest(self):
        """The retired claude-3-5-haiku-latest model is no longer referenced."""
        assert entity_merge._RESOLVER_MODEL != "claude-3-5-haiku-latest"

    def test_agent_sdk_path_used_when_available(self):
        """When ClaudeSDKClient is available, anthropic.Anthropic() is NOT called."""
        mock_anthropic = MagicMock()

        async def fake_resolver(prompt, cwd):
            return "agent result"

        with patch.object(entity_merge, "ClaudeSDKClient", MagicMock()):
            with patch.object(entity_merge, "_resolve_with_agent_sdk", fake_resolver):
                with patch.object(entity_merge, "anthropic", mock_anthropic):
                    result = entity_merge.resolve_wiki_conflict(
                        "wiki/test.md",
                        SIMPLE_CONFLICT,
                        "my-specialist",
                    )

        assert result == "agent result"
        mock_anthropic.Anthropic.assert_not_called()

    def test_agent_sdk_result_returned(self):
        """resolve_wiki_conflict returns the string produced by the agent SDK."""
        expected = "# Synthesized content\n\nMerged knowledge here.\n"

        async def fake_resolver(prompt, cwd):
            return expected

        with patch.object(entity_merge, "ClaudeSDKClient", MagicMock()):
            with patch.object(entity_merge, "_resolve_with_agent_sdk", fake_resolver):
                result = entity_merge.resolve_wiki_conflict(
                    "wiki/domain/page.md",
                    SIMPLE_CONFLICT,
                    "specialist",
                )

        assert result == expected

    def test_agent_sdk_receives_entity_dir(self, tmp_path):
        """entity_dir is forwarded to _resolve_with_agent_sdk as cwd."""
        received_cwd = []

        async def capturing_resolver(prompt, cwd):
            received_cwd.append(cwd)
            return "result"

        with patch.object(entity_merge, "ClaudeSDKClient", MagicMock()):
            with patch.object(entity_merge, "_resolve_with_agent_sdk", capturing_resolver):
                entity_merge.resolve_wiki_conflict(
                    "wiki/test.md",
                    SIMPLE_CONFLICT,
                    "specialist",
                    entity_dir=tmp_path,
                )

        assert received_cwd[0] == tmp_path

    def test_fallback_to_anthropic_sdk_when_agent_unavailable(self):
        """When ClaudeSDKClient is None, the Anthropic SDK path is used."""
        mock_anthropic_module, mock_client = self._make_mock_anthropic("fallback result")

        with patch.object(entity_merge, "ClaudeSDKClient", None):
            with patch.object(entity_merge, "anthropic", mock_anthropic_module):
                result = entity_merge.resolve_wiki_conflict(
                    "wiki/test.md",
                    SIMPLE_CONFLICT,
                    "my-specialist",
                )

        assert result == "fallback result"
        mock_client.messages.create.assert_called_once()

    def test_fallback_error_mentions_api_key(self):
        """When both SDKs are unavailable, the error message mentions ANTHROPIC_API_KEY."""
        with patch.object(entity_merge, "ClaudeSDKClient", None):
            with patch.object(entity_merge, "anthropic", None):
                with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                    entity_merge.resolve_wiki_conflict(
                        "wiki/test.md",
                        SIMPLE_CONFLICT,
                        "my-specialist",
                    )

    def test_fallback_error_mentions_claude_agent_sdk(self):
        """When both SDKs are unavailable, the error message mentions claude_agent_sdk."""
        with patch.object(entity_merge, "ClaudeSDKClient", None):
            with patch.object(entity_merge, "anthropic", None):
                with pytest.raises(RuntimeError, match="claude.agent.sdk"):
                    entity_merge.resolve_wiki_conflict(
                        "wiki/test.md",
                        SIMPLE_CONFLICT,
                        "my-specialist",
                    )
