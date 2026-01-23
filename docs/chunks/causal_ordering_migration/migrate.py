"""One-time migration to populate created_after fields for existing artifacts.

# Chunk: docs/chunks/0042-causal_ordering_migration - Causal ordering migration

Run with: uv run python docs/chunks/0042-causal_ordering_migration/migrate.py

This script populates `created_after` fields for all existing artifacts (chunks,
narratives, investigations, subsystems) by using sequence number order to create
a linear chain.

Migration strategy:
1. Sort artifacts by sequence number prefix (e.g., 0001-, 0002-)
2. Each artifact's `created_after` = [full directory name of previous artifact]
3. First artifact of each type has `created_after: []`

This is a one-time migration for this repository. Future users of Vibe Engineering
get causal ordering from the start via chunk 0039-populate_created_after.
"""

import json
import re
from pathlib import Path

import yaml


def extract_short_name(dir_name: str) -> str:
    """Extract short name from directory name.

    Handles formats:
    - 0001-short_name -> short_name
    - 0001-short_name-ve-001 -> short_name (ticket suffix stripped)
    - 0001-short_name-ticket123 -> short_name (ticket suffix stripped)

    Args:
        dir_name: Directory name like "0001-foo" or "0001-foo-ve-001"

    Returns:
        The short name portion (e.g., "foo")
    """
    # Pattern: NNNN-short_name[-ticket_suffix]
    # Ticket suffixes: -ve-NNN, -ticketNNN, etc.
    match = re.match(r"^(\d{4})-(.+?)(-[a-zA-Z]+-\d+|-[a-zA-Z]+\d+)?$", dir_name)
    if match:
        return match.group(2)
    return dir_name


def extract_sequence_number(dir_name: str) -> int:
    """Extract sequence number from directory name.

    Args:
        dir_name: Directory name like "0001-foo" or "0042-bar"

    Returns:
        The sequence number (e.g., 1 or 42), or 0 if no prefix found
    """
    match = re.match(r"^(\d{4})-", dir_name)
    if match:
        return int(match.group(1))
    return 0


def parse_frontmatter(file_path: Path) -> tuple[dict | None, str, str]:
    """Parse YAML frontmatter from a markdown file.

    Args:
        file_path: Path to markdown file with YAML frontmatter

    Returns:
        Tuple of (frontmatter_dict, yaml_text, rest_of_file)
        Returns (None, "", content) if no frontmatter found
    """
    content = file_path.read_text()

    # Match frontmatter: --- at start, YAML content, ---
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    if not match:
        return None, "", content

    yaml_text = match.group(1)
    rest = match.group(2)

    try:
        frontmatter = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        return None, yaml_text, rest

    return frontmatter, yaml_text, rest


