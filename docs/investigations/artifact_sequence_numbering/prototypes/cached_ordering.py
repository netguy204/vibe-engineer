"""Prototype cached/indexed ordering approach.

The idea: Store the sorted chunk order in a lightweight index file.
Rebuild only when the chunk set changes (detected via mtime or git).

Run with: uv run python prototypes/cached_ordering.py

This prototype explores:
1. Index file format (.chunk-order.json)
2. Staleness detection (comparing chunk mtimes vs index mtime)
3. Query performance from index vs full rebuild
"""
import json
import pathlib
import re
import time
import yaml
from collections import defaultdict


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


def topological_sort(deps: dict[str, str | None]) -> list[str]:
    """Topological sort based on created_after dependencies."""
    children = defaultdict(list)
    roots = []
    for chunk, parent in deps.items():
        if parent is None:
            roots.append(chunk)
        else:
            children[parent].append(chunk)

    result = []
    queue = sorted(roots)  # Sort roots for determinism
    while queue:
        node = queue.pop(0)
        result.append(node)
        queue.extend(sorted(children[node]))

    return result


def build_index(chunk_dir: pathlib.Path) -> dict:
    """Build the full index by reading all frontmatter."""
    chunks = [f for f in chunk_dir.iterdir() if f.is_dir()]

    # Load all frontmatter
    frontmatters = {}
    for chunk_path in chunks:
        goal = chunk_path / "GOAL.md"
        if goal.exists():
            fm = parse_frontmatter(goal)
            frontmatters[chunk_path.name] = {
                "created_after": fm.get("created_after"),
                "status": fm.get("status"),
                "mtime": goal.stat().st_mtime,
            }

    # Build dependency graph and sort
    deps = {name: data["created_after"] for name, data in frontmatters.items()}
    ordered = topological_sort(deps)

    # Find tips (chunks with no dependents)
    has_dependents = set(deps.values())
    tips = [name for name in ordered if name not in has_dependents]

    return {
        "ordered": ordered,
        "tips": tips,
        "chunk_mtimes": {name: data["mtime"] for name, data in frontmatters.items()},
        "index_version": 1,
    }


def is_index_stale(index: dict, chunk_dir: pathlib.Path) -> bool:
    """Check if index is stale by comparing chunk set and mtimes."""
    current_chunks = {f.name for f in chunk_dir.iterdir() if f.is_dir()}
    indexed_chunks = set(index.get("chunk_mtimes", {}).keys())

    # New or deleted chunks
    if current_chunks != indexed_chunks:
        return True

    # Check mtimes for modified chunks
    for chunk_name, indexed_mtime in index.get("chunk_mtimes", {}).items():
        goal = chunk_dir / chunk_name / "GOAL.md"
        if goal.exists():
            if goal.stat().st_mtime > indexed_mtime:
                return True

    return False


def demo_cached_ordering(chunk_dir: pathlib.Path):
    """Demonstrate cached ordering approach."""
    index_file = chunk_dir / ".chunk-order.json"

    # Scenario 1: Cold start (no index)
    print("=== Scenario 1: Cold start (build index) ===")
    start = time.perf_counter()
    index = build_index(chunk_dir)
    build_time = time.perf_counter() - start
    print(f"Build time: {build_time*1000:.2f} ms")
    print(f"Chunks: {len(index['ordered'])}")
    print(f"Tips: {index['tips']}")

    # Save index
    index_file.write_text(json.dumps(index, indent=2))
    print(f"Index saved to: {index_file}")
    print()

    # Scenario 2: Warm start (load from index)
    print("=== Scenario 2: Warm start (load index) ===")
    start = time.perf_counter()
    loaded_index = json.loads(index_file.read_text())
    load_time = time.perf_counter() - start
    print(f"Load time: {load_time*1000:.2f} ms")

    # Check staleness
    start = time.perf_counter()
    stale = is_index_stale(loaded_index, chunk_dir)
    stale_check_time = time.perf_counter() - start
    print(f"Staleness check: {stale_check_time*1000:.2f} ms (stale={stale})")
    print(f"Total warm query: {(load_time + stale_check_time)*1000:.2f} ms")
    print()

    # Compare
    print("=== Performance comparison ===")
    print(f"Cold (rebuild):     {build_time*1000:7.2f} ms")
    print(f"Warm (index+check): {(load_time + stale_check_time)*1000:7.2f} ms")
    speedup = build_time / (load_time + stale_check_time)
    print(f"Speedup: {speedup:.1f}x")
    print()

    # Extrapolate
    print("=== Extrapolated warm query times ===")
    per_chunk_stale_check = stale_check_time / len(index['ordered'])
    for n in [100, 500, 1000]:
        estimated = load_time + (per_chunk_stale_check * n)
        print(f"{n:4d} chunks: {estimated*1000:.2f} ms")

    # Cleanup
    index_file.unlink()


if __name__ == "__main__":
    chunk_dir = pathlib.Path("docs/chunks")
    demo_cached_ordering(chunk_dir)
