"""Cluster rename module - batch rename chunks with a common prefix.

This module provides functionality to rename all chunks matching a prefix pattern
to a new prefix, updating all references across the project.
"""
# Chunk: docs/chunks/cluster_rename - Cluster rename functionality

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from chunks import Chunks
from investigations import Investigations
from narratives import Narratives
from subsystems import Subsystems
from models import extract_short_name


# Step 1: Core discovery function
def find_chunks_by_prefix(project_dir: Path, prefix: str) -> list[str]:
    """Find all chunk directory names that start with {prefix}_.

    Uses strict underscore separation to avoid false matches like
    'task_init' matching when 'task' is the prefix but 'task_foo' doesn't exist.

    Handles both legacy {NNNN}-{short_name} and new {short_name} formats.
    For legacy format, checks the short_name portion after the NNNN- prefix.

    Args:
        project_dir: Path to the project root directory.
        prefix: The prefix to match (without trailing underscore).

    Returns:
        List of chunk directory names that match {prefix}_*.
    """
    chunks = Chunks(project_dir)
    matching = []

    for chunk_name in chunks.enumerate_chunks():
        # Extract the short_name (handles both legacy and new formats)
        short_name = extract_short_name(chunk_name)

        # Check if short_name starts with {prefix}_
        if short_name.startswith(f"{prefix}_"):
            matching.append(chunk_name)

    return sorted(matching)


# Step 2: Collision detection
def check_rename_collisions(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str,
    matching_chunks: list[str],
) -> list[str]:
    """Check if renaming would cause collisions with existing chunk names.

    Args:
        project_dir: Path to the project root directory.
        old_prefix: The old prefix being replaced.
        new_prefix: The new prefix to use.
        matching_chunks: List of chunk names that match the old prefix.

    Returns:
        List of collision error messages, empty if safe to rename.
    """
    chunks = Chunks(project_dir)
    existing_chunks = set(chunks.enumerate_chunks())
    errors = []

    for chunk_name in matching_chunks:
        short_name = extract_short_name(chunk_name)
        # Replace old_prefix with new_prefix at the start of short_name
        new_short_name = new_prefix + short_name[len(old_prefix):]

        # Determine new directory name
        if re.match(r"^\d{4}-", chunk_name):
            # Legacy format: preserve the sequence number
            seq_prefix = chunk_name.split("-", 1)[0]
            new_chunk_name = f"{seq_prefix}-{new_short_name}"
        else:
            new_chunk_name = new_short_name

        # Check for collision (but not with itself in case of case-only changes)
        if new_chunk_name != chunk_name and new_chunk_name in existing_chunks:
            errors.append(
                f"Cannot rename '{chunk_name}' to '{new_chunk_name}': "
                f"target name already exists"
            )

    return errors


