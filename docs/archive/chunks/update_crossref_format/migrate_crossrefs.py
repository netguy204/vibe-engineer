#!/usr/bin/env python3
"""Migration script to update cross-references from legacy NNNN-short_name to short_name format.

# Chunk: docs/chunks/update_crossref_format - Migration script

This script updates all cross-references in the codebase:
1. Code backreferences: # Chunk: docs/chunks/NNNN-name -> # Chunk: docs/chunks/name
2. Subsystem backreferences: # Subsystem: docs/subsystems/NNNN-name -> # Subsystem: docs/subsystems/name
3. Frontmatter references: chunk_id, parent_chunk, subsystem_id with NNNN- prefix

Usage:
    python docs/chunks/update_crossref_format/migrate_crossrefs.py [--project-dir PATH] [--dry-run]

Options:
    --project-dir PATH  Path to project directory (default: current directory)
    --dry-run           Show what would be changed without making changes
"""

import argparse
import re
import sys
from pathlib import Path


# Patterns for code backreferences (in comments)
# Match: # Chunk: docs/chunks/NNNN-name or # Subsystem: docs/subsystems/NNNN-name
CHUNK_BACKREF_PATTERN = re.compile(
    r"(#\s*Chunk:\s*docs/chunks/)(\d{4})-(\w+)"
)
SUBSYSTEM_BACKREF_PATTERN = re.compile(
    r"(#\s*Subsystem:\s*docs/subsystems/)(\d{4})-(\w+)"
)

# Patterns for frontmatter YAML references
# Match lines like: chunk_id: 0012-symbolic_code_refs
# Or: parent_chunk: 0038-artifact_ordering_index
# Or: subsystem_id: 0001-template_system
FRONTMATTER_CHUNK_ID_PATTERN = re.compile(
    r"^(\s*chunk_id:\s*)(\d{4})-(\w+)(\s*)$", re.MULTILINE
)
FRONTMATTER_PARENT_CHUNK_PATTERN = re.compile(
    r"^(\s*parent_chunk:\s*)(\d{4})-(\w+)(\s*)$", re.MULTILINE
)
FRONTMATTER_SUBSYSTEM_ID_PATTERN = re.compile(
    r"^(\s*subsystem_id:\s*)(\d{4})-(\w+)(\s*)$", re.MULTILINE
)


def update_source_file(file_path: Path, dry_run: bool) -> dict[str, int]:
    """Update code backreferences in a source file.

    Returns:
        Dict with counts: {'chunk': N, 'subsystem': M}
    """
    try:
        content = file_path.read_text()
    except UnicodeDecodeError:
        return {"chunk": 0, "subsystem": 0}

    original_content = content
    counts = {"chunk": 0, "subsystem": 0}

    # Update chunk backreferences
    def replace_chunk(match):
        counts["chunk"] += 1
        prefix = match.group(1)  # "# Chunk: docs/chunks/"
        short_name = match.group(3)  # "symbolic_code_refs"
        return f"{prefix}{short_name}"

    content = CHUNK_BACKREF_PATTERN.sub(replace_chunk, content)

    # Update subsystem backreferences
    def replace_subsystem(match):
        counts["subsystem"] += 1
        prefix = match.group(1)  # "# Subsystem: docs/subsystems/"
        short_name = match.group(3)  # "template_system"
        return f"{prefix}{short_name}"

    content = SUBSYSTEM_BACKREF_PATTERN.sub(replace_subsystem, content)

    if content != original_content:
        if not dry_run:
            file_path.write_text(content)

    return counts


