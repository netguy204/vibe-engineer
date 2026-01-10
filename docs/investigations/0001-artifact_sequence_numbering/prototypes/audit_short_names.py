"""Audit short name uniqueness across all artifact types.

Run with: uv run python prototypes/audit_short_names.py

Results (2026-01-10):
- All 36 chunks have unique short names
- All 3 narratives have unique short names
- All 2 subsystems have unique short names
- 1 investigation has unique short name
- No cross-type collisions

Conclusion: Short names can serve as unique handles.
"""
import pathlib
import re
from collections import defaultdict


def extract_short_name(dir_name: str) -> str:
    """Extract short name from directory name like '0001-feature_name' or '0001-feature_name-TICKET'.

    Examples:
        '0001-implement_chunk_start' -> 'implement_chunk_start'
        '0001-implement_chunk_start-ve-001' -> 'implement_chunk_start'
        '0002-chunk_list_command-JIRA-123' -> 'chunk_list_command'
    """
    # Remove leading sequence number
    match = re.match(r'^\d{4}-(.+)$', dir_name)
    if not match:
        return dir_name
    remainder = match.group(1)

    # Check for trailing ticket ID (e.g., -ve-001, -JIRA-123)
    # Pattern: ends with -LETTERS-DIGITS or -LETTERS followed by DIGITS
    ticket_match = re.match(r'^(.+)-([a-zA-Z]+-\d+|[a-zA-Z]+\d+)$', remainder)
    if ticket_match:
        return ticket_match.group(1)

    return remainder


def audit_artifact_type(base_dir: pathlib.Path, artifact_type: str) -> dict:
    """Audit short names for an artifact type."""
    if not base_dir.exists():
        return {"dirs": [], "short_names": {}, "duplicates": {}}

    dirs = [d.name for d in base_dir.iterdir() if d.is_dir()]

    # Map short names to directories
    short_to_dirs = defaultdict(list)
    for d in dirs:
        short = extract_short_name(d)
        short_to_dirs[short].append(d)

    # Find duplicates
    duplicates = {k: v for k, v in short_to_dirs.items() if len(v) > 1}

    return {
        "dirs": dirs,
        "short_names": dict(short_to_dirs),
        "duplicates": duplicates,
    }


def main():
    docs = pathlib.Path("docs")

    artifact_types = [
        ("chunks", docs / "chunks"),
        ("narratives", docs / "narratives"),
        ("subsystems", docs / "subsystems"),
        ("investigations", docs / "investigations"),
    ]

    print("=== Short Name Uniqueness Audit ===\n")

    all_unique = True
    for name, path in artifact_types:
        result = audit_artifact_type(path, name)
        count = len(result["dirs"])
        unique = len(result["short_names"])
        dups = result["duplicates"]

        status = "✓" if not dups else "✗"
        print(f"{status} {name}: {count} artifacts, {unique} unique short names")

        if dups:
            all_unique = False
            for short, dirs in dups.items():
                print(f"    DUPLICATE '{short}': {dirs}")

        # Show all short names for review
        if count <= 10:
            for short, dirs in sorted(result["short_names"].items()):
                print(f"    {short} <- {dirs}")
        print()

    # Cross-type analysis
    print("=== Cross-Type Short Name Analysis ===\n")

    # Collect all short names across types
    all_shorts = defaultdict(list)
    for name, path in artifact_types:
        result = audit_artifact_type(path, name)
        for short in result["short_names"]:
            all_shorts[short].append(name)

    # Find names used in multiple types
    cross_type = {k: v for k, v in all_shorts.items() if len(v) > 1}
    if cross_type:
        print("Short names used in multiple artifact types:")
        for short, types in sorted(cross_type.items()):
            print(f"  '{short}' in: {types}")
    else:
        print("No short name collisions across artifact types.")

    print()
    print("=== Summary ===")
    if all_unique:
        print("All short names are unique within their artifact type.")
    else:
        print("WARNING: Some short name duplicates exist.")


if __name__ == "__main__":
    main()
