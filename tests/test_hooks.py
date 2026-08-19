"""Unit tests for the VE hooks module.

VE hooks are operator-authored instruction fragments in docs/hooks/<command>.md
that lifecycle commands inject into their context block. The load-bearing
property under test is total-functionness: this code runs inside the `!`-prefixed
context lines of *every* plugin command, so any exception here corrupts the
prompt of a command that has nothing to do with hooks.

# Chunk: docs/chunks/hooks_lifecycle_fragments - VE hook resolution and rendering
"""

import os
import pathlib

import pytest

from hooks import KNOWN_EVENTS, Hooks


def write_hook(project_dir: pathlib.Path, event: str, content: str) -> pathlib.Path:
    """Write docs/hooks/<event>.md under project_dir, creating parents."""
    hooks_dir = project_dir / "docs" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    path = hooks_dir / f"{event}.md"
    path.write_text(content)
    return path


class TestResolve:
    """Resolution of docs/hooks/<event>.md into a HookFragment."""

    def test_absent_hooks_directory_resolves_to_none(self, temp_project):
        """A project that has never heard of hooks resolves to nothing."""
        assert Hooks(temp_project).resolve("chunk-complete") is None

    def test_absent_fragment_resolves_to_none(self, temp_project):
        """An existing docs/hooks/ without the requested event resolves to nothing."""
        write_hook(temp_project, "chunk-create", "Something else.\n")

        assert Hooks(temp_project).resolve("chunk-complete") is None

    def test_bare_prose_body_round_trips_verbatim(self, temp_project):
        """Operator prose survives resolution unmodified, with no metadata."""
        body = "Did this chunk change public docs?\n\nIf so, update them.\n"
        write_hook(temp_project, "chunk-complete", body)

        fragment = Hooks(temp_project).resolve("chunk-complete")

        assert fragment is not None
        assert fragment.body == body
        assert fragment.metadata == {}
        assert fragment.event == "chunk-complete"

    def test_frontmatter_is_parsed_and_kept_out_of_the_body(self, temp_project):
        """The forward-compatibility seam: a future checks: key must not leak
        into the prompt as if it were an instruction."""
        write_hook(
            temp_project,
            "chunk-complete",
            "---\nchecks:\n  - make docs\n---\nUpdate the docs.\n",
        )

        fragment = Hooks(temp_project).resolve("chunk-complete")

        assert fragment is not None
        assert fragment.metadata == {"checks": ["make docs"]}
        assert fragment.body == "Update the docs.\n"
        assert "checks" not in fragment.body

    def test_unreadable_fragment_resolves_to_none(self, temp_project):
        """An unreadable file degrades to no hook rather than an exception."""
        path = write_hook(temp_project, "chunk-complete", "Secret.\n")
        path.chmod(0o000)
        try:
            if os.access(path, os.R_OK):
                pytest.skip("filesystem or privileges ignore chmod 000")

            assert Hooks(temp_project).resolve("chunk-complete") is None
        finally:
            path.chmod(0o644)

    def test_directory_where_a_fragment_belongs_resolves_to_none(self, temp_project):
        """docs/hooks/chunk-complete.md as a directory must not raise."""
        (temp_project / "docs" / "hooks" / "chunk-complete.md").mkdir(parents=True)

        assert Hooks(temp_project).resolve("chunk-complete") is None

    @pytest.mark.parametrize(
        "event",
        ["../../../etc/passwd", "a/b", "..", ".", "chunk/../../secret", ""],
    )
    def test_path_traversal_is_rejected(self, temp_project, event):
        """Event names are filenames, not paths; separators and dots are refused."""
        assert Hooks(temp_project).resolve(event) is None

    def test_traversal_rejection_does_not_read_outside_hooks_dir(self, temp_project):
        """A traversal attempt must not resolve even when the target exists."""
        (temp_project / "secret.md").write_text("do not read me\n")

        assert Hooks(temp_project).resolve("../secret") is None


class TestRender:
    """The injectable block handed to a command's context line."""

    def test_render_names_the_event_and_its_source_file(self, temp_project):
        """An agent must be able to cite what produced an instruction."""
        write_hook(temp_project, "chunk-complete", "Update the docs.\n")
        hooks = Hooks(temp_project)

        rendered = hooks.render(hooks.resolve("chunk-complete"))

        assert "chunk-complete" in rendered
        assert "docs/hooks/chunk-complete.md" in rendered
        assert "Update the docs." in rendered

    def test_render_uses_a_project_relative_source_path(self, temp_project):
        """Absolute tmpdir paths are noise in a prompt and leak the checkout
        location; the source is cited relative to the project root."""
        write_hook(temp_project, "chunk-complete", "Update the docs.\n")
        hooks = Hooks(temp_project)

        rendered = hooks.render(hooks.resolve("chunk-complete"))

        assert str(temp_project) not in rendered

    def test_render_omits_frontmatter(self, temp_project):
        """Metadata is machinery, not instruction."""
        write_hook(
            temp_project,
            "chunk-complete",
            "---\nchecks:\n  - make docs\n---\nUpdate the docs.\n",
        )
        hooks = Hooks(temp_project)

        rendered = hooks.render(hooks.resolve("chunk-complete"))

        assert "checks" not in rendered
        assert "Update the docs." in rendered


class TestListFragments:
    """Enumeration, and detection of hooks that will never fire."""

    def test_absent_directory_lists_nothing(self, temp_project):
        assert Hooks(temp_project).list_fragments() == []

    def test_known_event_is_flagged_known(self, temp_project):
        write_hook(temp_project, "chunk-complete", "Body.\n")

        fragments = Hooks(temp_project).list_fragments()

        assert [(f.event, known) for f, known in fragments] == [
            ("chunk-complete", True)
        ]

    def test_misspelled_event_is_flagged_unknown(self, temp_project):
        """The primary failure mode of the design: a hook that silently never
        fires because its filename matches no command."""
        write_hook(temp_project, "chunk-completed", "Body.\n")

        fragments = Hooks(temp_project).list_fragments()

        assert [(f.event, known) for f, known in fragments] == [
            ("chunk-completed", False)
        ]

    def test_listing_is_sorted_and_covers_both_kinds(self, temp_project):
        write_hook(temp_project, "chunk-complete", "a\n")
        write_hook(temp_project, "chunk-completed", "b\n")
        write_hook(temp_project, "narrative-create", "c\n")

        fragments = Hooks(temp_project).list_fragments()

        assert [(f.event, known) for f, known in fragments] == [
            ("chunk-complete", True),
            ("chunk-completed", False),
            ("narrative-create", True),
        ]

    def test_non_markdown_files_are_ignored(self, temp_project):
        """A README or a stray .txt in docs/hooks/ is not a hook."""
        hooks_dir = temp_project / "docs" / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "notes.txt").write_text("scratch\n")

        assert Hooks(temp_project).list_fragments() == []


class TestKnownEvents:
    """KNOWN_EVENTS is the vocabulary that makes unknown-hook detection possible."""

    def test_known_events_is_non_empty(self):
        assert KNOWN_EVENTS

    def test_chunk_lifecycle_commands_are_known(self):
        """Regression guard for the events most likely to carry a hook."""
        assert {"chunk-create", "chunk-plan", "chunk-implement", "chunk-complete"} <= (
            KNOWN_EVENTS
        )
