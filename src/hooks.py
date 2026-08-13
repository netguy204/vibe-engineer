"""VE hooks - operator-authored instruction fragments for lifecycle commands.

# Chunk: docs/chunks/hooks_lifecycle_fragments - VE hook resolution and rendering

A project declares repository-specific requirements for a lifecycle phase by
writing `docs/hooks/<command-name>.md`. Every plugin command carries a
`!`ve hooks show <command-name>`` line in its context block, so the fragment is
loaded precisely when the phase it governs is running, rather than always-on the
way CLAUDE.md content is.

These are NOT Claude Code plugin hooks (`hooks/hooks.json`, `SessionStart`),
which are a harness-level mechanism firing on session events. VE hooks are
prompt content, not executable callbacks.

VE hooks are also not workflow artifacts in the docs/subsystems/workflow_artifacts
sense: they have no status, no state machine, no ordering, and deliberately do
not go through ArtifactManager (DEC-009). They are inert content keyed by
filename.

Everything here is total. Resolution runs inside the context block of every
command invocation, so an exception raised here would corrupt the prompt of a
command that has nothing to do with hooks.
"""

import pathlib
from dataclasses import dataclass, field
from typing import Any

from frontmatter import split_frontmatter_and_body
from validation import validate_identifier


# The set of valid event names: exactly the plugin's skill (command) names.
#
# A literal rather than a directory scan because no single path holds the
# skill files across all install layouts: a built wheel force-includes
# skills/ as orchestrator/skills (see pyproject.toml), that directory does
# not exist in a source checkout, and the separately-installed CLI (DEC-010)
# cannot count on CLAUDE_PLUGIN_ROOT, which is only set inside hook execution.
# A three-way fallback would be more machinery than a literal plus one test:
# tests/test_plugin_skills.py pins this to skills/*/SKILL.md by exact equality
# in both directions, so a skill added or removed without updating it fails.
KNOWN_EVENTS: frozenset[str] = frozenset(
    {
        "audit-corpus",
        "audit-intent",
        "chunk-commit",
        "chunk-complete",
        "chunk-create",
        "chunk-demote",
        "chunk-execute",
        "chunk-execute-all",
        "chunk-implement",
        "chunk-plan",
        "chunk-rebase",
        "chunk-review",
        "chunk-update-references",
        "chunks-resolve-references",
        "cluster-rename",
        "decision-create",
        "discover-subsystems",
        "entity-episodic",
        "entity-shutdown",
        "entity-startup",
        "friction-log",
        "investigation-create",
        "migrate-managed-claude-md",
        "narrative-compact",
        "narrative-create",
        "narrative-execute",
        "orchestrator-inject",
        "orchestrator-investigate",
        "orchestrator-monitor",
        "orchestrator-submit-future",
        "steward-changelog",
        "steward-send",
        "steward-setup",
        "steward-watch",
        "subsystem-discover",
        "swarm-monitor",
        "swarm-request-response",
        "validate-fix",
        "ve-status",
        "workspace-validate-fix",
    }
)

# Directory holding hook fragments, relative to the project root.
HOOKS_DIR = pathlib.Path("docs") / "hooks"

# Printed when no fragment exists. Every line of the canonical command preamble
# prints an explicit negative; a blank value in a context bullet reads to an
# agent as a broken command rather than an absent file.
NO_HOOK_MESSAGE = "(no project hook)"


@dataclass
class HookFragment:
    """A resolved hook fragment.

    Attributes:
        event: The command name this fragment governs.
        path: Absolute path to the fragment on disk.
        relative_path: Path relative to the project root, for citation.
        metadata: Parsed frontmatter. Carries no required keys today; it exists
            so a later enforced-check key (`checks:`) is an additive change to
            the format rather than a migration of every operator's hook files.
        body: The instruction prose, verbatim and frontmatter-free.
    """

    event: str
    path: pathlib.Path
    relative_path: str
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)


class Hooks:
    """Resolves and renders VE hook fragments for a project."""

    def __init__(self, project_dir: pathlib.Path):
        self.project_dir = pathlib.Path(project_dir)
        self.hooks_dir = self.project_dir / HOOKS_DIR

    def resolve(self, event: str) -> HookFragment | None:
        """Resolve docs/hooks/<event>.md into a fragment.

        Returns None - never raises - when the event name is not a bare
        filename, the directory or file is absent, the path is not a regular
        file, or the file cannot be read.
        """
        if not self._is_safe_event_name(event):
            return None

        path = self.hooks_dir / f"{event}.md"
        return self._read_fragment(event, path)

    def render(self, fragment: HookFragment | None) -> str:
        """Render a fragment as the block injected into a command's context."""
        if fragment is None:
            return NO_HOOK_MESSAGE

        return (
            f"## Project hook: {fragment.event}\n"
            f"Source: {fragment.relative_path}\n\n"
            f"{fragment.body}"
        )

    def list_fragments(self) -> list[tuple[HookFragment, bool]]:
        """List every fragment in docs/hooks/, sorted by event name.

        Each entry is paired with whether its filename names a known command.
        An unknown name is the design's primary failure mode: the hook is
        well-formed and will simply never fire.
        """
        try:
            paths = sorted(self.hooks_dir.glob("*.md"))
        except OSError:
            return []

        results = []
        for path in paths:
            fragment = self._read_fragment(path.stem, path)
            if fragment is not None:
                results.append((fragment, fragment.event in KNOWN_EVENTS))
        return results

    @staticmethod
    def _is_safe_event_name(event: str) -> bool:
        """An event name is a bare filename: no separators, no dots.

        Guards against `resolve("../../../etc/passwd")` reading outside the
        hooks directory. validate_identifier permits [a-zA-Z0-9_-], which
        covers every hyphenated command name and rejects paths and dots.
        """
        if not event:
            return False
        return not validate_identifier(event, "event", max_length=None)

    def _read_fragment(
        self, event: str, path: pathlib.Path
    ) -> HookFragment | None:
        """Read and split a fragment, degrading to None on any I/O problem."""
        try:
            if not path.is_file():
                return None
            content = path.read_text()
        except OSError:
            return None

        metadata, body = split_frontmatter_and_body(content)
        return HookFragment(
            event=event,
            path=path,
            relative_path=(HOOKS_DIR / path.name).as_posix(),
            body=body,
            metadata=metadata,
        )