def update_markdown_file(file_path: Path, dry_run: bool) -> dict[str, int]:
    """Update frontmatter references in a markdown file.

    Returns:
        Dict with counts: {'chunk_id': N, 'parent_chunk': M, 'subsystem_id': P}
    """
    try:
        content = file_path.read_text()
    except UnicodeDecodeError:
        return {"chunk_id": 0, "parent_chunk": 0, "subsystem_id": 0}

    # Only process files with frontmatter
    if not content.startswith("---"):
        return {"chunk_id": 0, "parent_chunk": 0, "subsystem_id": 0}

    original_content = content
    counts = {"chunk_id": 0, "parent_chunk": 0, "subsystem_id": 0}

    # Update chunk_id references
    def replace_chunk_id(match):
        counts["chunk_id"] += 1
        prefix = match.group(1)  # "  chunk_id: "
        short_name = match.group(3)  # "symbolic_code_refs"
        trailing = match.group(4)  # whitespace/newline
        return f"{prefix}{short_name}{trailing}"

    content = FRONTMATTER_CHUNK_ID_PATTERN.sub(replace_chunk_id, content)

    # Update parent_chunk references
    def replace_parent_chunk(match):
        counts["parent_chunk"] += 1
        prefix = match.group(1)  # "parent_chunk: "
        short_name = match.group(3)  # "artifact_ordering_index"
        trailing = match.group(4)
        return f"{prefix}{short_name}{trailing}"

    content = FRONTMATTER_PARENT_CHUNK_PATTERN.sub(replace_parent_chunk, content)

    # Update subsystem_id references
    def replace_subsystem_id(match):
        counts["subsystem_id"] += 1
        prefix = match.group(1)  # "  subsystem_id: "
        short_name = match.group(3)  # "template_system"
        trailing = match.group(4)
        return f"{prefix}{short_name}{trailing}"

    content = FRONTMATTER_SUBSYSTEM_ID_PATTERN.sub(replace_subsystem_id, content)

    if content != original_content:
        if not dry_run:
            file_path.write_text(content)

    return counts


def process_directory(
    base_dir: Path,
    patterns: list[str],
    processor,
    dry_run: bool,
    description: str,
) -> dict[str, int]:
    """Process files matching patterns in a directory.

    Returns:
        Aggregated counts from all files.
    """
    total_counts: dict[str, int] = {}
    files_changed = 0

    for pattern in patterns:
        for file_path in base_dir.glob(pattern):
            if file_path.is_file():
                counts = processor(file_path, dry_run)
                if any(v > 0 for v in counts.values()):
                    files_changed += 1
                    if dry_run:
                        print(f"  Would update: {file_path.relative_to(base_dir)}")
                    else:
                        print(f"  Updated: {file_path.relative_to(base_dir)}")

                for key, value in counts.items():
                    total_counts[key] = total_counts.get(key, 0) + value

    return total_counts


def main():
    parser = argparse.ArgumentParser(
        description="Update cross-references from NNNN-name to name format."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Path to project directory (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )

    args = parser.parse_args()
    project_dir = args.project_dir

    if not (project_dir / "src").exists():
        print(f"ERROR: src directory not found in {project_dir}")
        sys.exit(1)

    if args.dry_run:
        print("DRY RUN MODE - no changes will be made\n")

    # Step 1: Update code backreferences in src/
    print("Step 1: Updating code backreferences in src/...")
    src_counts = process_directory(
        project_dir,
        ["src/**/*.py"],
        update_source_file,
        args.dry_run,
        "source files",
    )
    print(f"  Chunk refs: {src_counts.get('chunk', 0)}, Subsystem refs: {src_counts.get('subsystem', 0)}")
    print()

    # Step 2: Update code backreferences in tests/
    print("Step 2: Updating code backreferences in tests/...")
    test_counts = process_directory(
        project_dir,
        ["tests/**/*.py"],
        update_source_file,
        args.dry_run,
        "test files",
    )
    print(f"  Chunk refs: {test_counts.get('chunk', 0)}, Subsystem refs: {test_counts.get('subsystem', 0)}")
    print()

    # Step 3: Update frontmatter references in docs/
    print("Step 3: Updating frontmatter references in docs/...")
    doc_counts = process_directory(
        project_dir,
        ["docs/**/*.md"],
        update_markdown_file,
        args.dry_run,
        "markdown files",
    )
    print(f"  chunk_id refs: {doc_counts.get('chunk_id', 0)}, "
          f"parent_chunk refs: {doc_counts.get('parent_chunk', 0)}, "
          f"subsystem_id refs: {doc_counts.get('subsystem_id', 0)}")
    print()

    # Summary
    total_code_refs = (
        src_counts.get("chunk", 0)
        + src_counts.get("subsystem", 0)
        + test_counts.get("chunk", 0)
        + test_counts.get("subsystem", 0)
    )
    total_frontmatter_refs = (
        doc_counts.get("chunk_id", 0)
        + doc_counts.get("parent_chunk", 0)
        + doc_counts.get("subsystem_id", 0)
    )

    print("=" * 60)
    print("Summary:")
    print(f"  Code backreferences updated: {total_code_refs}")
    print(f"  Frontmatter references updated: {total_frontmatter_refs}")
    print(f"  Total references updated: {total_code_refs + total_frontmatter_refs}")
    print()
    print("Migration complete!" if not args.dry_run else "Dry run complete!")


if __name__ == "__main__":
    main()
