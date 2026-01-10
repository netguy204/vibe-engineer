#!/usr/bin/env python3
"""Migration script to remove sequence prefixes from artifact directory names.

# Chunk: docs/chunks/0044-remove_sequence_prefix - Migration script

This script renames artifact directories from {NNNN}-{short_name} to {short_name}
and updates all frontmatter references (created_after, chunks, subsystems).

Usage:
    python scripts/migrate_artifact_names.py [--project-dir PATH] [--dry-run]

Options:
    --project-dir PATH  Path to project directory (default: current directory)
    --dry-run           Show what would be changed without making changes
"""

import argparse
import re
import sys
from pathlib import Path

import yaml


def extract_short_name(dir_name: str) -> str:
    """Extract short name from directory name, handling both patterns."""
    if re.match(r"^\d{4}-", dir_name):
        return dir_name.split("-", 1)[1]
    return dir_name


def is_legacy_format(dir_name: str) -> bool:
    """Check if directory name uses legacy {NNNN}-{name} format."""
    return bool(re.match(r"^\d{4}-", dir_name))


def rename_directories(docs_dir: Path, artifact_type: str, dry_run: bool) -> dict[str, str]:
    """Rename artifact directories from legacy to new format.

    Returns:
        Mapping of old directory name to new directory name.
    """
    artifact_dir = docs_dir / artifact_type
    if not artifact_dir.exists():
        return {}

    renames = {}
    for item in artifact_dir.iterdir():
        if not item.is_dir():
            continue
        if not is_legacy_format(item.name):
            continue

        short_name = extract_short_name(item.name)
        new_path = artifact_dir / short_name

        if new_path.exists():
            print(f"WARNING: Cannot rename {item.name} -> {short_name}: target exists")
            continue

        renames[item.name] = short_name

        if dry_run:
            print(f"  Would rename: {artifact_type}/{item.name} -> {artifact_type}/{short_name}")
        else:
            item.rename(new_path)
            print(f"  Renamed: {artifact_type}/{item.name} -> {artifact_type}/{short_name}")

    return renames


def update_frontmatter_references(
    docs_dir: Path,
    renames: dict[str, str],
    dry_run: bool
) -> None:
    """Update created_after and other references in frontmatter."""
    # Find all GOAL.md and OVERVIEW.md files
    for pattern in ["chunks/*/GOAL.md", "narratives/*/OVERVIEW.md",
                    "investigations/*/OVERVIEW.md", "subsystems/*/OVERVIEW.md"]:
        for file_path in docs_dir.glob(pattern):
            update_file_references(file_path, renames, dry_run)


def update_file_references(
    file_path: Path,
    renames: dict[str, str],
    dry_run: bool
) -> None:
    """Update references in a single file."""
    content = file_path.read_text()

    # Check if file has frontmatter
    if not content.startswith("---"):
        return

    # Split into frontmatter and body
    parts = content.split("---", 2)
    if len(parts) < 3:
        return

    frontmatter_text = parts[1]
    body = "---".join(parts[2:])

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        if frontmatter is None:
            return
    except yaml.YAMLError:
        return

    changed = False

    # Update created_after
    if "created_after" in frontmatter and frontmatter["created_after"]:
        new_created_after = []
        for ref in frontmatter["created_after"]:
            if ref in renames:
                new_created_after.append(renames[ref])
                changed = True
            else:
                new_created_after.append(ref)
        frontmatter["created_after"] = new_created_after

    # Update chunks (in subsystems)
    if "chunks" in frontmatter and frontmatter["chunks"]:
        for chunk_ref in frontmatter["chunks"]:
            if isinstance(chunk_ref, dict) and "chunk_id" in chunk_ref:
                if chunk_ref["chunk_id"] in renames:
                    chunk_ref["chunk_id"] = renames[chunk_ref["chunk_id"]]
                    changed = True

    # Update subsystems (in chunks)
    if "subsystems" in frontmatter and frontmatter["subsystems"]:
        for subsystem_ref in frontmatter["subsystems"]:
            if isinstance(subsystem_ref, dict) and "subsystem_id" in subsystem_ref:
                if subsystem_ref["subsystem_id"] in renames:
                    subsystem_ref["subsystem_id"] = renames[subsystem_ref["subsystem_id"]]
                    changed = True

    # Update narrative (in chunks)
    if "narrative" in frontmatter and frontmatter["narrative"] in renames:
        frontmatter["narrative"] = renames[frontmatter["narrative"]]
        changed = True

    # Update proposed_chunks chunk_directory
    if "proposed_chunks" in frontmatter and frontmatter["proposed_chunks"]:
        for proposed in frontmatter["proposed_chunks"]:
            if isinstance(proposed, dict) and "chunk_directory" in proposed:
                if proposed["chunk_directory"] in renames:
                    proposed["chunk_directory"] = renames[proposed["chunk_directory"]]
                    changed = True

    if not changed:
        return

    # Reconstruct file
    new_frontmatter_text = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    new_content = f"---\n{new_frontmatter_text}---{body}"

    if dry_run:
        print(f"  Would update references in: {file_path.relative_to(file_path.parent.parent.parent)}")
    else:
        file_path.write_text(new_content)
        print(f"  Updated references in: {file_path.relative_to(file_path.parent.parent.parent)}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate artifact directories from {NNNN}-{name} to {name} format."
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
    docs_dir = project_dir / "docs"

    if not docs_dir.exists():
        print(f"ERROR: docs directory not found in {project_dir}")
        sys.exit(1)

    if args.dry_run:
        print("DRY RUN MODE - no changes will be made\n")

    # Collect all renames
    all_renames: dict[str, str] = {}

    # Rename directories
    print("Step 1: Renaming artifact directories...")
    for artifact_type in ["chunks", "narratives", "investigations", "subsystems"]:
        renames = rename_directories(docs_dir, artifact_type, args.dry_run)
        all_renames.update(renames)

    if not all_renames:
        print("  No directories need renaming.")

    print()

    # Update frontmatter references
    print("Step 2: Updating frontmatter references...")
    if all_renames:
        update_frontmatter_references(docs_dir, all_renames, args.dry_run)
    else:
        print("  No references to update.")

    print()

    # Clean up artifact index
    artifact_index = project_dir / ".artifact-order.json"
    if artifact_index.exists():
        if args.dry_run:
            print("Step 3: Would remove .artifact-order.json for rebuild")
        else:
            artifact_index.unlink()
            print("Step 3: Removed .artifact-order.json (will be rebuilt automatically)")

    print()
    print("Migration complete!" if not args.dry_run else "Dry run complete!")

    if all_renames:
        print(f"\nRenamed {len(all_renames)} artifact(s):")
        for old, new in sorted(all_renames.items()):
            print(f"  {old} -> {new}")


if __name__ == "__main__":
    main()