# Step 3: Git cleanliness check
def is_git_clean(project_dir: Path) -> bool:
    """Check if git working tree has no uncommitted changes.

    Args:
        project_dir: Path to the project root directory.

    Returns:
        True if working tree has no uncommitted changes, False otherwise.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        # Empty output means clean working tree
        return result.stdout.strip() == ""
    except subprocess.CalledProcessError:
        # If git command fails, assume not clean
        return False


# Step 4: Reference discovery dataclasses and functions
@dataclass
class FrontmatterUpdate:
    """Represents a frontmatter field that needs to be updated."""

    file_path: Path
    field: str
    old_value: str
    new_value: str


def _compute_new_chunk_name(chunk_name: str, old_prefix: str, new_prefix: str) -> str:
    """Compute the new chunk name after prefix replacement.

    Args:
        chunk_name: The current chunk directory name.
        old_prefix: The prefix being replaced.
        new_prefix: The new prefix.

    Returns:
        The new chunk directory name.
    """
    short_name = extract_short_name(chunk_name)
    new_short_name = new_prefix + short_name[len(old_prefix):]

    if re.match(r"^\d{4}-", chunk_name):
        # Legacy format: preserve the sequence number
        seq_prefix = chunk_name.split("-", 1)[0]
        return f"{seq_prefix}-{new_short_name}"
    return new_short_name


def find_created_after_references(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str,
) -> list[FrontmatterUpdate]:
    """Find created_after entries in all chunk GOAL.md files that need updating.

    Args:
        project_dir: Path to the project root directory.
        old_prefix: The prefix being replaced.
        new_prefix: The new prefix.

    Returns:
        List of FrontmatterUpdate objects for each reference to update.
    """
    updates = []
    chunks = Chunks(project_dir)

    for chunk_name in chunks.enumerate_chunks():
        goal_path = chunks.get_chunk_goal_path(chunk_name)
        if goal_path is None or not goal_path.exists():
            continue

        frontmatter = chunks.parse_chunk_frontmatter(chunk_name)
        if frontmatter is None:
            continue

        for ref in frontmatter.created_after:
            # Extract short_name from the reference
            ref_short = extract_short_name(ref)
            if ref_short.startswith(f"{old_prefix}_"):
                new_ref = _compute_new_chunk_name(ref, old_prefix, new_prefix)
                updates.append(FrontmatterUpdate(
                    file_path=goal_path,
                    field="created_after",
                    old_value=ref,
                    new_value=new_ref,
                ))

    return updates


def find_subsystem_chunk_references(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str,
) -> list[FrontmatterUpdate]:
    """Find chunks[].chunk_id in subsystem OVERVIEW.md files that need updating.

    Args:
        project_dir: Path to the project root directory.
        old_prefix: The prefix being replaced.
        new_prefix: The new prefix.

    Returns:
        List of FrontmatterUpdate objects for each reference to update.
    """
    updates = []
    subsystems = Subsystems(project_dir)

    for subsystem_id in subsystems.enumerate_subsystems():
        overview_path = subsystems.subsystems_dir / subsystem_id / "OVERVIEW.md"
        if not overview_path.exists():
            continue

        frontmatter = subsystems.parse_subsystem_frontmatter(subsystem_id)
        if frontmatter is None:
            continue

        for chunk_rel in frontmatter.chunks:
            chunk_id = chunk_rel.chunk_id
            chunk_short = extract_short_name(chunk_id)
            if chunk_short.startswith(f"{old_prefix}_"):
                new_chunk_id = _compute_new_chunk_name(chunk_id, old_prefix, new_prefix)
                updates.append(FrontmatterUpdate(
                    file_path=overview_path,
                    field="chunks[].chunk_id",
                    old_value=chunk_id,
                    new_value=new_chunk_id,
                ))

    return updates


def find_narrative_chunk_references(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str,
) -> list[FrontmatterUpdate]:
    """Find proposed_chunks[].chunk_directory in narrative OVERVIEW.md files.

    Args:
        project_dir: Path to the project root directory.
        old_prefix: The prefix being replaced.
        new_prefix: The new prefix.

    Returns:
        List of FrontmatterUpdate objects for each reference to update.
    """
    updates = []
    narratives = Narratives(project_dir)

    for narrative_id in narratives.enumerate_narratives():
        overview_path = narratives.narratives_dir / narrative_id / "OVERVIEW.md"
        if not overview_path.exists():
            continue

        frontmatter = narratives.parse_narrative_frontmatter(narrative_id)
        if frontmatter is None:
            continue

        for proposed in frontmatter.proposed_chunks:
            if proposed.chunk_directory:
                chunk_short = extract_short_name(proposed.chunk_directory)
                if chunk_short.startswith(f"{old_prefix}_"):
                    new_chunk_dir = _compute_new_chunk_name(
                        proposed.chunk_directory, old_prefix, new_prefix
                    )
                    updates.append(FrontmatterUpdate(
                        file_path=overview_path,
                        field="proposed_chunks[].chunk_directory",
                        old_value=proposed.chunk_directory,
                        new_value=new_chunk_dir,
                    ))

    return updates


def find_investigation_chunk_references(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str,
) -> list[FrontmatterUpdate]:
    """Find proposed_chunks[].chunk_directory in investigation OVERVIEW.md files.

    Args:
        project_dir: Path to the project root directory.
        old_prefix: The prefix being replaced.
        new_prefix: The new prefix.

    Returns:
        List of FrontmatterUpdate objects for each reference to update.
    """
    updates = []
    investigations = Investigations(project_dir)

    for inv_id in investigations.enumerate_investigations():
        overview_path = investigations.investigations_dir / inv_id / "OVERVIEW.md"
        if not overview_path.exists():
            continue

        frontmatter = investigations.parse_investigation_frontmatter(inv_id)
        if frontmatter is None:
            continue

        for proposed in frontmatter.proposed_chunks:
            if proposed.chunk_directory:
                chunk_short = extract_short_name(proposed.chunk_directory)
                if chunk_short.startswith(f"{old_prefix}_"):
                    new_chunk_dir = _compute_new_chunk_name(
                        proposed.chunk_directory, old_prefix, new_prefix
                    )
                    updates.append(FrontmatterUpdate(
                        file_path=overview_path,
                        field="proposed_chunks[].chunk_directory",
                        old_value=proposed.chunk_directory,
                        new_value=new_chunk_dir,
                    ))

    return updates


# Step 5: Code backreference discovery
@dataclass
class BackreferenceUpdate:
    """Represents a code backreference that needs to be updated."""

    file_path: Path
    line_number: int
    old_line: str
    new_line: str


def find_code_backreferences(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str,
    matching_chunks: list[str],
) -> list[BackreferenceUpdate]:
    """Find # Chunk: docs/chunks/{matching_chunk} comments in source files.

    Args:
        project_dir: Path to the project root directory.
        old_prefix: The prefix being replaced.
        new_prefix: The new prefix.
        matching_chunks: List of chunk names that match the old prefix.

    Returns:
        List of BackreferenceUpdate objects for each backreference to update.
    """
    updates = []

    # Build a mapping of old chunk names to new chunk names
    name_mapping = {}
    for chunk_name in matching_chunks:
        new_name = _compute_new_chunk_name(chunk_name, old_prefix, new_prefix)
        name_mapping[chunk_name] = new_name

    # Search for backreferences in source files
    # Use ripgrep for efficiency, fall back to manual search if not available
    source_extensions = ["py", "ts", "js", "tsx", "jsx", "rs", "go", "java", "rb"]

    try:
        # Build pattern to match any of the old chunk names
        pattern = "|".join(re.escape(name) for name in matching_chunks)
        rg_pattern = f"# Chunk: docs/chunks/({pattern})"

        result = subprocess.run(
            ["rg", "-n", "--no-heading", rg_pattern, "--type-add",
             f"src:*.{{{','.join(source_extensions)}}}", "-tsrc", "."],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                # Parse rg output: file:line:content
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    file_path = project_dir / parts[0]
                    line_num = int(parts[1])
                    content = parts[2]

                    # Find which chunk name is in this line
                    for old_name, new_name in name_mapping.items():
                        if f"docs/chunks/{old_name}" in content:
                            new_content = content.replace(
                                f"docs/chunks/{old_name}",
                                f"docs/chunks/{new_name}"
                            )
                            updates.append(BackreferenceUpdate(
                                file_path=file_path,
                                line_number=line_num,
                                old_line=content,
                                new_line=new_content,
                            ))
                            break
    except FileNotFoundError:
        # ripgrep not available, do manual search
        updates = _find_backreferences_manual(project_dir, name_mapping, source_extensions)

    return updates


def _find_backreferences_manual(
    project_dir: Path,
    name_mapping: dict[str, str],
    extensions: list[str],
) -> list[BackreferenceUpdate]:
    """Manually search for backreferences without ripgrep.

    Args:
        project_dir: Path to the project root directory.
        name_mapping: Mapping of old chunk names to new names.
        extensions: List of file extensions to search.

    Returns:
        List of BackreferenceUpdate objects.
    """
    updates = []

    # Walk through project looking for source files
    for ext in extensions:
        for file_path in project_dir.rglob(f"*.{ext}"):
            # Skip hidden directories and common non-source locations
            if any(part.startswith(".") for part in file_path.parts):
                continue
            if "node_modules" in file_path.parts:
                continue
            if "__pycache__" in file_path.parts:
                continue

            try:
                content = file_path.read_text()
            except (OSError, UnicodeDecodeError):
                continue

            for line_num, line in enumerate(content.split("\n"), 1):
                if "# Chunk: docs/chunks/" in line:
                    for old_name, new_name in name_mapping.items():
                        if f"docs/chunks/{old_name}" in line:
                            new_line = line.replace(
                                f"docs/chunks/{old_name}",
                                f"docs/chunks/{new_name}"
                            )
                            updates.append(BackreferenceUpdate(
                                file_path=file_path,
                                line_number=line_num,
                                old_line=line,
                                new_line=new_line,
                            ))
                            break

    return updates


# Step 6: Prose reference discovery
def find_prose_references(
    project_dir: Path,
    matching_chunks: list[str],
) -> list[tuple[Path, int, str]]:
    """Find potential prose references that might need manual review.

    Searches markdown and other documentation files for chunk name mentions
    that cannot be safely auto-updated.

    Args:
        project_dir: Path to the project root directory.
        matching_chunks: List of chunk names being renamed.

    Returns:
        List of tuples (file_path, line_number, line_content) for manual review.
    """
    results = []

    # Build pattern to match any of the chunk names
    # Exclude the standard code backreference pattern since those are auto-updated
    patterns = [re.escape(name) for name in matching_chunks]

    try:
        # Use ripgrep to search markdown and text files
        pattern = "|".join(patterns)

        result = subprocess.run(
            ["rg", "-n", "--no-heading", pattern, "-t", "md", "-t", "txt", "."],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    file_path = project_dir / parts[0]
                    line_num = int(parts[1])
                    content = parts[2]

                    # Skip if this is just a standard backreference
                    if "# Chunk: docs/chunks/" in content:
                        continue
                    # Skip frontmatter fields we handle automatically
                    if content.strip().startswith("- ") and content.strip().endswith(":"):
                        continue
                    if "created_after:" in content:
                        continue
                    if "chunk_directory:" in content:
                        continue
                    if "chunk_id:" in content:
                        continue

                    results.append((file_path, line_num, content))

    except FileNotFoundError:
        # ripgrep not available, do manual search
        results = _find_prose_manual(project_dir, matching_chunks)

    return results


def _find_prose_manual(
    project_dir: Path,
    matching_chunks: list[str],
) -> list[tuple[Path, int, str]]:
    """Manual prose reference search without ripgrep."""
    results = []

    for file_path in project_dir.rglob("*.md"):
        if any(part.startswith(".") for part in file_path.parts):
            continue

        try:
            content = file_path.read_text()
        except (OSError, UnicodeDecodeError):
            continue

        for line_num, line in enumerate(content.split("\n"), 1):
            for chunk_name in matching_chunks:
                if chunk_name in line:
                    # Skip standard backreferences
                    if "# Chunk: docs/chunks/" in line:
                        continue
                    if "created_after:" in line:
                        continue
                    if "chunk_directory:" in line:
                        continue
                    if "chunk_id:" in line:
                        continue

                    results.append((file_path, line_num, line))
                    break  # Don't report same line multiple times

    return results


# Step 7: Dry-run output formatter
@dataclass
class RenamePreview:
    """Preview of all changes that would be made by a cluster rename."""

    directories: list[tuple[str, str]]  # (old_name, new_name)
    frontmatter_updates: list[FrontmatterUpdate] = field(default_factory=list)
    backreference_updates: list[BackreferenceUpdate] = field(default_factory=list)
    prose_references: list[tuple[Path, int, str]] = field(default_factory=list)


def format_dry_run_output(preview: RenamePreview, project_dir: Path) -> str:
    """Format the dry-run preview for display.

    Args:
        preview: The RenamePreview to format.
        project_dir: Project root for relative path display.

    Returns:
        Formatted string for display.
    """
    lines = []

    # Directories to be renamed
    lines.append("## Directories to be renamed")
    lines.append("")
    if preview.directories:
        for old_name, new_name in preview.directories:
            lines.append(f"  docs/chunks/{old_name} -> docs/chunks/{new_name}")
    else:
        lines.append("  (none)")
    lines.append("")

    # Frontmatter updates grouped by file
    lines.append("## Frontmatter references to be updated")
    lines.append("")
    if preview.frontmatter_updates:
        by_file: dict[Path, list[FrontmatterUpdate]] = {}
        for update in preview.frontmatter_updates:
            by_file.setdefault(update.file_path, []).append(update)

        for file_path, updates in sorted(by_file.items()):
            try:
                rel_path = file_path.relative_to(project_dir)
            except ValueError:
                rel_path = file_path
            lines.append(f"  {rel_path}:")
            for update in updates:
                lines.append(f"    {update.field}: {update.old_value} -> {update.new_value}")
    else:
        lines.append("  (none)")
    lines.append("")

    # Code backreferences
    lines.append("## Code backreferences to be updated")
    lines.append("")
    if preview.backreference_updates:
        for update in preview.backreference_updates:
            try:
                rel_path = update.file_path.relative_to(project_dir)
            except ValueError:
                rel_path = update.file_path
            lines.append(f"  {rel_path}:{update.line_number}")
    else:
        lines.append("  (none)")
    lines.append("")

    # Prose references for manual review
    lines.append("## Prose references requiring manual review")
    lines.append("")
    if preview.prose_references:
        for file_path, line_num, content in preview.prose_references:
            try:
                rel_path = file_path.relative_to(project_dir)
            except ValueError:
                rel_path = file_path
            # Truncate long lines
            display_content = content.strip()
            if len(display_content) > 80:
                display_content = display_content[:77] + "..."
            lines.append(f"  {rel_path}:{line_num}: {display_content}")
    else:
        lines.append("  (none)")

    return "\n".join(lines)


# Step 8: Execution functions
def rename_chunk_directories(
    project_dir: Path,
    renames: list[tuple[str, str]],
) -> None:
    """Rename chunk directories from old to new names.

    Args:
        project_dir: Path to the project root directory.
        renames: List of (old_name, new_name) tuples.
    """
    chunks_dir = project_dir / "docs" / "chunks"

    for old_name, new_name in renames:
        old_path = chunks_dir / old_name
        new_path = chunks_dir / new_name
        old_path.rename(new_path)


def update_frontmatter_references(updates: list[FrontmatterUpdate]) -> None:
    """Update frontmatter references in YAML files.

    Uses simple string replacement within frontmatter to preserve formatting.

    Args:
        updates: List of FrontmatterUpdate objects describing changes.
    """
    # Group updates by file
    by_file: dict[Path, list[FrontmatterUpdate]] = {}
    for update in updates:
        by_file.setdefault(update.file_path, []).append(update)

    for file_path, file_updates in by_file.items():
        content = file_path.read_text()

        # Find frontmatter section
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            continue

        frontmatter_text = match.group(1)
        body = match.group(2)

        # Apply replacements to frontmatter
        for update in file_updates:
            # Replace old_value with new_value in frontmatter
            # Be careful to only replace exact matches
            frontmatter_text = frontmatter_text.replace(update.old_value, update.new_value)

        # Reconstruct file
        new_content = f"---\n{frontmatter_text}\n---\n{body}"
        file_path.write_text(new_content)


def update_code_backreferences(updates: list[BackreferenceUpdate]) -> None:
    """Update code backreferences in source files.

    Args:
        updates: List of BackreferenceUpdate objects describing changes.
    """
    # Group updates by file
    by_file: dict[Path, list[BackreferenceUpdate]] = {}
    for update in updates:
        by_file.setdefault(update.file_path, []).append(update)

    for file_path, file_updates in by_file.items():
        content = file_path.read_text()
        lines = content.split("\n")

        # Apply updates (sorted by line number descending to preserve indices)
        for update in sorted(file_updates, key=lambda u: u.line_number, reverse=True):
            # Line numbers are 1-indexed
            idx = update.line_number - 1
            if 0 <= idx < len(lines):
                lines[idx] = update.new_line

        file_path.write_text("\n".join(lines))


# Step 9: Main orchestration function
@dataclass
class ClusterRenameResult:
    """Result of a cluster rename operation."""

    preview: RenamePreview
    git_dirty: bool = False


def cluster_rename(
    project_dir: Path,
    old_prefix: str,
    new_prefix: str,
    execute: bool = False,
) -> ClusterRenameResult:
    """Perform cluster rename operation.

    In dry-run mode (execute=False), returns preview without making changes.
    In execute mode, applies all changes and returns what was changed.

    Args:
        project_dir: Path to the project root directory.
        old_prefix: The prefix to replace.
        new_prefix: The new prefix to use.
        execute: If True, apply changes. If False, preview only.

    Returns:
        ClusterRenameResult with preview and git status info.

    Raises:
        ValueError: If no chunks match or collisions exist.
    """
    # Discovery phase
    matching_chunks = find_chunks_by_prefix(project_dir, old_prefix)
    if not matching_chunks:
        raise ValueError(f"No chunks found matching prefix '{old_prefix}_'")

    # Collision detection
    collisions = check_rename_collisions(project_dir, old_prefix, new_prefix, matching_chunks)
    if collisions:
        raise ValueError("\n".join(collisions))

    # Git cleanliness check (informational only, does not block)
    git_dirty = not is_git_clean(project_dir)

    # Build directory renames
    directories = []
    for chunk_name in matching_chunks:
        new_name = _compute_new_chunk_name(chunk_name, old_prefix, new_prefix)
        directories.append((chunk_name, new_name))

    # Discover all references
    frontmatter_updates = []
    frontmatter_updates.extend(find_created_after_references(project_dir, old_prefix, new_prefix))
    frontmatter_updates.extend(find_subsystem_chunk_references(project_dir, old_prefix, new_prefix))
    frontmatter_updates.extend(find_narrative_chunk_references(project_dir, old_prefix, new_prefix))
    frontmatter_updates.extend(find_investigation_chunk_references(project_dir, old_prefix, new_prefix))

    backreference_updates = find_code_backreferences(
        project_dir, old_prefix, new_prefix, matching_chunks
    )

    prose_references = find_prose_references(project_dir, matching_chunks)

    preview = RenamePreview(
        directories=directories,
        frontmatter_updates=frontmatter_updates,
        backreference_updates=backreference_updates,
        prose_references=prose_references,
    )

    # Execute if requested
    if execute:
        rename_chunk_directories(project_dir, directories)
        update_frontmatter_references(frontmatter_updates)
        update_code_backreferences(backreference_updates)

    return ClusterRenameResult(preview=preview, git_dirty=git_dirty)
