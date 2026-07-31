"""CLI integration tests for `ve hooks`.

The contract these tests defend is unusual: `ve hooks show` is invoked from
inside the `!`-prefixed context block of every plugin command. It must exit 0
in every circumstance - including for garbage input - because a non-zero exit
there is a failure the agent has to reason about in a command that isn't about
hooks.

# Chunk: docs/chunks/hooks_lifecycle_fragments - ve hooks CLI surface
"""

import json

import pytest

from ve import cli

from test_hooks import write_hook


@pytest.fixture
def show(runner, temp_project):
    """Invoke `ve hooks show <event>` against the temp project."""

    def _show(event: str, *extra):
        return runner.invoke(
            cli, ["hooks", "show", event, "--project-dir", str(temp_project), *extra]
        )

    return _show


@pytest.fixture
def hook_list(runner, temp_project):
    """Invoke `ve hooks list` against the temp project."""

    def _list(*extra):
        return runner.invoke(
            cli, ["hooks", "list", "--project-dir", str(temp_project), *extra]
        )

    return _list


class TestShow:
    """`ve hooks show` - the command embedded in every context block."""

    def test_absent_hook_reports_explicit_negative(self, show):
        """A blank value in a context bullet reads as a broken command."""
        result = show("chunk-complete")

        assert result.exit_code == 0
        assert "(no project hook)" in result.output

    def test_present_hook_is_printed_with_its_source(self, show, temp_project):
        write_hook(temp_project, "chunk-complete", "Update the public docs.\n")

        result = show("chunk-complete")

        assert result.exit_code == 0
        assert "Update the public docs." in result.output
        assert "docs/hooks/chunk-complete.md" in result.output

    def test_frontmatter_does_not_reach_the_output(self, show, temp_project):
        """Machinery must not be presented to the agent as instruction."""
        write_hook(
            temp_project,
            "chunk-complete",
            "---\nchecks:\n  - make docs\n---\nUpdate the docs.\n",
        )

        result = show("chunk-complete")

        assert result.exit_code == 0
        assert "checks" not in result.output
        assert "Update the docs." in result.output

    def test_unknown_event_name_still_exits_zero(self, show):
        """Regression guard for the context-block contract: an event name that
        is not a command must not fail the command that invoked it."""
        result = show("not-a-real-command")

        assert result.exit_code == 0
        assert "(no project hook)" in result.output

    def test_path_traversal_exits_zero_without_leaking(self, show, temp_project):
        (temp_project / "secret.md").write_text("do not read me\n")

        result = show("../secret")

        assert result.exit_code == 0
        assert "do not read me" not in result.output

    def test_unreadable_hook_exits_zero(self, show, temp_project):
        import os

        path = write_hook(temp_project, "chunk-complete", "Secret.\n")
        path.chmod(0o000)
        try:
            if os.access(path, os.R_OK):
                pytest.skip("filesystem or privileges ignore chmod 000")

            result = show("chunk-complete")

            assert result.exit_code == 0
            assert "(no project hook)" in result.output
        finally:
            path.chmod(0o644)

    def test_absent_project_dir_exits_zero(self, runner, temp_project):
        """A path that does not exist must degrade, not explode - the context
        line runs wherever the agent happens to be."""
        result = runner.invoke(
            cli,
            ["hooks", "show", "chunk-complete", "--project-dir", str(temp_project / "nope")],
        )

        assert result.exit_code == 0
        assert "(no project hook)" in result.output


class TestList:
    """`ve hooks list` - surfacing hooks that will never fire."""

    def test_empty_project_lists_nothing_and_succeeds(self, hook_list):
        result = hook_list()

        assert result.exit_code == 0

    def test_known_hook_is_listed_without_a_warning(self, hook_list, temp_project):
        write_hook(temp_project, "chunk-complete", "Body.\n")

        result = hook_list()

        assert result.exit_code == 0
        assert "chunk-complete" in result.output
        assert "UNKNOWN" not in result.output

    def test_misspelled_hook_is_flagged(self, hook_list, temp_project):
        """An operator who writes chunk-completed.md must learn it from
        tooling, not from the hook silently never firing."""
        write_hook(temp_project, "chunk-completed", "Body.\n")

        result = hook_list()

        assert result.exit_code == 0
        assert "chunk-completed" in result.output
        assert "UNKNOWN" in result.output

    def test_flagging_an_unknown_hook_does_not_fail_the_command(
        self, hook_list, temp_project
    ):
        """Version skew between CLI and plugin (DEC-011) can make a legitimate
        hook look unknown; that must never fail anyone's build."""
        write_hook(temp_project, "invented-by-a-newer-plugin", "Body.\n")

        assert hook_list().exit_code == 0

    def test_json_output_reports_events_and_known_flags(
        self, hook_list, temp_project
    ):
        write_hook(temp_project, "chunk-complete", "a\n")
        write_hook(temp_project, "chunk-completed", "b\n")

        result = hook_list("--json")

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert {(e["event"], e["known"]) for e in payload} == {
            ("chunk-complete", True),
            ("chunk-completed", False),
        }
