"""
Prototype: File-based referential integrity validator

This validator traverses the file system to check all link types without
maintaining a separate database. It builds an in-memory graph on each run.

Key insight: VE already has validation for chunk outbound links. The gaps are:
1. Code backreferences (# Chunk:, # Subsystem: comments)
2. proposed_chunks[].chunk_directory in narratives/investigations/friction
3. Bidirectional consistency (A→B implies B→A where applicable)
4. created_after references
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

# Patterns from chunks.py
CHUNK_BACKREF_PATTERN = re.compile(
    r"^#\s+Chunk:\s+docs/chunks/([a-z0-9_-]+)", re.MULTILINE
)
SUBSYSTEM_BACKREF_PATTERN = re.compile(
    r"^#\s+Subsystem:\s+docs/subsystems/([a-z0-9_-]+)", re.MULTILINE
)


@dataclass
class ValidationError:
    """A referential integrity violation."""

    source: str  # Where the broken link originates
    target: str  # What it points to
    link_type: str  # Type of link
    issue: str  # Description of the problem


@dataclass
class ReferenceGraph:
    """In-memory representation of all artifact links."""

    # Known artifacts (path relative to docs/)
    chunks: set[str] = field(default_factory=set)
    narratives: set[str] = field(default_factory=set)
    investigations: set[str] = field(default_factory=set)
    subsystems: set[str] = field(default_factory=set)
    friction_entries: set[str] = field(default_factory=set)

    # Edges: source → {targets}
    chunk_to_narrative: dict[str, str] = field(default_factory=dict)
    chunk_to_investigation: dict[str, str] = field(default_factory=dict)
    chunk_to_subsystems: dict[str, set[str]] = field(default_factory=dict)
    chunk_to_friction: dict[str, set[str]] = field(default_factory=dict)
    chunk_to_code: dict[str, set[str]] = field(default_factory=dict)

    code_to_chunks: dict[str, set[str]] = field(default_factory=dict)
    code_to_subsystems: dict[str, set[str]] = field(default_factory=dict)

    narrative_to_chunks: dict[str, set[str]] = field(default_factory=dict)
    investigation_to_chunks: dict[str, set[str]] = field(default_factory=dict)
    friction_to_chunks: dict[str, set[str]] = field(default_factory=dict)

    subsystem_to_chunks: dict[str, set[str]] = field(default_factory=dict)

    created_after: dict[str, set[str]] = field(default_factory=dict)


def scan_artifacts(docs_path: Path) -> ReferenceGraph:
    """Scan docs/ to discover all artifacts and their links."""
    graph = ReferenceGraph()

    # Scan chunks
    chunks_dir = docs_path / "chunks"
    if chunks_dir.exists():
        for chunk_dir in chunks_dir.iterdir():
            if chunk_dir.is_dir() and (chunk_dir / "GOAL.md").exists():
                chunk_id = chunk_dir.name
                graph.chunks.add(chunk_id)
                _parse_chunk_links(chunk_dir / "GOAL.md", chunk_id, graph)

    # Scan narratives
    narratives_dir = docs_path / "narratives"
    if narratives_dir.exists():
        for narr_dir in narratives_dir.iterdir():
            if narr_dir.is_dir() and (narr_dir / "OVERVIEW.md").exists():
                narr_id = narr_dir.name
                graph.narratives.add(narr_id)
                _parse_parent_artifact_links(
                    narr_dir / "OVERVIEW.md", narr_id, graph, "narrative"
                )

    # Scan investigations
    inv_dir = docs_path / "investigations"
    if inv_dir.exists():
        for investigation in inv_dir.iterdir():
            if investigation.is_dir() and (investigation / "OVERVIEW.md").exists():
                inv_id = investigation.name
                graph.investigations.add(inv_id)
                _parse_parent_artifact_links(
                    investigation / "OVERVIEW.md", inv_id, graph, "investigation"
                )

    # Scan subsystems
    subsys_dir = docs_path / "subsystems"
    if subsys_dir.exists():
        for subsystem in subsys_dir.iterdir():
            if subsystem.is_dir() and (subsystem / "OVERVIEW.md").exists():
                subsys_id = subsystem.name
                graph.subsystems.add(subsys_id)
                _parse_subsystem_links(subsystem / "OVERVIEW.md", subsys_id, graph)

    # Scan friction entries
    friction_file = docs_path / "trunk" / "FRICTION.md"
    if friction_file.exists():
        _parse_friction_file(friction_file, graph)

    return graph


def scan_code_backrefs(src_path: Path, graph: ReferenceGraph) -> None:
    """Scan source files for backreference comments."""
    for py_file in src_path.rglob("*.py"):
        try:
            content = py_file.read_text()
        except Exception:
            continue

        file_key = str(py_file)

        # Find chunk backrefs
        for match in CHUNK_BACKREF_PATTERN.finditer(content):
            chunk_id = match.group(1)
            if file_key not in graph.code_to_chunks:
                graph.code_to_chunks[file_key] = set()
            graph.code_to_chunks[file_key].add(chunk_id)

        # Find subsystem backrefs
        for match in SUBSYSTEM_BACKREF_PATTERN.finditer(content):
            subsys_id = match.group(1)
            if file_key not in graph.code_to_subsystems:
                graph.code_to_subsystems[file_key] = set()
            graph.code_to_subsystems[file_key].add(subsys_id)


def validate_graph(graph: ReferenceGraph) -> list[ValidationError]:
    """Check all referential integrity constraints."""
    errors: list[ValidationError] = []

    # 1. Code→Chunk backrefs must point to existing chunks
    for file_path, chunk_ids in graph.code_to_chunks.items():
        for chunk_id in chunk_ids:
            if chunk_id not in graph.chunks:
                errors.append(
                    ValidationError(
                        source=file_path,
                        target=f"chunks/{chunk_id}",
                        link_type="code_backref",
                        issue=f"Code references non-existent chunk '{chunk_id}'",
                    )
                )

    # 2. Code→Subsystem backrefs must point to existing subsystems
    for file_path, subsys_ids in graph.code_to_subsystems.items():
        for subsys_id in subsys_ids:
            if subsys_id not in graph.subsystems:
                errors.append(
                    ValidationError(
                        source=file_path,
                        target=f"subsystems/{subsys_id}",
                        link_type="code_backref",
                        issue=f"Code references non-existent subsystem '{subsys_id}'",
                    )
                )

    # 3. Narrative proposed_chunks must point to existing chunks (if set)
    for narr_id, chunk_ids in graph.narrative_to_chunks.items():
        for chunk_id in chunk_ids:
            if chunk_id and chunk_id not in graph.chunks:
                errors.append(
                    ValidationError(
                        source=f"narratives/{narr_id}",
                        target=f"chunks/{chunk_id}",
                        link_type="proposed_chunk",
                        issue=f"Narrative references non-existent chunk '{chunk_id}'",
                    )
                )

    # 4. Investigation proposed_chunks must point to existing chunks (if set)
    for inv_id, chunk_ids in graph.investigation_to_chunks.items():
        for chunk_id in chunk_ids:
            if chunk_id and chunk_id not in graph.chunks:
                errors.append(
                    ValidationError(
                        source=f"investigations/{inv_id}",
                        target=f"chunks/{chunk_id}",
                        link_type="proposed_chunk",
                        issue=f"Investigation references non-existent chunk '{chunk_id}'",
                    )
                )

    # 5. Chunk→Narrative must point to existing narrative
    for chunk_id, narr_id in graph.chunk_to_narrative.items():
        if narr_id not in graph.narratives:
            errors.append(
                ValidationError(
                    source=f"chunks/{chunk_id}",
                    target=f"narratives/{narr_id}",
                    link_type="chunk_narrative",
                    issue=f"Chunk references non-existent narrative '{narr_id}'",
                )
            )

    # 6. Chunk→Investigation must point to existing investigation
    for chunk_id, inv_id in graph.chunk_to_investigation.items():
        if inv_id not in graph.investigations:
            errors.append(
                ValidationError(
                    source=f"chunks/{chunk_id}",
                    target=f"investigations/{inv_id}",
                    link_type="chunk_investigation",
                    issue=f"Chunk references non-existent investigation '{inv_id}'",
                )
            )

    # 7. Chunk→Subsystem must point to existing subsystem
    for chunk_id, subsys_ids in graph.chunk_to_subsystems.items():
        for subsys_id in subsys_ids:
            if subsys_id not in graph.subsystems:
                errors.append(
                    ValidationError(
                        source=f"chunks/{chunk_id}",
                        target=f"subsystems/{subsys_id}",
                        link_type="chunk_subsystem",
                        issue=f"Chunk references non-existent subsystem '{subsys_id}'",
                    )
                )

    # 8. Bidirectional: If chunk→narrative, narrative should list chunk in proposed_chunks
    for chunk_id, narr_id in graph.chunk_to_narrative.items():
        narr_chunks = graph.narrative_to_chunks.get(narr_id, set())
        if chunk_id not in narr_chunks:
            errors.append(
                ValidationError(
                    source=f"chunks/{chunk_id}",
                    target=f"narratives/{narr_id}",
                    link_type="bidirectional",
                    issue=f"Chunk claims narrative '{narr_id}' but narrative doesn't list chunk",
                )
            )

    # 9. Bidirectional: If chunk→investigation, investigation should list chunk
    for chunk_id, inv_id in graph.chunk_to_investigation.items():
        inv_chunks = graph.investigation_to_chunks.get(inv_id, set())
        if chunk_id not in inv_chunks:
            errors.append(
                ValidationError(
                    source=f"chunks/{chunk_id}",
                    target=f"investigations/{inv_id}",
                    link_type="bidirectional",
                    issue=f"Chunk claims investigation '{inv_id}' but investigation doesn't list chunk",
                )
            )

    # 10. Bidirectional: Code→Chunk should have Chunk→Code (warning, not error)
    # This is tricky because chunk→code uses file+symbol, code→chunk is just chunk id
    # For now, check that if code references chunk, chunk references that file
    for file_path, chunk_ids in graph.code_to_chunks.items():
        for chunk_id in chunk_ids:
            chunk_files = graph.chunk_to_code.get(chunk_id, set())
            # Normalize paths for comparison
            if not any(file_path.endswith(f) for f in chunk_files):
                errors.append(
                    ValidationError(
                        source=file_path,
                        target=f"chunks/{chunk_id}",
                        link_type="bidirectional",
                        issue=f"Code has backref to chunk but chunk doesn't reference this file",
                    )
                )

    return errors


def _parse_chunk_links(goal_file: Path, chunk_id: str, graph: ReferenceGraph) -> None:
    """Extract links from chunk GOAL.md frontmatter."""
    try:
        content = goal_file.read_text()
        fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not fm_match:
            return
        fm = yaml.safe_load(fm_match.group(1)) or {}
    except Exception:
        return

    if fm.get("narrative"):
        graph.chunk_to_narrative[chunk_id] = fm["narrative"]

    if fm.get("investigation"):
        graph.chunk_to_investigation[chunk_id] = fm["investigation"]

    if fm.get("subsystems"):
        graph.chunk_to_subsystems[chunk_id] = {
            s["subsystem_id"] if isinstance(s, dict) else s for s in fm["subsystems"]
        }

    if fm.get("friction_entries"):
        graph.chunk_to_friction[chunk_id] = {
            e["entry_id"] if isinstance(e, dict) else e for e in fm["friction_entries"]
        }

    if fm.get("code_references"):
        graph.chunk_to_code[chunk_id] = set()
        for ref in fm["code_references"]:
            if isinstance(ref, dict) and ref.get("ref"):
                # Extract file path from symbolic reference
                ref_str = ref["ref"]
                file_part = ref_str.split("#")[0]
                if "::" in file_part:
                    file_part = file_part.split("::")[-1]
                graph.chunk_to_code[chunk_id].add(file_part)


def _parse_parent_artifact_links(
    overview_file: Path,
    artifact_id: str,
    graph: ReferenceGraph,
    artifact_type: Literal["narrative", "investigation"],
) -> None:
    """Extract proposed_chunks links from narrative/investigation."""
    try:
        content = overview_file.read_text()
        fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not fm_match:
            return
        fm = yaml.safe_load(fm_match.group(1)) or {}
    except Exception:
        return

    proposed = fm.get("proposed_chunks", [])
    chunk_ids = set()
    for p in proposed:
        if isinstance(p, dict) and p.get("chunk_directory"):
            # Extract chunk name from path like "docs/chunks/foo"
            chunk_dir = p["chunk_directory"]
            chunk_name = chunk_dir.split("/")[-1] if "/" in chunk_dir else chunk_dir
            chunk_ids.add(chunk_name)

    if artifact_type == "narrative":
        graph.narrative_to_chunks[artifact_id] = chunk_ids
    else:
        graph.investigation_to_chunks[artifact_id] = chunk_ids


def _parse_subsystem_links(
    overview_file: Path, subsys_id: str, graph: ReferenceGraph
) -> None:
    """Extract chunk refs from subsystem OVERVIEW.md."""
    try:
        content = overview_file.read_text()
        fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not fm_match:
            return
        fm = yaml.safe_load(fm_match.group(1)) or {}
    except Exception:
        return

    chunks = fm.get("chunks", [])
    graph.subsystem_to_chunks[subsys_id] = set(chunks)


def _parse_friction_file(friction_file: Path, graph: ReferenceGraph) -> None:
    """Extract friction entries and proposed_chunks from FRICTION.md."""
    try:
        content = friction_file.read_text()
    except Exception:
        return

    # Parse entry IDs from body
    entry_pattern = re.compile(r"###\s+(F\d+):")
    for match in entry_pattern.finditer(content):
        graph.friction_entries.add(match.group(1))

    # Parse proposed_chunks from frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        try:
            fm = yaml.safe_load(fm_match.group(1)) or {}
            proposed = fm.get("proposed_chunks", [])
            chunk_ids = set()
            for p in proposed:
                if isinstance(p, dict) and p.get("chunk_directory"):
                    chunk_dir = p["chunk_directory"]
                    chunk_name = (
                        chunk_dir.split("/")[-1] if "/" in chunk_dir else chunk_dir
                    )
                    chunk_ids.add(chunk_name)
            graph.friction_to_chunks["friction"] = chunk_ids
        except Exception:
            pass


# ============================================
# PERFORMANCE ANALYSIS
# ============================================
#
# Time complexity for a project with:
#   C chunks, N narratives, I investigations, S subsystems, F friction entries
#   P source files, L total lines of code
#
# scan_artifacts: O(C + N + I + S + F) file reads + YAML parses
# scan_code_backrefs: O(P) file reads + O(L) regex scans
# validate_graph: O(E) where E = total edges
#
# For a medium project (100 chunks, 500 source files, 50k LOC):
#   - scan_artifacts: ~100 file reads, ~50ms
#   - scan_code_backrefs: ~500 file reads, ~200ms
#   - validate_graph: ~1000 edge checks, ~10ms
#   - Total: ~260ms (well under 2-3 second git hook threshold)
#
# For a large project (1000 chunks, 5000 source files, 500k LOC):
#   - scan_artifacts: ~1000 file reads, ~500ms
#   - scan_code_backrefs: ~5000 file reads, ~2s
#   - validate_graph: ~10000 edge checks, ~100ms
#   - Total: ~2.6s (borderline for pre-commit, fine for pre-push)
#
# Optimizations available:
#   - Incremental: Only re-scan files changed since last run (git diff)
#   - Parallel: Use multiprocessing for file reads
#   - Caching: Persist graph to disk, update incrementally
