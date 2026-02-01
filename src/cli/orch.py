"""Orchestrator command group.

Commands for managing the orchestrator daemon and work units.
"""
# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/cli_modularize - Orchestrator CLI commands
# Chunk: docs/chunks/orch_tcp_port - ve orch start with --port and --host options
# Chunk: docs/chunks/orch_url_command - ve orch url command for getting orchestrator endpoint
# Chunk: docs/chunks/orch_attention_reason - Store and display reason for NEEDS_ATTENTION status

import pathlib

import click

from external_refs import strip_artifact_path_prefix
from models import ArtifactType


@click.group()
def orch():
    """Orchestrator daemon commands."""
    pass


@orch.command()
@click.option("--port", type=int, default=0, help="TCP port for dashboard (0 = auto-select)")
@click.option("--host", type=str, default="127.0.0.1", help="Host to bind TCP server to")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def start(port, host, project_dir):
    """Start the orchestrator daemon."""
    from orchestrator.daemon import start_daemon, DaemonError

    try:
        pid, actual_port = start_daemon(project_dir, port=port, host=host)
        click.echo(f"Orchestrator daemon started (PID {pid})")
        click.echo(f"Dashboard available at http://{host}:{actual_port}/")
    except DaemonError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@orch.command()
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def stop(project_dir):
    """Stop the orchestrator daemon."""
    from orchestrator.daemon import stop_daemon, DaemonError

    try:
        stopped = stop_daemon(project_dir)
        if stopped:
            click.echo("Orchestrator daemon stopped")
        else:
            click.echo("Orchestrator daemon is not running")
    except DaemonError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@orch.command("status")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_status(json_output, project_dir):
    """Show orchestrator daemon status."""
    from orchestrator.daemon import get_daemon_status
    import json

    state = get_daemon_status(project_dir)

    if json_output:
        click.echo(json.dumps(state.model_dump_json_serializable(), indent=2))
    else:
        if state.running:
            click.echo(f"Status: Running")
            click.echo(f"PID: {state.pid}")
            if state.uptime_seconds is not None:
                # Format uptime nicely
                uptime = state.uptime_seconds
                if uptime < 60:
                    uptime_str = f"{uptime:.0f}s"
                elif uptime < 3600:
                    uptime_str = f"{uptime / 60:.0f}m"
                else:
                    uptime_str = f"{uptime / 3600:.1f}h"
                click.echo(f"Uptime: {uptime_str}")
            if state.work_unit_counts:
                click.echo("Work Units:")
                for status, count in sorted(state.work_unit_counts.items()):
                    click.echo(f"  {status}: {count}")
        else:
            click.echo("Status: Stopped")


@orch.command("url")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_url(json_output, project_dir):
    """Print the orchestrator dashboard URL."""
    from orchestrator.daemon import is_daemon_running, get_daemon_url
    import json

    # Check if daemon is running
    if not is_daemon_running(project_dir):
        click.echo("Error: Orchestrator is not running.")
        click.echo("Start it with: ve orch start")
        raise SystemExit(1)

    # Get the URL
    url = get_daemon_url(project_dir)
    if url is None:
        click.echo("Error: Could not read daemon port file.")
        click.echo("The daemon may be running but the port file is missing.")
        raise SystemExit(1)

    if json_output:
        click.echo(json.dumps({"url": url}))
    else:
        click.echo(url)


