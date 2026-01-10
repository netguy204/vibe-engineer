"""Test frontmatter parsing at scale with simulated files.

Run with: uv run python prototypes/scaling_test.py

Results (simulated minimal frontmatter):
   50 chunks: enum=   0.1ms, load=    6.5ms, TOTAL=    6.5ms
  100 chunks: enum=   0.1ms, load=   13.2ms, TOTAL=   13.3ms
  250 chunks: enum=   0.3ms, load=   32.4ms, TOTAL=   32.7ms
  500 chunks: enum=   0.5ms, load=   64.5ms, TOTAL=   65.0ms
  750 chunks: enum=   0.9ms, load=   99.3ms, TOTAL=  100.2ms
 1000 chunks: enum=   1.1ms, load=  132.6ms, TOTAL=  133.7ms

Note: ~0.13ms per chunk with minimal frontmatter vs ~0.9ms per chunk
with real data. Real GOAL.md files have more content to parse.
"""
import pathlib
import tempfile
import time
import re
import yaml

FRONTMATTER_TEMPLATE = """---
status: ACTIVE
created_after: {created_after}
code_references:
  - ref: src/module_{n}.py#SomeClass
---

# Chunk {n}

This is a simulated chunk for performance testing.
"""


def create_test_chunks(base_dir: pathlib.Path, count: int):
    """Create simulated chunk directories with frontmatter."""
    for i in range(count):
        chunk_dir = base_dir / f"{i:04d}-test_chunk_{i}"
        chunk_dir.mkdir(parents=True)

        created_after = f"{i-1:04d}-test_chunk_{i-1}" if i > 0 else "null"
        content = FRONTMATTER_TEMPLATE.format(n=i, created_after=created_after)
        (chunk_dir / "GOAL.md").write_text(content)


def parse_frontmatter(goal_path: pathlib.Path) -> dict:
    content = goal_path.read_text()
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def measure_at_scale(count: int):
    """Measure frontmatter loading time at a given scale."""
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp) / "chunks"
        base.mkdir()

        # Create chunks
        create_test_chunks(base, count)

        # Measure loading
        start = time.perf_counter()
        chunks = list(base.iterdir())
        enum_time = time.perf_counter() - start

        start = time.perf_counter()
        for chunk in chunks:
            goal = chunk / "GOAL.md"
            if goal.exists():
                fm = parse_frontmatter(goal)
        load_time = time.perf_counter() - start

        total = enum_time + load_time
        print(f"{count:5d} chunks: enum={enum_time*1000:6.1f}ms, load={load_time*1000:7.1f}ms, TOTAL={total*1000:7.1f}ms")


if __name__ == "__main__":
    print("Testing frontmatter loading at scale...")
    print()
    for n in [50, 100, 250, 500, 750, 1000]:
        measure_at_scale(n)
