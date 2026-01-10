"""Prototype migration strategy for existing chunks.

Run with: uv run python prototypes/migration_strategy.py

The key insight: Sequence numbers captured creation order, which is a
reasonable approximation of causal order. We can use this to bootstrap
the `created_after` graph.

Migration strategy:
1. Sort chunks by sequence number
2. Each chunk's `created_after` = [short_name of previous chunk]
3. First chunk has `created_after: []`

This creates a linear chain that preserves the existing order.
"""
import pathlib
import re
import yaml


def extract_short_name(dir_name: str) -> str:
    """Extract short name from directory name."""
    match = re.match(r'^(\d{4})-(.+?)(-[a-zA-Z]+-\d+|-[a-zA-Z]+\d+)?$', dir_name)
    if match:
        return match.group(2)
    return dir_name


def extract_sequence_number(dir_name: str) -> int:
    """Extract sequence number from directory name."""
    match = re.match(r'^(\d{4})-', dir_name)
    if match:
        return int(match.group(1))
    return 0


def generate_migration_plan(chunk_dir: pathlib.Path) -> list[dict]:
    """Generate a migration plan for existing chunks.

    Returns list of {dir_name, short_name, created_after} dicts.
    """
    chunks = sorted(
        [d.name for d in chunk_dir.iterdir() if d.is_dir()],
        key=extract_sequence_number
    )

    plan = []
    prev_short = None

    for dir_name in chunks:
        short = extract_short_name(dir_name)
        created_after = [prev_short] if prev_short else []

        plan.append({
            "dir_name": dir_name,
            "short_name": short,
            "new_dir_name": short,  # Without sequence number
            "created_after": created_after,
        })

        prev_short = short

    return plan


def preview_migration(chunk_dir: pathlib.Path):
    """Preview what the migration would do."""
    plan = generate_migration_plan(chunk_dir)

    print("=== Migration Plan Preview ===\n")
    print(f"Total chunks to migrate: {len(plan)}\n")

    print("First 10 chunks:")
    print("-" * 70)
    for entry in plan[:10]:
        old = entry["dir_name"]
        new = entry["new_dir_name"]
        after = entry["created_after"]
        print(f"  {old}")
        print(f"    -> {new}/")
        print(f"       created_after: {after}")
        print()

    print("...")
    print()

    print("Last 3 chunks:")
    print("-" * 70)
    for entry in plan[-3:]:
        old = entry["dir_name"]
        new = entry["new_dir_name"]
        after = entry["created_after"]
        print(f"  {old}")
        print(f"    -> {new}/")
        print(f"       created_after: {after}")
        print()

    # After migration state
    print("=== After Migration ===\n")
    last = plan[-1] if plan else None
    if last:
        print(f"Single tip: {last['short_name']}")
        print(f"Chain length: {len(plan)}")
        print()

    # What new chunk creation looks like
    print("=== New Chunk Creation (post-migration) ===\n")
    if last:
        print(f"New chunk 'my_new_feature' would have:")
        print(f"  created_after: ['{last['short_name']}']")
        print()
        print("Much cleaner than listing all 36 previous chunks!")


def analyze_directory_rename_impact(chunk_dir: pathlib.Path):
    """Analyze what references would need updating if directories are renamed."""
    plan = generate_migration_plan(chunk_dir)

    print("\n=== Directory Rename Impact ===\n")

    # Build old->new mapping
    renames = {e["dir_name"]: e["new_dir_name"] for e in plan}

    # Find references in code that would need updating
    print("References that would need updating:")
    print("  - docs/chunks/* paths in code comments (# Chunk: docs/chunks/0001-...)")
    print("  - Frontmatter references (narrative, subsystems, parent_chunk)")
    print("  - Any external links or documentation")
    print()

    # Check if any chunks reference others by full path
    print("Current cross-references in frontmatter:")
    refs_found = 0
    for entry in plan:
        goal = chunk_dir / entry["dir_name"] / "GOAL.md"
        if goal.exists():
            content = goal.read_text()
            # Look for references to other chunk directories
            for other in plan:
                if other["dir_name"] != entry["dir_name"]:
                    if other["dir_name"] in content:
                        print(f"  {entry['dir_name']} references {other['dir_name']}")
                        refs_found += 1

    if refs_found == 0:
        print("  (none found in frontmatter)")

    print()
    print("NOTE: A migration would also need to update:")
    print("  - src/chunks.py (list_chunks regex, etc.)")
    print("  - Any code that parses chunk directory names")
    print("  - Tests that reference chunk directories")


if __name__ == "__main__":
    chunk_dir = pathlib.Path("docs/chunks")
    preview_migration(chunk_dir)
    analyze_directory_rename_impact(chunk_dir)
