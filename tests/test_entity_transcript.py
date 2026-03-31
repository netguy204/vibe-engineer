"""Tests for src/entity_transcript.py — transcript parsing, cleaning, filtering."""

import json
import pytest
from pathlib import Path

from entity_transcript import (
    Turn,
    SessionTranscript,
    clean_text,
    is_substantive_turn,
    parse_session_jsonl,
    resolve_session_jsonl_path,
)


# ---------------------------------------------------------------------------
# clean_text tests
# ---------------------------------------------------------------------------

class TestCleanText:
    def test_removes_system_reminder_tags(self):
        raw = "Hello\n<system-reminder>This is noise\nMultiple lines</system-reminder>\nWorld"
        result = clean_text(raw)
        assert "<system-reminder>" not in result
        assert "This is noise" not in result
        assert "Hello" in result
        assert "World" in result

    def test_removes_command_message_tags(self):
        raw = "Before<command-message>cmd content</command-message>After"
        result = clean_text(raw)
        assert "<command-message>" not in result
        assert "cmd content" not in result
        assert "Before" in result
        assert "After" in result

    def test_removes_command_name_tags(self):
        raw = "Run <command-name>/foo</command-name> now"
        result = clean_text(raw)
        assert "<command-name>" not in result
        assert "/foo" not in result
        assert "Run" in result
        assert "now" in result

    def test_removes_command_args_tags(self):
        raw = "Args: <command-args>--verbose</command-args> done"
        result = clean_text(raw)
        assert "<command-args>" not in result
        assert "--verbose" not in result
        assert "done" in result

    def test_removes_task_notification_tags(self):
        raw = "Real text\n<task-notification>task info here</task-notification>\nMore text"
        result = clean_text(raw)
        assert "<task-notification>" not in result
        assert "task info here" not in result
        assert "Real text" in result
        assert "More text" in result

    def test_removes_private_tmp_file_paths(self):
        raw = "See file /private/tmp/claude-501/foo/bar.txt for details"
        result = clean_text(raw)
        assert "/private/tmp/claude-501/foo/bar.txt" not in result
        assert "See file" in result
        assert "for details" in result

    def test_removes_private_tmp_path_with_digits(self):
        raw = "Path: /private/tmp/claude-12345/sessions/abc.json"
        result = clean_text(raw)
        assert "/private/tmp/claude-12345/sessions/abc.json" not in result

    def test_removes_uuids(self):
        raw = "Request id=3f2504e0-4f89-11d3-9a0c-0305e82c3301 done"
        result = clean_text(raw)
        assert "3f2504e0-4f89-11d3-9a0c-0305e82c3301" not in result
        assert "Request id=" in result
        assert "done" in result

    def test_removes_uppercase_uuids(self):
        raw = "UUID: 3F2504E0-4F89-11D3-9A0C-0305E82C3301"
        result = clean_text(raw)
        assert "3F2504E0-4F89-11D3-9A0C-0305E82C3301" not in result

    def test_collapses_excessive_blank_lines(self):
        raw = "Line one\n\n\n\nLine two\n\n\n\n\nLine three"
        result = clean_text(raw)
        # Should not have 3+ consecutive newlines
        assert "\n\n\n" not in result
        assert "Line one" in result
        assert "Line two" in result
        assert "Line three" in result

    def test_collapses_spaces_and_tabs(self):
        raw = "Hello   world\t\ttest"
        result = clean_text(raw)
        assert "Hello world" in result
        assert "test" in result
        # No double spaces
        assert "  " not in result

    def test_clean_text_unchanged_when_nothing_to_strip(self):
        raw = "This is normal text with no noise."
        result = clean_text(raw)
        assert "normal text with no noise" in result

    def test_multiline_tag_content_removed(self):
        raw = "Before\n<system-reminder>\nLine 1\nLine 2\nLine 3\n</system-reminder>\nAfter"
        result = clean_text(raw)
        assert "Line 1" not in result
        assert "Line 2" not in result
        assert "Before" in result
        assert "After" in result


# ---------------------------------------------------------------------------
# is_substantive_turn tests
# ---------------------------------------------------------------------------

class TestIsSubstantiveTurn:
    def _make_turn(self, text: str) -> Turn:
        return Turn(role="user", text=text, timestamp="", uuid="", tool_uses=[])

    def test_short_text_is_not_substantive(self):
        turn = self._make_turn("Hi")
        assert not is_substantive_turn(turn)

    def test_exactly_19_chars_is_not_substantive(self):
        turn = self._make_turn("A" * 19)
        assert not is_substantive_turn(turn)

    def test_exactly_20_chars_is_substantive(self):
        turn = self._make_turn("A" * 20)
        assert is_substantive_turn(turn)

    def test_whitespace_only_is_not_substantive(self):
        turn = self._make_turn("   \n\n\t  ")
        assert not is_substantive_turn(turn)

    def test_task_notification_only_is_not_substantive(self):
        # After cleaning, the remaining text should be < 20 chars
        turn = self._make_turn("<task-notification>some long task info here</task-notification>")
        assert not is_substantive_turn(turn)

    def test_real_content_is_substantive(self):
        turn = self._make_turn("Please implement the foo feature in the bar module.")
        assert is_substantive_turn(turn)

    def test_noise_tag_with_some_real_content_preserved(self):
        # 30 chars of real text + a task-notification; should be substantive
        turn = self._make_turn(
            "Here is my question for you today"
            "<task-notification>noise</task-notification>"
        )
        assert is_substantive_turn(turn)


