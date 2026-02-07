# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_cli_extract - Extracted dependency resolution functions from CLI layer
# Chunk: docs/chunks/explicit_deps_batch_inject - Original implementation of dependency resolution
"""Dependency resolution functions for orchestrator work unit scheduling.

This module provides pure computation functions for resolving chunk dependencies:
- Topological sorting of chunks by dependency order
- Reading depends_on declarations from chunk frontmatter
- Validating external dependencies exist as work units

These functions are used by the CLI layer and could be used by other components
that need dependency resolution without importing CLI code.
"""

import pathlib


def topological_sort_chunks(
    chunks: list[str],
    dependencies: dict[str, list[str] | None],
) -> list[str]:
    """Sort chunks by dependency order (dependencies first).

    Uses Kahn's algorithm for topological sorting.

    Args:
        chunks: List of chunk names to sort
        dependencies: Maps chunk name -> list of chunk names it depends on (or None if unknown)

    Returns:
        Chunks in topological order (dependencies before dependents)

    Raises:
        ValueError: If a dependency cycle is detected
    """
    # Build in-degree map (count of dependencies within the batch for each chunk)
    in_degree: dict[str, int] = {chunk: 0 for chunk in chunks}
    batch_set = set(chunks)

    # Only count dependencies that are in the batch (treat None as empty list for sorting)
    for chunk in chunks:
        deps = dependencies.get(chunk) or []
        for dep in deps:
            if dep in batch_set:
                in_degree[chunk] += 1

    # Start with chunks that have no in-batch dependencies
    queue = [chunk for chunk in chunks if in_degree[chunk] == 0]
    result: list[str] = []

    while queue:
        # Sort for deterministic ordering
        queue.sort()
        current = queue.pop(0)
        result.append(current)

        # Reduce in-degree for chunks that depend on current
        for chunk in chunks:
            deps = dependencies.get(chunk) or []
            if current in deps:
                in_degree[chunk] -= 1
                if in_degree[chunk] == 0:
                    queue.append(chunk)

    # If we haven't processed all chunks, there's a cycle
    if len(result) != len(chunks):
        # Find the cycle for error message
        remaining = [c for c in chunks if c not in result]
        # Build a simple cycle representation
        cycle_parts = []
        visited = set()
        current = remaining[0]
        while current not in visited:
            visited.add(current)
            cycle_parts.append(current)
            # Find next node in cycle
            deps = dependencies.get(current) or []
            for dep in deps:
                if dep in remaining:
                    current = dep
                    break
        cycle_parts.append(current)  # Complete the cycle
        cycle_str = " -> ".join(cycle_parts)
        raise ValueError(f"Dependency cycle detected: {cycle_str}")

    return result


def read_chunk_dependencies(project_dir: pathlib.Path, chunk_names: list[str]) -> dict[str, list[str] | None]:
    """Read depends_on from chunk frontmatter for all specified chunks.

    Args:
        project_dir: Project directory
        chunk_names: List of chunk names to read

    Returns:
        Dict mapping chunk name -> list of depends_on chunk names, or None if unknown.

        The distinction between None and [] is semantically significant:
        - None: Dependencies unknown (consult oracle)
        - []: Explicitly no dependencies (bypass oracle)
        - ["chunk_a", ...]: Explicit dependencies (bypass oracle)
    """
    from chunks import Chunks

    chunks_manager = Chunks(project_dir)
    dependencies: dict[str, list[str] | None] = {}

    for chunk_name in chunk_names:
        frontmatter = chunks_manager.parse_chunk_frontmatter(chunk_name)
        if frontmatter is not None:
            # Preserve None vs [] distinction from frontmatter
            dependencies[chunk_name] = frontmatter.depends_on
        else:
            # No frontmatter means unknown dependencies
            dependencies[chunk_name] = None

    return dependencies


def validate_external_dependencies(
    client,
    batch_chunks: set[str],
    dependencies: dict[str, list[str] | None],
) -> list[str]:
    """Validate that dependencies outside the batch exist as work units.

    Args:
        client: Orchestrator client for querying existing work units
        batch_chunks: Set of chunk names in the current batch
        dependencies: Maps chunk name -> list of depends_on chunk names (or None if unknown)

    Returns:
        List of error messages (empty if all external deps exist)
    """
    # Collect all external dependencies (skip None values - those have unknown deps)
    external_deps: set[str] = set()
    for chunk, deps in dependencies.items():
        if deps is not None:
            for dep in deps:
                if dep not in batch_chunks:
                    external_deps.add(dep)

    if not external_deps:
        return []

    # Query existing work units
    try:
        result = client._request("GET", "/work-units")
        existing_chunks = {wu["chunk"] for wu in result.get("work_units", [])}
    except Exception:
        existing_chunks = set()

    # Check which external deps are missing
    errors: list[str] = []
    for dep in external_deps:
        if dep not in existing_chunks:
            # Find which chunk(s) depend on this missing dep (skip None values)
            dependents = [c for c, d in dependencies.items() if d is not None and dep in d]
            for dependent in dependents:
                errors.append(
                    f"Chunk '{dependent}' depends on '{dep}' which is not in this batch "
                    "and not an existing work unit"
                )

    return errors
