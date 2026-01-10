"""Prototype frontmatter-based causal ordering to measure performance.

Run with: uv run python prototypes/frontmatter_ordering.py

Results from real chunks (36 chunks):
- Enumerate dirs:      0.35 ms
- Load frontmatter:   32.48 ms  (~0.9ms per chunk)
- Build deps:          0.01 ms
- Topological sort:    0.01 ms
- TOTAL:              32.85 ms

Extrapolated:
- 100 chunks:  ~91ms
- 500 chunks: ~452ms
- 1000 chunks: ~903ms
"""
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
    """Topological sort of chunks based on created_after dependencies.

    deps: mapping of chunk_name -> created_after (parent chunk name or None)
    Returns: list of chunk names in causal order (oldest first)
    """
    # Build reverse adjacency (parent -> children)
    children = defaultdict(list)
    roots = []
    for chunk, parent in deps.items():
        if parent is None:
            roots.append(chunk)
        else:
            children[parent].append(chunk)

    # BFS from roots
    result = []
    queue = list(roots)
    while queue:
        node = queue.pop(0)
        result.append(node)
        for child in children[node]:
            queue.append(child)

    return result


def measure_frontmatter_ordering(chunk_dir: pathlib.Path):
    """Measure time to load all frontmatter and build causal order."""

    # Phase 1: Enumerate directories
    start = time.perf_counter()
    chunks = [f for f in chunk_dir.iterdir() if f.is_dir()]
    enum_time = time.perf_counter() - start

    # Phase 2: Load all frontmatter
    start = time.perf_counter()
    frontmatters = {}
    for chunk_path in chunks:
        goal = chunk_path / "GOAL.md"
        if goal.exists():
            frontmatters[chunk_path.name] = parse_frontmatter(goal)
    load_time = time.perf_counter() - start

    # Phase 3: Build dependency graph (simulated - using sequence order as proxy)
    # In real implementation, we'd use created_after field
    start = time.perf_counter()
    deps = {}
    sorted_names = sorted(frontmatters.keys())
    for i, name in enumerate(sorted_names):
        if i == 0:
            deps[name] = None
        else:
            deps[name] = sorted_names[i-1]
    sort_time = time.perf_counter() - start

    # Phase 4: Topological sort
    start = time.perf_counter()
    ordered = topological_sort(deps)
    topo_time = time.perf_counter() - start

    total = enum_time + load_time + sort_time + topo_time

    print(f"Chunks: {len(chunks)}")
    print(f"Enumerate dirs:     {enum_time*1000:7.2f} ms")
    print(f"Load frontmatter:   {load_time*1000:7.2f} ms")
    print(f"Build deps:         {sort_time*1000:7.2f} ms")
    print(f"Topological sort:   {topo_time*1000:7.2f} ms")
    print(f"TOTAL:              {total*1000:7.2f} ms")
    print()

    # Per-chunk cost
    if chunks:
        print(f"Per-chunk cost:     {(load_time/len(chunks))*1000:7.2f} ms")
        print()

    # Extrapolate to larger sizes
    per_chunk_load = load_time / len(chunks) if chunks else 0.01
    for n in [100, 500, 1000]:
        estimated = enum_time + (per_chunk_load * n) + sort_time + topo_time
        print(f"Estimated for {n:4d} chunks: {estimated*1000:7.2f} ms")


if __name__ == "__main__":
    chunk_dir = pathlib.Path("docs/chunks")
    measure_frontmatter_ordering(chunk_dir)