# ---------------------------------------------------------------------------
# parse_session_jsonl tests
# ---------------------------------------------------------------------------

def _write_jsonl(path: Path, entries: list[dict]) -> None:
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


class TestParseSessionJsonl:
    def test_user_turn_string_content(self, tmp_path):
        jsonl = tmp_path / "abc123.jsonl"
        _write_jsonl(jsonl, [
            {
                "type": "user",
                "uuid": "u1",
                "timestamp": "2024-01-01T00:00:00Z",
                "message": {"content": "Hello, can you help me?"},
            }
        ])
        transcript = parse_session_jsonl(jsonl)
        assert transcript.session_id == "abc123"
        assert len(transcript.turns) == 1
        turn = transcript.turns[0]
        assert turn.role == "user"
        assert "Hello, can you help me?" in turn.text
        assert turn.uuid == "u1"
        assert turn.timestamp == "2024-01-01T00:00:00Z"

    def test_imeta_user_turn_is_skipped(self, tmp_path):
        jsonl = tmp_path / "sess.jsonl"
        _write_jsonl(jsonl, [
            {
                "type": "user",
                "isMeta": True,
                "uuid": "meta1",
                "timestamp": "2024-01-01T00:00:00Z",
                "message": {"content": "system context injection"},
            },
            {
                "type": "user",
                "uuid": "u2",
                "timestamp": "2024-01-01T00:01:00Z",
                "message": {"content": "A real user message here for testing"},
            },
        ])
        transcript = parse_session_jsonl(jsonl)
        assert len(transcript.turns) == 1
        assert transcript.turns[0].uuid == "u2"

    def test_file_history_snapshot_is_skipped(self, tmp_path):
        jsonl = tmp_path / "sess.jsonl"
        _write_jsonl(jsonl, [
            {"type": "file-history-snapshot", "files": ["foo.py"]},
            {
                "type": "user",
                "uuid": "u1",
                "timestamp": "2024-01-01T00:00:00Z",
                "message": {"content": "Real user message content here"},
            },
        ])
        transcript = parse_session_jsonl(jsonl)
        assert len(transcript.turns) == 1
        assert transcript.turns[0].role == "user"

    def test_assistant_text_block_extracted(self, tmp_path):
        jsonl = tmp_path / "sess.jsonl"
        _write_jsonl(jsonl, [
            {
                "type": "assistant",
                "requestId": "req1",
                "uuid": "a1",
                "timestamp": "2024-01-01T00:00:00Z",
                "message": {
                    "content": [
                        {"type": "text", "text": "Sure, I can help you with that task."}
                    ]
                },
            }
        ])
        transcript = parse_session_jsonl(jsonl)
        assert len(transcript.turns) == 1
        turn = transcript.turns[0]
        assert turn.role == "assistant"
        assert "Sure, I can help you with that task." in turn.text

    def test_assistant_continuations_merged(self, tmp_path):
        jsonl = tmp_path / "sess.jsonl"
        _write_jsonl(jsonl, [
            {
                "type": "assistant",
                "requestId": "req1",
                "uuid": "a1",
                "timestamp": "2024-01-01T00:00:00Z",
                "message": {"content": [{"type": "text", "text": "First part of response."}]},
            },
            {
                "type": "assistant",
                "requestId": "req1",
                "uuid": "a1b",
                "timestamp": "2024-01-01T00:00:01Z",
                "message": {"content": [{"type": "text", "text": "Second part of response."}]},
            },
        ])
        transcript = parse_session_jsonl(jsonl)
        assert len(transcript.turns) == 1
        assert "First part" in transcript.turns[0].text
        assert "Second part" in transcript.turns[0].text

    def test_different_request_ids_produce_separate_turns(self, tmp_path):
        jsonl = tmp_path / "sess.jsonl"
        _write_jsonl(jsonl, [
            {
                "type": "assistant",
                "requestId": "req1",
                "uuid": "a1",
                "timestamp": "2024-01-01T00:00:00Z",
                "message": {"content": [{"type": "text", "text": "First response text here."}]},
            },
            {
                "type": "assistant",
                "requestId": "req2",
                "uuid": "a2",
                "timestamp": "2024-01-01T00:01:00Z",
                "message": {"content": [{"type": "text", "text": "Second response text here."}]},
            },
        ])
        transcript = parse_session_jsonl(jsonl)
        assert len(transcript.turns) == 2
        assert transcript.turns[0].role == "assistant"
        assert transcript.turns[1].role == "assistant"

    def test_tool_names_captured_in_tool_uses(self, tmp_path):
        jsonl = tmp_path / "sess.jsonl"
        _write_jsonl(jsonl, [
            {
                "type": "assistant",
                "requestId": "req1",
                "uuid": "a1",
                "timestamp": "2024-01-01T00:00:00Z",
                "message": {
                    "content": [
                        {"type": "text", "text": "Running a command for you now."},
                        {"type": "tool_use", "name": "Bash", "input": {"command": "ls -la"}},
                    ]
                },
            }
        ])
        transcript = parse_session_jsonl(jsonl)
        assert len(transcript.turns) == 1
        turn = transcript.turns[0]
        assert "Bash" in turn.tool_uses
        # Tool input should not appear in text
        assert "ls -la" not in turn.text

    def test_tool_result_not_in_text(self, tmp_path):
        jsonl = tmp_path / "sess.jsonl"
        _write_jsonl(jsonl, [
            {
                "type": "assistant",
                "requestId": "req1",
                "uuid": "a1",
                "timestamp": "2024-01-01T00:00:00Z",
                "message": {
                    "content": [
                        {"type": "text", "text": "Here is the output summary for you."},
                        {"type": "tool_result", "content": "file contents: SECRET DATA"},
                    ]
                },
            }
        ])
        transcript = parse_session_jsonl(jsonl)
        turn = transcript.turns[0]
        assert "SECRET DATA" not in turn.text

    def test_user_message_with_content_blocks(self, tmp_path):
        """User messages can also have list content."""
        jsonl = tmp_path / "sess.jsonl"
        _write_jsonl(jsonl, [
            {
                "type": "user",
                "uuid": "u1",
                "timestamp": "2024-01-01T00:00:00Z",
                "message": {
                    "content": [
                        {"type": "text", "text": "What is the meaning of life, universe, everything?"}
                    ]
                },
            }
        ])
        transcript = parse_session_jsonl(jsonl)
        assert len(transcript.turns) == 1
        assert "meaning of life" in transcript.turns[0].text