def update_frontmatter(file_path: Path, created_after: list[str]) -> bool:
    """Update the created_after field in a file's frontmatter.

    Preserves all other frontmatter fields. Uses string manipulation to avoid
    reformatting the entire YAML (which could change list styles, etc.).

    Args:
        file_path: Path to the markdown file
        created_after: New value for created_after field

    Returns:
        True if file was updated, False if skipped (no frontmatter)
    """
    content = file_path.read_text()

    # Match frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False

    yaml_text = match.group(1)
    end_pos = match.end()
    rest = content[end_pos:]

    # Parse frontmatter to check current value
    try:
        frontmatter = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        return False

    # Format the new created_after value as JSON array for consistency
    new_value = json.dumps(created_after)

    # Check if created_after already exists in the YAML
    if re.search(r"^created_after:", yaml_text, re.MULTILINE):
        # Replace existing created_after line
        new_yaml = re.sub(
            r"^created_after:.*$",
            f"created_after: {new_value}",
            yaml_text,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        # Add created_after before the closing ---
        # Find the best place to insert (after subsystems if present, else at end)
        if "subsystems:" in yaml_text:
            # Insert after subsystems block - find last line of subsystems
            lines = yaml_text.split("\n")
            insert_idx = len(lines)
            in_subsystems = False
            for i, line in enumerate(lines):
                if line.startswith("subsystems:"):
                    in_subsystems = True
                elif in_subsystems and (
                    line and not line[0].isspace() and not line.startswith("-")
                ):
                    insert_idx = i
                    break
            lines.insert(insert_idx, f"created_after: {new_value}")
            new_yaml = "\n".join(lines)
        else:
            # Just add at end
            new_yaml = yaml_text.rstrip() + f"\ncreated_after: {new_value}"

    # Reconstruct file
    new_content = f"---\n{new_yaml}\n---{rest}"
    file_path.write_text(new_content)
    return True


def migrate_artifact_type(
    artifact_dir: Path, main_file: str, dry_run: bool = False
) -> list[dict]:
    """Migrate all artifacts of a type to have created_after populated.

    Args:
        artifact_dir: Directory containing artifact subdirectories
        main_file: Name of the main file (GOAL.md or OVERVIEW.md)
        dry_run: If True, don't write files, just return plan

    Returns:
        List of migration actions taken: [{"dir": str, "short": str, "after": list}]
    """
    if not artifact_dir.exists():
        return []

    # Find all artifact directories
    dirs = sorted(
        [d.name for d in artifact_dir.iterdir() if d.is_dir() and (d / main_file).exists()],
        key=extract_sequence_number,
    )

    if not dirs:
        return []

    actions = []
    prev_dir = None

    for dir_name in dirs:
        short = extract_short_name(dir_name)
        # Use full directory name for created_after, matching how new artifacts are created
        created_after = [prev_dir] if prev_dir else []

        action = {"dir": dir_name, "short": short, "after": created_after}
        actions.append(action)

        if not dry_run:
            file_path = artifact_dir / dir_name / main_file
            update_frontmatter(file_path, created_after)

        prev_dir = dir_name

    return actions


def migrate_all(project_root: Path, dry_run: bool = False) -> dict[str, list[dict]]:
    """Migrate all artifact types.

    Args:
        project_root: Root directory of the project
        dry_run: If True, don't write files, just return plan

    Returns:
        Dict mapping artifact type to list of migration actions
    """
    docs = project_root / "docs"

    results = {}

    # Chunks: docs/chunks/, main file GOAL.md
    results["chunks"] = migrate_artifact_type(
        docs / "chunks", "GOAL.md", dry_run=dry_run
    )

    # Narratives: docs/narratives/, main file OVERVIEW.md
    results["narratives"] = migrate_artifact_type(
        docs / "narratives", "OVERVIEW.md", dry_run=dry_run
    )

    # Investigations: docs/investigations/, main file OVERVIEW.md
    results["investigations"] = migrate_artifact_type(
        docs / "investigations", "OVERVIEW.md", dry_run=dry_run
    )

    # Subsystems: docs/subsystems/, main file OVERVIEW.md
    results["subsystems"] = migrate_artifact_type(
        docs / "subsystems", "OVERVIEW.md", dry_run=dry_run
    )

    return results


def find_project_root(start: Path) -> Path | None:
    """Find project root by looking for docs/trunk/GOAL.md.

    Args:
        start: Starting directory for search

    Returns:
        Path to project root, or None if not found
    """
    current = start.resolve()
    while current != current.parent:
        if (current / "docs" / "trunk" / "GOAL.md").exists():
            return current
        current = current.parent
    return None


def main():
    """Run the migration."""
    # Find project root
    script_path = Path(__file__).resolve()
    project_root = find_project_root(script_path.parent)

    if not project_root:
        print("Error: Could not find project root (no docs/trunk/GOAL.md found)")
        return 1

    print(f"Project root: {project_root}")
    print()

    # Show dry run first
    print("=== Migration Plan (dry run) ===")
    print()

    plan = migrate_all(project_root, dry_run=True)

    for artifact_type, actions in plan.items():
        print(f"{artifact_type}: {len(actions)} artifacts")
        if actions:
            # Show first and last
            first = actions[0]
            last = actions[-1]
            print(f"  First: {first['dir']} -> created_after: {first['after']}")
            print(f"  Last:  {last['dir']} -> created_after: {last['after']}")
        print()

    # Execute migration
    print("=== Executing Migration ===")
    print()

    results = migrate_all(project_root, dry_run=False)

    total = sum(len(actions) for actions in results.values())
    print(f"Migrated {total} artifacts:")
    for artifact_type, actions in results.items():
        print(f"  {artifact_type}: {len(actions)}")

    print()
    print("Migration complete!")
    print()
    print("Verify with:")
    print("  ve chunk list")
    print("  ve narrative list")
    print("  ve investigation list")
    print("  ve subsystem list")

    return 0


if __name__ == "__main__":
    exit(main())
