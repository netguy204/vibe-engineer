"""Prototype git-hash-based staleness detection.

Run with: uv run python prototypes/git_hash_staleness.py

Uses git blob hashes instead of mtimes for reliable staleness detection
across merges, checkouts, and other git operations.
"""
import json
import pathlib
import subprocess
import time
import re
import yaml
from collections import defaultdict


def get_git_hash(file_path: pathlib.Path) -> str | None:
    """Get the git blob hash for a file.

    Returns the hash of the file's current content (staged or working tree),
    or None if git is not available or file is not in a git repo.
    """
    try:
        # git hash-object computes the blob hash for the file's current content
        result = subprocess.run(
            ["git", "hash-object", str(file_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_all_goal_hashes(chunk_dir: pathlib.Path) -> dict[str, str]:
    """Get git hashes for all GOAL.md files efficiently.

    Uses a single git command to hash all files at once.
    """
    chunks = [f for f in chunk_dir.iterdir() if f.is_dir()]
    goal_files = []
    chunk_names = []

    for chunk in chunks:
        goal = chunk / "GOAL.md"
        if goal.exists():
            goal_files.append(str(goal))
            chunk_names.append(chunk.name)

    if not goal_files:
        return {}

    # Hash all files in one git command
    try:
        result = subprocess.run(
            ["git", "hash-object", "--"] + goal_files,
            capture_output=True,
            text=True,
            check=True,
        )
        hashes = result.stdout.strip().split('\n')
        return dict(zip(chunk_names, hashes))
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}


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


def topological_sort_multi_parent(deps: dict[str, list[str]]) -> list[str]:
    """Topological sort with multi-parent support.

    deps: mapping of chunk_name -> list of parent chunk names (created_after)
    Returns: list of chunk names in causal order (oldest first)
    """
    # Build in-degree count and reverse adjacency
    in_degree = defaultdict(int)
    children = defaultdict(list)
    all_nodes = set(deps.keys())

    for chunk, parents in deps.items():
        in_degree[chunk] = len(parents)
        for parent in parents:
            children[parent].append(chunk)
            all_nodes.add(parent)

    # Find roots (nodes with no parents)
    roots = [n for n in all_nodes if in_degree[n] == 0]

    # Kahn's algorithm
    result = []
    queue = sorted(roots)  # Sort for determinism

    while queue:
        node = queue.pop(0)
        if node in deps:  # Only include actual chunks, not missing parents
            result.append(node)
        for child in sorted(children[node]):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    return result


def build_index_with_git_hashes(chunk_dir: pathlib.Path) -> dict:
    """Build index using git hashes for staleness detection."""
    chunks = [f for f in chunk_dir.iterdir() if f.is_dir()]

    # Get all hashes efficiently
    hashes = get_all_goal_hashes(chunk_dir)

    # Load frontmatter
    frontmatters = {}
    for chunk_path in chunks:
        goal = chunk_path / "GOAL.md"
        if goal.exists():
            fm = parse_frontmatter(goal)
            # created_after is an array; default to empty
            created_after = fm.get("created_after", [])
            if created_after is None:
                created_after = []
            elif isinstance(created_after, str):
                # Handle legacy single-value format
                created_after = [created_after]

            frontmatters[chunk_path.name] = {
                "created_after": created_after,
                "status": fm.get("status"),
            }

    # Build dependency graph and sort
    deps = {name: data["created_after"] for name, data in frontmatters.items()}
    ordered = topological_sort_multi_parent(deps)

    # Find tips (chunks that no other chunk depends on)
    all_parents = set()
    for parents in deps.values():
        all_parents.update(parents)
    tips = [name for name in ordered if name not in all_parents]

    return {
        "ordered": ordered,
        "tips": tips,
        "chunk_hashes": hashes,
        "index_version": 2,
    }


def is_index_stale_git(index: dict, chunk_dir: pathlib.Path) -> tuple[bool, str]:
    """Check staleness using git hashes.

    Returns (is_stale, reason).
    """
    current_chunks = {f.name for f in chunk_dir.iterdir() if f.is_dir()}
    indexed_chunks = set(index.get("chunk_hashes", {}).keys())

    # New chunks
    new_chunks = current_chunks - indexed_chunks
    if new_chunks:
        return True, f"new chunks: {new_chunks}"

    # Deleted chunks
    deleted_chunks = indexed_chunks - current_chunks
    if deleted_chunks:
        return True, f"deleted chunks: {deleted_chunks}"

    # Get current hashes
    current_hashes = get_all_goal_hashes(chunk_dir)

    # Check for modified chunks
    for chunk_name, indexed_hash in index.get("chunk_hashes", {}).items():
        current_hash = current_hashes.get(chunk_name)
        if current_hash != indexed_hash:
            return True, f"modified: {chunk_name}"

    return False, "up to date"


def demo_git_hash_approach(chunk_dir: pathlib.Path):
    """Demonstrate git-hash-based caching."""
    index_file = chunk_dir / ".chunk-order.json"

    print("=== Git Hash-Based Staleness Detection ===\n")

    # Build index
    print("Building index...")
    start = time.perf_counter()
    index = build_index_with_git_hashes(chunk_dir)
    build_time = time.perf_counter() - start
    print(f"Build time: {build_time*1000:.2f} ms")
    print(f"Chunks: {len(index['ordered'])}")
    print(f"Tips: {index['tips']}")
    print()

    # Save
    index_file.write_text(json.dumps(index, indent=2))

    # Load and check staleness
    print("Loading index and checking staleness...")
    start = time.perf_counter()
    loaded = json.loads(index_file.read_text())
    load_time = time.perf_counter() - start

    start = time.perf_counter()
    is_stale, reason = is_index_stale_git(loaded, chunk_dir)
    stale_time = time.perf_counter() - start

    print(f"Load time: {load_time*1000:.2f} ms")
    print(f"Staleness check: {stale_time*1000:.2f} ms")
    print(f"Stale: {is_stale} ({reason})")
    print(f"Total warm query: {(load_time + stale_time)*1000:.2f} ms")
    print()

    # Comparison
    print("=== Performance Summary ===")
    print(f"Cold (full rebuild):    {build_time*1000:7.2f} ms")
    print(f"Warm (load + git hash): {(load_time + stale_time)*1000:7.2f} ms")

    # Note: git hash-object is slower than stat() but more reliable
    print()
    print("Note: Git hash check is slower than mtime check but reliable across")
    print("merges, checkouts, and other git operations.")

    # Cleanup
    index_file.unlink()


if __name__ == "__main__":
    chunk_dir = pathlib.Path("docs/chunks")
    demo_git_hash_approach(chunk_dir)