# ---------------------------------------------------------------------------
# resolve_session_jsonl_path tests
# ---------------------------------------------------------------------------

class TestResolveSessionJsonlPath:
    def test_returns_archived_path_when_exists(self, tmp_path, monkeypatch):
        # Set up .entities/<name>/sessions/<session_id>.jsonl
        entity_dir = tmp_path / ".entities" / "myentity" / "sessions"
        entity_dir.mkdir(parents=True)
        session_file = entity_dir / "abc123.jsonl"
        session_file.write_text("{}")

        result = resolve_session_jsonl_path(str(tmp_path), "abc123")
        assert result == session_file

    def test_falls_back_to_claude_home_path(self, tmp_path, monkeypatch):
        # No entity archive — simulate ~/.claude/projects/<encoded>/<session_id>.jsonl
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        project_path = "/Users/foo/myproject"
        encoded = "-Users-foo-myproject"
        claude_dir = fake_home / ".claude" / "projects" / encoded
        claude_dir.mkdir(parents=True)
        session_file = claude_dir / "sess999.jsonl"
        session_file.write_text("{}")

        result = resolve_session_jsonl_path(project_path, "sess999")
        assert result == session_file

    def test_returns_none_when_not_found(self, tmp_path, monkeypatch):
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        result = resolve_session_jsonl_path(str(tmp_path), "nonexistent")
        assert result is None

    def test_encoding_replaces_slashes_with_dashes(self, tmp_path, monkeypatch):
        """Verify the path encoding: leading dash, slashes → dashes."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        project_path = "/Users/foo/bar"
        encoded = "-Users-foo-bar"
        claude_dir = fake_home / ".claude" / "projects" / encoded
        claude_dir.mkdir(parents=True)
        session_file = claude_dir / "s1.jsonl"
        session_file.write_text("{}")

        result = resolve_session_jsonl_path(project_path, "s1")
        assert result is not None
        assert encoded in str(result)

    def test_archived_path_preferred_over_claude_home(self, tmp_path, monkeypatch):
        """Archived path takes precedence over ~/.claude/ fallback."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        # Set up both locations
        entity_dir = tmp_path / ".entities" / "ent" / "sessions"
        entity_dir.mkdir(parents=True)
        archived = entity_dir / "sess1.jsonl"
        archived.write_text("{}")

        encoded = "-" + str(tmp_path).lstrip("/").replace("/", "-")
        claude_dir = fake_home / ".claude" / "projects" / encoded
        claude_dir.mkdir(parents=True)
        fallback = claude_dir / "sess1.jsonl"
        fallback.write_text("{}")

        result = resolve_session_jsonl_path(str(tmp_path), "sess1")
        assert result == archived
