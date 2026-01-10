"""Prototype the chunk creation flow with created_after.

Run with: uv run python prototypes/creation_flow.py

This explores:
1. How to find current tips (chunks with no dependents)
2. How new chunk creation should populate created_after
3. Collision detection for short names
"""
import pathlib
import re
import yaml
from collections import defaultdict


def extract_short_name(dir_name: str) -> str:
    """Extract short name from directory name."""
    match = re.match(r'^(\d{4})-(.+?)(-[a-zA-Z]+-\d+|-[a-zA-Z]+\d+)?$', dir_name)
    if match:
        return match.group(2)
    return dir_name


def parse_frontmatter(goal_path: pathlib.Path) -> dict:
    """Parse YAML frontmatter from a file."""
    content = goal_path.read_text()
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def find_tips(chunk_dir: pathlib.Path) -> list[str]:
    """Find current tips - chunks that no other chunk references in created_after.

    In the new model, tips are chunks that could be parents of a new chunk.
    """
    chunks = [d.name for d in chunk_dir.iterdir() if d.is_dir()]

    # Collect all created_after references
    referenced = set()
    for chunk_name in chunks:
        goal = chunk_dir / chunk_name / "GOAL.md"
        if goal.exists():
            fm = parse_frontmatter(goal)
            created_after = fm.get("created_after", [])
            if created_after is None:
                created_after = []
            elif isinstance(created_after, str):
                created_after = [created_after]

            # References are short names in the new model
            for ref in created_after:
                referenced.add(ref)

    # Tips = chunks not referenced by any other chunk
    tips = []
    for chunk_name in chunks:
        short = extract_short_name(chunk_name)
        if short not in referenced:
            tips.append(short)

    return sorted(tips)


def check_short_name_collision(chunk_dir: pathlib.Path, proposed_name: str) -> str | None:
    """Check if a short name would collide with existing chunks.

    Returns the existing directory name if collision, None otherwise.
    """
    for d in chunk_dir.iterdir():
        if d.is_dir():
            existing_short = extract_short_name(d.name)
            if existing_short == proposed_name:
                return d.name
    return None


def simulate_chunk_creation(chunk_dir: pathlib.Path, short_name: str, ticket_id: str | None = None):
    """Simulate what would happen when creating a new chunk."""
    print(f"=== Simulating creation of chunk '{short_name}' ===\n")

    # Check for collision
    collision = check_short_name_collision(chunk_dir, short_name)
    if collision:
        print(f"ERROR: Short name collision with existing: {collision}")
        print("Options:")
        print("  1. Choose a different short name")
        print("  2. Add distinguishing suffix (e.g., 'foo_v2', 'foo_refactor')")
        if ticket_id:
            print(f"  3. Ticket ID '{ticket_id}' would NOT prevent collision (short name is the handle)")
        return

    # Find tips
    tips = find_tips(chunk_dir)
    print(f"Current tips (potential parents): {len(tips)}")
    if len(tips) <= 5:
        for tip in tips:
            print(f"  - {tip}")
    else:
        print(f"  (showing first 5 of {len(tips)})")
        for tip in tips[:5]:
            print(f"  - {tip}")
    print()

    # What the new chunk's frontmatter would look like
    print("New chunk frontmatter would include:")
    print("---")
    print(f"created_after: {tips if tips else '[]'}")
    print("---")
    print()

    # Directory name
    if ticket_id:
        dir_name = f"{short_name}-{ticket_id}"
    else:
        dir_name = short_name
    print(f"Directory name: docs/chunks/{dir_name}/")
    print()

    # After creation
    print("After creation:")
    print(f"  - '{short_name}' becomes the only tip")
    print(f"  - Previous tips ({len(tips)}) are now ancestors")


def demo_creation_scenarios(chunk_dir: pathlib.Path):
    """Demo various creation scenarios."""
    print("=" * 60)
    print("CHUNK CREATION FLOW SIMULATION")
    print("=" * 60)
    print()

    # Scenario 1: Normal creation
    simulate_chunk_creation(chunk_dir, "new_feature")
    print()

    # Scenario 2: Collision
    print("-" * 60)
    print()
    # Use an existing short name
    existing = list(chunk_dir.iterdir())[0].name if list(chunk_dir.iterdir()) else None
    if existing:
        short = extract_short_name(existing)
        simulate_chunk_creation(chunk_dir, short)
    print()

    # Scenario 3: With ticket
    print("-" * 60)
    print()
    simulate_chunk_creation(chunk_dir, "api_refactor", "JIRA-456")


if __name__ == "__main__":
    chunk_dir = pathlib.Path("docs/chunks")
    demo_creation_scenarios(chunk_dir)