@orch.command("ps")
@click.option("--status", "status_filter", type=str, help="Filter by status")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_ps(status_filter, json_output, project_dir):
    """List all work units (alias for work-unit list)."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client.list_work_units(status=status_filter)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            units = result["work_units"]
            if not units:
                click.echo("No work units")
                return

            # Check if any unit needs attention with a reason
            has_attention_reason = any(
                unit.get("status") == "NEEDS_ATTENTION" and unit.get("attention_reason")
                for unit in units
            )

            # Display table - include REASON column if any NEEDS_ATTENTION units have reasons
            if has_attention_reason:
                click.echo(f"{'CHUNK':<30} {'PHASE':<12} {'STATUS':<16} {'REASON':<32} {'BLOCKED BY'}")
                click.echo("-" * 110)
            else:
                click.echo(f"{'CHUNK':<30} {'PHASE':<12} {'STATUS':<16} {'BLOCKED BY'}")
                click.echo("-" * 80)

            for unit in units:
                blocked = ", ".join(unit["blocked_by"]) if unit["blocked_by"] else "-"
                if has_attention_reason:
                    reason = unit.get("attention_reason") or "-"
                    # Truncate reason to 30 chars
                    if len(reason) > 30:
                        reason = reason[:27] + "..."
                    click.echo(f"{unit['chunk']:<30} {unit['phase']:<12} {unit['status']:<16} {reason:<32} {blocked}")
                else:
                    click.echo(f"{unit['chunk']:<30} {unit['phase']:<12} {unit['status']:<16} {blocked}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.group("work-unit")
def work_unit():
    """Work unit management commands."""
    pass


@work_unit.command("create")
@click.argument("chunk")
@click.option("--phase", default="GOAL", help="Initial phase (GOAL, PLAN, IMPLEMENT, COMPLETE)")
@click.option("--status", "init_status", default="READY", help="Initial status")
@click.option("--blocked-by", multiple=True, help="Chunks this is blocked by")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def work_unit_create(chunk, phase, init_status, blocked_by, json_output, project_dir):
    """Create a new work unit for a chunk."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client.create_work_unit(
            chunk=chunk,
            phase=phase,
            status=init_status,
            blocked_by=list(blocked_by) if blocked_by else None,
        )

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Created work unit: {result['chunk']} [{result['phase']}] {result['status']}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@work_unit.command("status")
@click.argument("chunk")
@click.argument("new_status", required=False, default=None)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def work_unit_status(chunk, new_status, json_output, project_dir):
    """Show or update work unit status."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        if new_status is None:
            # Show current status
            result = client.get_work_unit(chunk)
            if json_output:
                click.echo(json.dumps(result, indent=2))
            else:
                click.echo(f"{result['chunk']}: [{result['phase']}] {result['status']}")
        else:
            # Update status
            old = client.get_work_unit(chunk)
            result = client.update_work_unit(chunk, status=new_status)
            if json_output:
                click.echo(json.dumps(result, indent=2))
            else:
                click.echo(f"{chunk}: {old['status']} -> {result['status']}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@work_unit.command("show")
@click.argument("chunk")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def work_unit_show(chunk, json_output, project_dir):
    """Show detailed work unit information including attention reason."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json as json_module

    client = create_client(project_dir)
    try:
        result = client.get_work_unit(chunk)

        if json_output:
            click.echo(json_module.dumps(result, indent=2))
        else:
            click.echo(f"Chunk:            {result['chunk']}")
            click.echo(f"Phase:            {result['phase']}")
            click.echo(f"Status:           {result['status']}")
            click.echo(f"Priority:         {result['priority']}")
            if result.get('blocked_by'):
                click.echo(f"Blocked By:       {', '.join(result['blocked_by'])}")
            if result.get('worktree'):
                click.echo(f"Worktree:         {result['worktree']}")
            if result.get('session_id'):
                click.echo(f"Session ID:       {result['session_id']}")
            if result.get('attention_reason'):
                click.echo(f"Attention Reason: {result['attention_reason']}")
            click.echo(f"Created At:       {result['created_at']}")
            click.echo(f"Updated At:       {result['updated_at']}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@work_unit.command("list")
@click.option("--status", "status_filter", type=str, help="Filter by status")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def work_unit_list(status_filter, json_output, project_dir):
    """List all work units."""
    # Delegate to orch ps
    from click import Context
    ctx = click.get_current_context()
    ctx.invoke(orch_ps, status_filter=status_filter, json_output=json_output, project_dir=project_dir)


@work_unit.command("delete")
@click.argument("chunk")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def work_unit_delete(chunk, json_output, project_dir):
    """Delete a work unit."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client.delete_work_unit(chunk)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Deleted work unit: {chunk}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


# Chunk: docs/chunks/explicit_deps_batch_inject - Kahn's algorithm for topological sorting of chunks by dependency order
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


# Chunk: docs/chunks/explicit_deps_batch_inject - Read depends_on from chunk GOAL.md frontmatter for dependency graph construction
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


# Chunk: docs/chunks/explicit_deps_batch_inject - Validate that dependencies outside the batch exist as work units
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


@orch.command("inject")
@click.argument("chunks", nargs=-1, required=True)
@click.option("--phase", type=str, default=None, help="Override initial phase (GOAL, PLAN, IMPLEMENT)")
@click.option("--priority", type=int, default=0, help="Scheduling priority (higher = more urgent)")
# Chunk: docs/chunks/orch_worktree_retain - Retain worktrees after completion
@click.option("--retain", is_flag=True, help="Retain worktree after completion for debugging")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_inject(chunks, phase, priority, retain, json_output, project_dir):
    """Inject one or more chunks into the orchestrator work pool.

    Accepts multiple chunk arguments: ve orch inject chunk_a chunk_b chunk_c

    When multiple chunks are provided, they are topologically sorted by their
    depends_on declarations and injected in dependency order (dependencies first).
    Chunks with non-empty depends_on have their work units created with blocked_by
    populated and explicit_deps=True.

    Use --retain to preserve the worktree after completion for debugging.
    Retained worktrees can be cleaned up with `ve orch prune`.
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json as json_module

    # Strip artifact path prefixes from all chunks
    chunk_list = [strip_artifact_path_prefix(c, ArtifactType.CHUNK) for c in chunks]
    batch_chunks = set(chunk_list)

    client = create_client(project_dir)
    try:
        # Read dependencies from all chunks
        if len(chunk_list) > 1 and not json_output:
            click.echo(f"Reading dependencies for {len(chunk_list)} chunks...")

        dependencies = read_chunk_dependencies(project_dir, chunk_list)

        # Validate external dependencies exist as work units
        errors = validate_external_dependencies(client, batch_chunks, dependencies)
        if errors:
            for error in errors:
                click.echo(f"Error: {error}", err=True)
            raise SystemExit(1)

        # Topologically sort chunks
        try:
            sorted_chunks = topological_sort_chunks(chunk_list, dependencies)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

        # Inject in order
        results: list[dict] = []
        for chunk in sorted_chunks:
            deps = dependencies.get(chunk)
            body = {"chunk": chunk, "priority": priority}
            if phase:
                body["phase"] = phase
            # Chunk: docs/chunks/orch_worktree_retain - Retain worktrees after completion
            if retain:
                body["retain_worktree"] = True

            # Set blocked_by and explicit_deps based on depends_on value
            # - None: Dependencies unknown (consult oracle) -> explicit_deps omitted/False
            # - []: Explicitly no dependencies (bypass oracle) -> explicit_deps=True
            # - ["chunk_a", ...]: Explicit dependencies -> explicit_deps=True, blocked_by set
            if deps is not None:
                # deps is a list (empty or non-empty) - explicit declaration
                body["explicit_deps"] = True
                if deps:
                    body["blocked_by"] = deps
            # else: deps is None - unknown, oracle will be consulted (no explicit_deps)

            result = client._request("POST", "/work-units/inject", json=body)
            results.append(result)

            if not json_output:
                blocked_info = ""
                if deps:
                    blocked_info = f" blocked_by={deps}"
                priority_info = f" priority={result.get('priority', priority)}"
                retain_info = " retain=True" if retain else ""
                click.echo(
                    f"Injected: {result['chunk']} [{result['phase']}]{priority_info}{blocked_info}{retain_info}"
                )

        # Final output
        if json_output:
            click.echo(json_module.dumps({"results": results}, indent=2))
        elif len(chunk_list) > 1:
            click.echo(f"Injected {len(results)} chunks in dependency order")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("queue")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_queue(json_output, project_dir):
    """Show ready queue ordered by priority."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client._request("GET", "/work-units/queue")

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            units = result["work_units"]
            if not units:
                click.echo("Ready queue is empty")
                return

            # Display table
            click.echo(f"{'CHUNK':<30} {'PHASE':<12} {'PRIORITY':<10}")
            click.echo("-" * 52)
            for unit in units:
                click.echo(f"{unit['chunk']:<30} {unit['phase']:<12} {unit['priority']:<10}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("prioritize")
@click.argument("chunk")
@click.argument("priority", type=int)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_prioritize(chunk, priority, json_output, project_dir):
    """Set priority for a work unit."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client._request(
            "PATCH",
            f"/work-units/{chunk}/priority",
            json={"priority": priority},
        )

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"{chunk}: priority set to {result['priority']}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("config")
@click.option("--max-agents", type=int, help="Maximum concurrent agents")
@click.option("--dispatch-interval", type=float, help="Dispatch interval in seconds")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_config(max_agents, dispatch_interval, json_output, project_dir):
    """Get or set orchestrator configuration.

    If no options are provided, shows current configuration.
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        if max_agents is None and dispatch_interval is None:
            # Get config
            result = client._request("GET", "/config")
        else:
            # Update config
            body = {}
            if max_agents is not None:
                body["max_agents"] = max_agents
            if dispatch_interval is not None:
                body["dispatch_interval_seconds"] = dispatch_interval

            result = client._request("PATCH", "/config", json=body)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo("Orchestrator Configuration:")
            click.echo(f"  max_agents: {result['max_agents']}")
            click.echo(f"  dispatch_interval_seconds: {result['dispatch_interval_seconds']}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("attention")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_attention(json_output, project_dir):
    """Show attention queue of work units needing operator input.

    Lists NEEDS_ATTENTION work units in priority order:
    - Higher blocked count = higher priority (unblocks more work)
    - Older items surface first among equal priority
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client.get_attention_queue()

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            items = result["attention_items"]
            if not items:
                click.echo("No work units need attention")
                return

            click.echo(f"ATTENTION QUEUE ({len(items)} items)")
            click.echo("─" * 60)

            for i, item in enumerate(items, 1):
                chunk = item["chunk"]
                phase = item["phase"]
                blocks = item["blocks_count"]

                # Format time waiting
                time_waiting = item["time_waiting"]
                if time_waiting < 60:
                    time_str = f"{time_waiting:.0f}s"
                elif time_waiting < 3600:
                    time_str = f"{time_waiting / 60:.0f}m"
                else:
                    time_str = f"{time_waiting / 3600:.1f}h"

                click.echo(f"[{i}] {chunk}  {phase}  blocks:{blocks}  waiting:{time_str}")

                # Show attention reason
                reason = item.get("attention_reason")
                if reason:
                    # Truncate long reasons for display
                    if len(reason) > 70:
                        reason = reason[:67] + "..."
                    click.echo(f"    {reason}")

                # Show goal summary if available
                goal_summary = item.get("goal_summary")
                if goal_summary:
                    # Truncate for display
                    if len(goal_summary) > 70:
                        goal_summary = goal_summary[:67] + "..."
                    click.echo(f"    Goal: {goal_summary}")

                click.echo("")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("answer")
