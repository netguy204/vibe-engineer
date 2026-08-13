"""Backreference scanning and management for VE artifacts.

# Chunk: docs/chunks/chunks_decompose - Extracted from chunks.py for module decomposition
# Chunk: docs/chunks/backref_language_agnostic - Language-agnostic source file enumeration
# Chunk: docs/chunks/federation_qualified_refs - Qualified backreference grammar and parser

This module provides utilities for scanning source files for backreference
comments (# Chunk:, # Narrative:, # Subsystem:) and updating them during
consolidation operations.

A backreference's target may be bare or qualified. The examples below use
`<id>` rather than a chunk name on purpose: since this module's grammar reads a
comment at any indentation, an illustrative reference written out in full would
be scanned as a real one and reported as dangling.

    # Chunk: docs/chunks/<id>                  bare - the nearest enclosing tree
    # Chunk: pybusiness::docs/chunks/<id>      another tree in the same workspace
    # Chunk: acme/platform::docs/chunks/<id>   another repository

The `::` qualifier is the same convention `models.references.SymbolicReference`
already accepts in frontmatter. This module owns the grammar: it parses,
classifies, and preserves qualifiers. It never *resolves* them - deciding
whether a member name or repository exists is the workspace validator's job, and
that separation is why classification needs no manifest lookup: a member
qualifier contains no `/` and an org/repo qualifier contains exactly one, so the
two forms are syntactically disjoint.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field
from enum import StrEnum

from external_refs import ARTIFACT_DIR_NAME
from models import ArtifactType
# Qualifier shape is classified by the same rule frontmatter validation uses,
# so comment refs and `SymbolicReference` refs cannot drift apart.
# Chunk: docs/chunks/federation_member_refs - Shared qualifier shape rule
from models.shared import classify_qualifier_shape
from source_files import enumerate_source_files


# Chunk: docs/chunks/federation_qualified_refs - Qualifier classification
class QualifierKind(StrEnum):
    """How a backreference's target is addressed.

    BARE:      no qualifier; resolves in the nearest enclosing tree.
    MEMBER:    `<member>::` - another VE tree in the same workspace.
    REPO:      `<org>/<repo>::` - a tree in another repository.
    MALFORMED: a qualifier was written but is not usable - most commonly the
               legacy prefix style `<something>/docs/chunks/<id>`, which is
               ambiguous by construction. Recognized so it can be reported and
               normalized, never resolved.
    """

    BARE = "bare"
    MEMBER = "member"
    REPO = "repo"
    MALFORMED = "malformed"


# Chunk: docs/chunks/federation_qualified_refs - Parsed reference carrying its qualifier
@dataclass(frozen=True)
class ParsedBackreference:
    """A single backreference comment, parsed and classified.

    Carries the qualifier alongside the artifact id so callers can tell a
    cross-tree reference from a local one without re-parsing the comment.

    # Chunk: docs/chunks/backref_indented_comments - Indentation travels with the reference
    """

    artifact_type: ArtifactType
    artifact_id: str
    qualifier: str | None = None
    qualifier_kind: QualifierKind = QualifierKind.BARE
    separator: str | None = None  # "::" as written, or "/" for legacy prefixes
    line_number: int | None = None  # 1-indexed, when parsed from file content
    malformed_reason: str | None = None
    # Leading whitespace as written, so a rewrite can put the reference back
    # at the column it came from instead of flattening it to the margin.
    indent: str = ""

    @property
    def is_bare(self) -> bool:
        """True when the reference resolves in its nearest enclosing tree."""
        return self.qualifier_kind == QualifierKind.BARE

    @property
    def is_qualified(self) -> bool:
        """True when the reference carries a usable cross-tree qualifier."""
        return self.qualifier_kind in (QualifierKind.MEMBER, QualifierKind.REPO)

    @property
    def is_malformed(self) -> bool:
        """True when a qualifier was written but cannot be used as one."""
        return self.qualifier_kind == QualifierKind.MALFORMED

    @property
    def artifact_dir(self) -> str:
        """The docs subdirectory for this artifact type (e.g. "chunks")."""
        return ARTIFACT_DIR_NAME[self.artifact_type]

    @property
    def artifact_path(self) -> str:
        """The unqualified path to the artifact (e.g. "docs/chunks/x")."""
        return f"docs/{self.artifact_dir}/{self.artifact_id}"

    @property
    def qualifier_prefix(self) -> str:
        """The qualifier as written, including its separator ("" when bare)."""
        if self.qualifier is None or self.separator is None:
            return ""
        return f"{self.qualifier}{self.separator}"

    @property
    def reference(self) -> str:
        """The full reference text as written (round-trips the source)."""
        return f"{self.qualifier_prefix}{self.artifact_path}"


@dataclass
class BackreferenceInfo:
    """Information about backreferences in a source file.

    The `*_refs` lists hold artifact ids for references that name an artifact
    unambiguously (bare or validly qualified). Malformed-qualifier references
    are deliberately excluded from them - a caller reading an id out of those
    lists treats it as an artifact of the local tree, which is exactly the
    silent misresolution the qualifier grammar exists to prevent. They remain
    visible, with their reason, in the `*_references` lists.
    """

    file_path: pathlib.Path
    chunk_refs: list[str]  # List of chunk IDs referenced
    narrative_refs: list[str]  # List of narrative IDs referenced
    subsystem_refs: list[str]  # List of subsystem IDs referenced
    # Chunk: docs/chunks/federation_qualified_refs - Qualifier-carrying references per type
    chunk_references: list[ParsedBackreference] = field(default_factory=list)
    narrative_references: list[ParsedBackreference] = field(default_factory=list)
    subsystem_references: list[ParsedBackreference] = field(default_factory=list)

    @property
    def unique_chunk_count(self) -> int:
        """Count of unique chunk references."""
        return len(set(self.chunk_refs))

    @property
    def total_chunk_count(self) -> int:
        """Total count of chunk references (including duplicates)."""
        return len(self.chunk_refs)


# The comment keyword for each artifact type that may be backreferenced from
# source. Investigations are deliberately absent: they are not a valid
# backreference type. Directory names come from ARTIFACT_DIR_NAME rather than
# being restated here.
_ARTIFACT_KEYWORDS: dict[ArtifactType, str] = {
    ArtifactType.CHUNK: "Chunk",
    ArtifactType.NARRATIVE: "Narrative",
    ArtifactType.SUBSYSTEM: "Subsystem",
}

# An optional qualifier ahead of the docs path. The separator is captured so a
# legacy prefix (`architecture/docs/...`) can be distinguished from an intended
# qualifier (`architecture::docs/...`) rather than silently conflated with it.
# The group is optional, so a bare path matches with both groups unset.
_QUALIFIER_PREFIX = r"(?:(?P<qualifier>\S*?)(?P<separator>::|/))?"


# Chunk: docs/chunks/federation_qualified_refs - One grammar generator for all artifact types
# Chunk: docs/chunks/backref_indented_comments - Indentation is captured, not rejected
def _build_backref_pattern(keyword: str, artifact_dir: str) -> re.Pattern[str]:
    """Compile the backreference pattern for one artifact type.

    Named groups (`qualifier`, `separator`, `artifact_id`) rather than
    positional ones: the artifact id is no longer the first group, and named
    access keeps that change loud instead of silently returning a qualifier.

    Leading indentation is unbounded and captured as `indent`; a reference is
    as valid inside a class or function as at column 0, and that is where most
    of them live. Everything after the marker is deliberately strict: the gaps
    are `[ \\t]` rather than `\\s`, so a reference occupies exactly one line and
    the parser cannot run past the end of it onto the next.

    `indent` is captured rather than discarded because rewrites re-emit it —
    making interior references visible must not reformat the code holding them.
    """
    return re.compile(
        rf"^(?P<indent>[ \t]*)#[ \t]+{keyword}:[ \t]+{_QUALIFIER_PREFIX}"
        rf"docs/{artifact_dir}/(?P<artifact_id>[a-z0-9_-]+)",
        re.MULTILINE,
    )


BACKREF_PATTERNS: dict[ArtifactType, re.Pattern[str]] = {
    artifact_type: _build_backref_pattern(keyword, ARTIFACT_DIR_NAME[artifact_type])
    for artifact_type, keyword in _ARTIFACT_KEYWORDS.items()
}

CHUNK_BACKREF_PATTERN = BACKREF_PATTERNS[ArtifactType.CHUNK]
NARRATIVE_BACKREF_PATTERN = BACKREF_PATTERNS[ArtifactType.NARRATIVE]
SUBSYSTEM_BACKREF_PATTERN = BACKREF_PATTERNS[ArtifactType.SUBSYSTEM]


# Chunk: docs/chunks/federation_qualified_refs - Qualifier syntax rules
def _classify_qualifier(
    qualifier: str | None, separator: str | None
) -> tuple[QualifierKind, str | None]:
    """Classify a qualifier by shape alone, returning (kind, malformed_reason).

    Shares `models.shared.classify_qualifier_shape` with the frontmatter model
    (`models.references.SymbolicReference`), so the two grammars cannot drift.
    Existence is not checked here: a well-formed qualifier naming a tree that
    does not exist is MEMBER, and reporting that is the workspace validator's
    job.
    """
    if separator is None:
        return QualifierKind.BARE, None

    if separator == "/":
        return QualifierKind.MALFORMED, (
            f"legacy prefix-style reference: '{qualifier}/' is a path prefix, not a "
            "qualifier; qualified references separate the qualifier with '::' "
            "(a workspace member name, or 'org/repo')"
        )

    if not qualifier:
        return QualifierKind.MALFORMED, "qualifier cannot be empty before '::'"

    if "::" in qualifier:
        return QualifierKind.MALFORMED, (
            f"qualifier '{qualifier}' cannot contain multiple '::' delimiters"
        )

    # Chunk: docs/chunks/federation_member_refs - Shape rule shared with frontmatter
    kind, reason = classify_qualifier_shape(qualifier)
    if kind == "member":
        return QualifierKind.MEMBER, None
    if kind == "repo":
        return QualifierKind.REPO, None
    return QualifierKind.MALFORMED, reason


# Chunk: docs/chunks/federation_qualified_refs - Shared single-line parser
def parse_backreference(line: str, line_number: int | None = None) -> ParsedBackreference | None:
    """Parse one line as a backreference comment.

    This is the single entry point for reading backreference syntax; callers
    (the scanner, consolidation rewrites, integrity checks, workspace
    validation) use it instead of matching the patterns themselves.

    Args:
        line: The line to parse.
        line_number: Optional 1-indexed line number to record on the result.

    Returns:
        The parsed reference, or None if the line is not a backreference.
    """
    # Every pattern anchors on "#" after optional indentation, so this skips
    # three regex attempts on the overwhelming majority of lines in every
    # scanned file. It strips first: an indented comment is a real reference.
    if not line.lstrip(" \t").startswith("#"):
        return None

    for artifact_type, pattern in BACKREF_PATTERNS.items():
        match = pattern.match(line)
        if match is None:
            continue
        qualifier = match.group("qualifier")
        separator = match.group("separator")
        kind, reason = _classify_qualifier(qualifier, separator)
        return ParsedBackreference(
            artifact_type=artifact_type,
            artifact_id=match.group("artifact_id"),
            qualifier=qualifier if separator is not None else None,
            qualifier_kind=kind,
            separator=separator,
            line_number=line_number,
            malformed_reason=reason,
            indent=match.group("indent"),
        )
    return None


# Chunk: docs/chunks/federation_qualified_refs - Line-numbered content scan
def scan_backreferences(content: str) -> list[ParsedBackreference]:
    """Parse every backreference in a blob of file content, in order.

    Each result carries its 1-indexed line number so callers can report
    `file:line` for a defective reference.
    """
    references: list[ParsedBackreference] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        parsed = parse_backreference(line, line_number=line_number)
        if parsed is not None:
            references.append(parsed)
    return references


def _artifact_ids(references: list[ParsedBackreference]) -> list[str]:
    """Artifact ids for references that name an artifact unambiguously.

    Malformed-qualifier references are omitted: their id alone would read as a
    local artifact id, and treating them as local is the misresolution the
    grammar exists to surface rather than reproduce.
    """
    return [reference.artifact_id for reference in references if not reference.is_malformed]


def count_backreferences(
    project_dir: pathlib.Path,
    source_patterns: list[str] | None = None,
) -> list[BackreferenceInfo]:
    """Scan source files for backreference comments.

    Finds all `# Chunk:`, `# Narrative:`, and `# Subsystem:` comments
    in source files and returns counts per file.

    Args:
        project_dir: Path to the project directory.
        source_patterns: List of glob patterns to search. If None, uses
            language-agnostic enumeration to find all source files.
            Providing explicit patterns is for backward compatibility.

    Returns:
        List of BackreferenceInfo for files containing backreferences.
    """
    results: list[BackreferenceInfo] = []

    # Determine file list based on source_patterns
    if source_patterns is None:
        # Use language-agnostic enumeration
        file_paths = enumerate_source_files(project_dir)
    else:
        # Use explicit glob patterns (backward compatibility)
        file_paths = []
        for pattern in source_patterns:
            for file_path in project_dir.glob(pattern):
                if file_path.is_file():
                    file_paths.append(file_path)

    for file_path in file_paths:
        try:
            content = file_path.read_text()
        except Exception:
            continue

        # Parse every backreference, qualified or not, keeping the qualifier
        references = scan_backreferences(content)
        if not references:
            continue

        by_type: dict[ArtifactType, list[ParsedBackreference]] = {
            artifact_type: [] for artifact_type in _ARTIFACT_KEYWORDS
        }
        for reference in references:
            by_type[reference.artifact_type].append(reference)

        results.append(BackreferenceInfo(
            file_path=file_path,
            chunk_refs=_artifact_ids(by_type[ArtifactType.CHUNK]),
            narrative_refs=_artifact_ids(by_type[ArtifactType.NARRATIVE]),
            subsystem_refs=_artifact_ids(by_type[ArtifactType.SUBSYSTEM]),
            chunk_references=by_type[ArtifactType.CHUNK],
            narrative_references=by_type[ArtifactType.NARRATIVE],
            subsystem_references=by_type[ArtifactType.SUBSYSTEM],
        ))

    # Sort by unique chunk count descending
    results.sort(key=lambda r: r.unique_chunk_count, reverse=True)

    return results


def update_backreferences(
    project_dir: pathlib.Path,
    file_path: pathlib.Path,
    chunk_ids_to_replace: list[str],
    narrative_id: str,
    narrative_description: str,
    dry_run: bool = False,
) -> int:
    """Replace chunk backreferences with narrative backreference.

    Finds all `# Chunk: docs/chunks/{id}` comments where id is in
    chunk_ids_to_replace and replaces them with a single
    `# Narrative: docs/narratives/{narrative_id} - {description}` comment.

    # Chunk: docs/chunks/federation_qualified_refs - Qualifier-preserving rewrite

    Qualifiers survive the rewrite: `pybusiness::docs/chunks/x` becomes
    `pybusiness::docs/narratives/{narrative_id}`, so consolidation neither skips
    qualified references (which would leave them pointing at chunks that no
    longer own the intent) nor silently relocates them into the local tree. One
    narrative comment is emitted per distinct qualifier, since references under
    different qualifiers name artifacts in different trees and cannot collapse
    into a single line.

    Whether a qualified reference denotes the same chunk the caller
    consolidated requires resolving the qualifier against a workspace manifest,
    which this layer deliberately does not do; the qualifier is carried through
    so `ve workspace validate` (federation_global_validator) can check it.

    Malformed-qualifier references (legacy `<prefix>/docs/chunks/{id}`) are left
    byte-identical and not counted: they must be normalized into a real
    qualifier before anyone can say which tree they meant.

    Args:
        project_dir: Path to the project directory.
        file_path: Path to the source file to update.
        chunk_ids_to_replace: Chunk IDs whose references should be replaced.
        narrative_id: Narrative directory to reference.
        narrative_description: Description for the narrative backreference.
        dry_run: If True, don't modify the file, just return count.

    Returns:
        Number of backreferences replaced.
    """
    if not file_path.exists():
        return 0

    content = file_path.read_text()
    lines = content.split("\n")
    new_lines: list[str] = []
    replaced_count = 0
    qualifiers_emitted: set[tuple[str, str]] = set()

    # Build pattern to match chunk refs we want to replace
    chunk_ids_set = set(chunk_ids_to_replace)

    for line in lines:
        parsed = parse_backreference(line)
        if (
            parsed is not None
            and parsed.artifact_type == ArtifactType.CHUNK
            and not parsed.is_malformed
            and parsed.artifact_id in chunk_ids_set
        ):
            replaced_count += 1
            # One narrative reference per (qualifier, column), emitted at the
            # column the chunk reference occupied.
            #
            # Chunk: docs/chunks/backref_indented_comments - Rewrites preserve indentation
            #
            # Indentation is part of the dedup key, not just the output: a
            # reference inside a function documents that function, so collapsing
            # it into a top-level comment would move the annotation away from
            # the code it describes and reindent the file. Two references at the
            # same column under the same qualifier still collapse — that is the
            # clutter reduction consolidation exists for.
            key = (parsed.qualifier_prefix, parsed.indent)
            if key not in qualifiers_emitted:
                new_lines.append(
                    f"{parsed.indent}# Narrative: {parsed.qualifier_prefix}"
                    f"docs/narratives/{narrative_id} - {narrative_description}"
                )
                qualifiers_emitted.add(key)
            # Skip this chunk line (don't add to new_lines)
            continue

        new_lines.append(line)

    if not dry_run and replaced_count > 0:
        file_path.write_text("\n".join(new_lines))

    return replaced_count