@click.argument("chunk")
@click.argument("answer")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_answer(chunk, answer, json_output, project_dir):
    """Answer a question from a NEEDS_ATTENTION work unit.

    Submits the answer and transitions the work unit to READY,
    allowing the scheduler to resume the agent with the answer injected.
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client.answer_work_unit(chunk, answer)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Answered {chunk}, work unit queued for resume")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()




@orch.command("conflicts")
@click.argument("chunk", required=False)
@click.option("--unresolved", is_flag=True, help="Show only ASK_OPERATOR verdicts")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_conflicts(chunk, unresolved, json_output, project_dir):
    """Show conflict analyses for chunks.

    If CHUNK is provided, shows conflicts for that specific chunk.
    Otherwise, shows all conflicts.

    Use --unresolved to filter to only ASK_OPERATOR verdicts that need resolution.
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        if chunk:
            result = client.get_conflicts(chunk)
            conflicts = result.get("conflicts", [])
        else:
            verdict_filter = "ASK_OPERATOR" if unresolved else None
            result = client.list_all_conflicts(verdict=verdict_filter)
            conflicts = result.get("conflicts", [])

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            if not conflicts:
                if unresolved:
                    click.echo("No unresolved conflicts")
                elif chunk:
                    click.echo(f"No conflicts for {chunk}")
                else:
                    click.echo("No conflicts found")
                return

            # Display conflicts
            click.echo(f"{'CHUNK A':<25} {'CHUNK B':<25} {'VERDICT':<15} {'CONFIDENCE':<12} {'STAGE'}")
            click.echo("-" * 90)

            for c in conflicts:
                chunk_a = c["chunk_a"]
                chunk_b = c["chunk_b"]
                verdict = c["verdict"]
                confidence = f"{c['confidence']:.2f}"
                stage = c["analysis_stage"]

                click.echo(f"{chunk_a:<25} {chunk_b:<25} {verdict:<15} {confidence:<12} {stage}")

                # Show overlapping files/symbols if present
                if c.get("overlapping_files"):
                    files = ", ".join(c["overlapping_files"][:3])
                    click.echo(f"  Files: {files}")
                if c.get("overlapping_symbols"):
                    symbols = ", ".join(c["overlapping_symbols"][:3])
                    click.echo(f"  Symbols: {symbols}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("resolve")
@click.argument("chunk")
@click.option("--with", "other_chunk", required=True, help="The other chunk in the conflict")
@click.argument("verdict", type=click.Choice(["parallelize", "serialize"]))
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_resolve(chunk, other_chunk, verdict, json_output, project_dir):
    """Resolve an ASK_OPERATOR conflict between two chunks.

    CHUNK is the work unit to update.
    VERDICT is either 'parallelize' (chunks can run together) or 'serialize' (must run sequentially).

    Example:
        ve orch resolve my_chunk --with other_chunk serialize
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    # Normalize chunk path
    chunk = strip_artifact_path_prefix(chunk, ArtifactType.CHUNK)
    other_chunk = strip_artifact_path_prefix(other_chunk, ArtifactType.CHUNK)

    client = create_client(project_dir)
    try:
        result = client.resolve_conflict(chunk, other_chunk, verdict)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            resolved_verdict = result.get("verdict", verdict)
            click.echo(f"Resolved: {chunk} vs {other_chunk} -> {resolved_verdict}")
            if result.get("blocked_by"):
                click.echo(f"  Blocked by: {', '.join(result['blocked_by'])}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("analyze")
@click.argument("chunk_a")
@click.argument("chunk_b")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_analyze(chunk_a, chunk_b, json_output, project_dir):
    """Analyze potential conflict between two chunks.

    Triggers the conflict oracle to analyze whether CHUNK_A and CHUNK_B
    can be safely parallelized or require serialization.
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    # Normalize chunk paths
    chunk_a = strip_artifact_path_prefix(chunk_a, ArtifactType.CHUNK)
    chunk_b = strip_artifact_path_prefix(chunk_b, ArtifactType.CHUNK)

    client = create_client(project_dir)
    try:
        result = client.analyze_conflicts(chunk_a, chunk_b)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            verdict = result.get("verdict", "UNKNOWN")
            confidence = result.get("confidence", 0)
            reason = result.get("reason", "")
            stage = result.get("analysis_stage", "UNKNOWN")

            click.echo(f"Conflict Analysis: {chunk_a} vs {chunk_b}")
            click.echo(f"  Verdict:    {verdict}")
            click.echo(f"  Confidence: {confidence:.2f}")
            click.echo(f"  Stage:      {stage}")
            click.echo(f"  Reason:     {reason}")

            if result.get("overlapping_files"):
                click.echo(f"  Files:      {', '.join(result['overlapping_files'])}")
            if result.get("overlapping_symbols"):
                click.echo(f"  Symbols:    {', '.join(result['overlapping_symbols'])}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("tail")
@click.argument("chunk")
@click.option("-f", "--follow", is_flag=True, help="Follow log output in real-time")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_tail(chunk, follow, project_dir):
    """Stream log output for an orchestrator work unit.

    Displays parsed, human-readable log output for CHUNK. Shows tool calls,
    tool results, and assistant messages in a condensed format.

    Use -f to follow the log in real-time as the agent works.
    """
    import time
    from orchestrator.log_parser import (
        parse_log_file,
        format_entry,
        format_phase_header,
    )
    from orchestrator.models import WorkUnitPhase

    # Normalize chunk path
    chunk = strip_artifact_path_prefix(chunk, ArtifactType.CHUNK)

    # Get log directory - compute directly without WorktreeManager to avoid git requirement
    log_dir = project_dir / ".ve" / "chunks" / chunk / "log"

    # Check if chunk directory exists
    chunk_dir = project_dir / "docs" / "chunks" / chunk
    if not chunk_dir.exists():
        click.echo(f"Error: Chunk '{chunk}' not found", err=True)
        raise SystemExit(1)

    # Check if log directory exists
    if not log_dir.exists():
        click.echo(f"No logs yet for chunk '{chunk}'. The work unit may not have started.", err=True)
        raise SystemExit(1)

    # Phase order for iteration
    phase_order = [
        WorkUnitPhase.GOAL,
        WorkUnitPhase.PLAN,
        WorkUnitPhase.IMPLEMENT,
        WorkUnitPhase.REVIEW,
        WorkUnitPhase.COMPLETE,
    ]

    def get_phase_log_files() -> list[tuple[WorkUnitPhase, pathlib.Path]]:
        """Get list of existing phase log files in order."""
        result = []
        for phase in phase_order:
            log_file = log_dir / f"{phase.value.lower()}.txt"
            if log_file.exists():
                result.append((phase, log_file))
        return result

    def display_phase_log(phase: WorkUnitPhase, log_file: pathlib.Path, show_header: bool = True):
        """Display a phase log file."""
        entries = parse_log_file(log_file)
        if not entries:
            return

        # Show phase header
        if show_header and entries:
            header = format_phase_header(phase.value, entries[0].timestamp)
            click.echo(f"\n{header}\n")

        # Display entries
        for entry in entries:
            lines = format_entry(entry)
            for line in lines:
                click.echo(line)

    # Basic mode: display all existing logs
    phase_logs = get_phase_log_files()

    if not phase_logs:
        click.echo(f"No logs yet for chunk '{chunk}'. The work unit may not have started.", err=True)
        raise SystemExit(1)

    # Display existing phase logs
    for phase, log_file in phase_logs:
        display_phase_log(phase, log_file)

    if not follow:
        return

    # Follow mode: stream new lines
    try:
        current_phase_idx = len(phase_logs) - 1
        current_phase, current_log = phase_logs[current_phase_idx]

        # Track file position
        with open(current_log) as f:
            f.seek(0, 2)  # Seek to end
            file_pos = f.tell()

        while True:
            time.sleep(0.1)  # 100ms polling interval

            # Check for new content in current log
            try:
                with open(current_log) as f:
                    f.seek(file_pos)
                    new_content = f.read()
                    if new_content:
                        file_pos = f.tell()
                        # Parse and display new lines
                        for line in new_content.strip().split("\n"):
                            if line.strip():
                                from orchestrator.log_parser import parse_log_line
                                entry = parse_log_line(line)
                                if entry:
                                    lines = format_entry(entry)
                                    for display_line in lines:
                                        click.echo(display_line)
            except FileNotFoundError:
                pass

            # Check for next phase log file
            next_phase_idx = current_phase_idx + 1
            if next_phase_idx < len(phase_order):
                next_phase = phase_order[next_phase_idx]
                next_log = log_dir / f"{next_phase.value.lower()}.txt"
                if next_log.exists():
                    # New phase started
                    current_phase_idx = next_phase_idx
                    current_phase = next_phase
                    current_log = next_log

                    # Show phase header
                    entries = parse_log_file(next_log)
                    if entries:
                        header = format_phase_header(next_phase.value, entries[0].timestamp)
                        click.echo(f"\n{header}\n")

                    # Display any content already in the file
                    for entry in entries:
                        lines = format_entry(entry)
                        for line in lines:
                            click.echo(line)

                    # Update file position
                    with open(current_log) as f:
                        f.seek(0, 2)
                        file_pos = f.tell()

    except KeyboardInterrupt:
        click.echo("\n")  # Clean exit on Ctrl+C


# Chunk: docs/chunks/orch_worktree_retain - Worktree management subgroup
@orch.group("worktree")
def worktree():
    """Worktree management commands.

    Commands for listing, inspecting, and cleaning up retained worktrees.
    Worktrees created with --retain are preserved after completion for
    debugging and inspection. Use these commands to manage them.
    """
    pass


@worktree.command("list")
@click.option("--status", "status_filter", default=None, help="Filter by status (active, completed, retained, orphaned)")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def worktree_list(status_filter, json_output, project_dir):
    """List all worktrees with their status.

    Shows worktrees with their current status:
    - active: Agent is currently running in this worktree
    - retained: Work unit completed with --retain flag, worktree preserved
    - orphaned: No active work unit, worktree exists (may contain uncommitted work)
    - completed: Work unit done, worktree still exists (will be cleaned up)

    Examples:
        ve orch worktree list               # List all worktrees
        ve orch worktree list --status retained  # Only show retained worktrees
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json as json_module

    client = create_client(project_dir)
    try:
        result = client._request("GET", "/worktrees")
        worktrees = result.get("worktrees", [])

        # Filter by status if requested
        if status_filter:
            worktrees = [w for w in worktrees if w.get("status") == status_filter]

        if json_output:
            click.echo(json_module.dumps({"worktrees": worktrees, "count": len(worktrees)}, indent=2))
        else:
            if not worktrees:
                click.echo("No worktrees found")
                return

            click.echo(f"{'CHUNK':<30} {'STATUS':<12} {'PATH'}")
            click.echo("-" * 80)
            for w in worktrees:
                chunk = w.get("chunk", "?")
                status = w.get("status", "?")
                path = w.get("path", "?")
                click.echo(f"{chunk:<30} {status:<12} {path}")

            click.echo(f"\nTotal: {len(worktrees)} worktree(s)")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@worktree.command("remove")
@click.argument("chunk")
@click.option("--keep-branch", is_flag=True, help="Keep the git branch after removing worktree")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def worktree_remove(chunk, keep_branch, json_output, project_dir):
    """Remove a worktree without merging.

    Removes the worktree directory and optionally the branch.
    WARNING: This does NOT merge changes back to base. Any uncommitted
    or unmerged changes will be lost.

    Use 've orch prune' instead if you want to merge changes before cleanup.

    Examples:
        ve orch worktree remove my_chunk         # Remove worktree and branch
        ve orch worktree remove my_chunk --keep-branch  # Keep the branch
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json as json_module

    # Normalize chunk path
    chunk = strip_artifact_path_prefix(chunk, ArtifactType.CHUNK)

    client = create_client(project_dir)
    try:
        params = {"remove_branch": "false" if keep_branch else "true"}
        result = client._request("DELETE", f"/worktrees/{chunk}", params=params)

        if json_output:
            click.echo(json_module.dumps(result, indent=2))
        else:
            status = result.get("status", "unknown")
            if status == "removed":
                branch_msg = " (branch kept)" if keep_branch else " (branch removed)"
                click.echo(f"Removed worktree for {chunk}{branch_msg}")
            elif status == "error":
                click.echo(f"Error removing worktree: {result.get('error', 'unknown')}", err=True)
                raise SystemExit(1)
            else:
                click.echo(f"Unexpected status: {status}", err=True)
                raise SystemExit(1)

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@worktree.command("prune")
@click.option("--dry-run", is_flag=True, help="Show what would be pruned without doing it")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def worktree_prune(dry_run, json_output, project_dir):
    """Prune all retained worktrees.

    Finds all DONE work units with retain_worktree=True and prunes them,
    merging changes back to base and cleaning up the worktrees and branches.

    This is equivalent to 've orch prune --all'.

    Examples:
        ve orch worktree prune            # Prune all retained worktrees
        ve orch worktree prune --dry-run  # Show what would be pruned
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json as json_module

    client = create_client(project_dir)
    try:
        result = client._request(
            "POST",
            "/work-units/prune",
            json={"dry_run": dry_run},
        )
        results = result.get("results", [])

        if json_output:
            click.echo(json_module.dumps({"results": results}, indent=2))
        else:
            if dry_run:
                click.echo("Dry run - would prune:")
            else:
                click.echo("Pruned:")

            if not results:
                click.echo("  (none)")
            else:
                for r in results:
                    status = r.get("status", "unknown")
                    chunk_name = r.get("chunk", "unknown")
                    if status == "pruned" or status == "would_prune":
                        click.echo(f"  {chunk_name}: merged and cleaned up")
                    elif status == "skipped":
                        click.echo(f"  {chunk_name}: skipped - {r.get('reason', 'unknown')}")
                    elif status == "error":
                        click.echo(f"  {chunk_name}: error - {r.get('error', 'unknown')}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


# Chunk: docs/chunks/orch_worktree_retain - Retain worktrees after completion
@orch.command("prune")
@click.argument("chunk", required=False)
@click.option("--all", "prune_all", is_flag=True, help="Prune all retained worktrees")
@click.option("--dry-run", is_flag=True, help="Show what would be pruned without doing it")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_prune(chunk, prune_all, dry_run, json_output, project_dir):
    """Clean up retained worktrees from completed work units.

    Retained worktrees (created with --retain flag) are not automatically cleaned
    up on completion. Use this command to merge and remove them.

    When a chunk is specified, only that chunk's worktree is pruned.
    Use --all to prune all retained worktrees from DONE work units.

    The prune operation will:
    1. Merge any uncommitted changes
    2. Merge the branch back to base
    3. Remove the worktree and branch
    4. Clear the retain_worktree flag

    Examples:
        ve orch prune my_chunk        # Prune specific chunk
        ve orch prune --all           # Prune all retained worktrees
        ve orch prune --all --dry-run # Show what would be pruned
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json as json_module

    if not chunk and not prune_all:
        click.echo("Error: Specify a chunk or use --all to prune all retained worktrees", err=True)
        raise SystemExit(1)

    # Normalize chunk path if provided
    if chunk:
        chunk = strip_artifact_path_prefix(chunk, ArtifactType.CHUNK)

    client = create_client(project_dir)
    try:
        if chunk:
            # Prune single chunk
            result = client._request(
                "POST",
                f"/work-units/{chunk}/prune",
                json={"dry_run": dry_run},
            )
            results = [result]
        else:
            # Prune all retained worktrees
            result = client._request(
                "POST",
                "/work-units/prune",
                json={"dry_run": dry_run},
            )
            results = result.get("results", [])

        if json_output:
            click.echo(json_module.dumps({"results": results}, indent=2))
        else:
            if dry_run:
                click.echo("Dry run - would prune:")
            else:
                click.echo("Pruned:")

            if not results:
                click.echo("  (none)")
            else:
                for r in results:
                    status = r.get("status", "unknown")
                    chunk_name = r.get("chunk", "unknown")
                    if status == "pruned" or status == "would_prune":
                        click.echo(f"  {chunk_name}: merged and cleaned up")
                    elif status == "skipped":
                        click.echo(f"  {chunk_name}: skipped - {r.get('reason', 'unknown')}")
                    elif status == "error":
                        click.echo(f"  {chunk_name}: error - {r.get('error', 'unknown')}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()
