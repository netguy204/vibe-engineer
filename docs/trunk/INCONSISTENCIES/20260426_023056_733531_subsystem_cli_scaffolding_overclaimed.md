---
discovered_by: audit batch 10g
discovered_at: 2026-04-26T02:30:56Z
severity: high
status: open
artifacts:
  - docs/chunks/subsystem_cli_scaffolding/GOAL.md
---

# Claim

`docs/chunks/subsystem_cli_scaffolding/GOAL.md` makes several success-criteria claims about the subsystem CLI:

- SC #1: "Running `ve subsystem discover validation` creates `docs/subsystems/0001-validation/OVERVIEW.md`"
- SC #2: "Sequential numbering: The `discover` command correctly increments the sequence number (e.g., if `0001-*` exists, the next subsystem gets `0002-*`)"
- SC #3: "`ve subsystem list` outputs each subsystem's directory name and status in the format: `docs/subsystems/0001-validation [DISCOVERING]`"
- SC #4: "`ve subsystem list` with no subsystems outputs 'No subsystems found' to stderr and exits with code 1"
- SC #6: "errors with a message like 'Subsystem 'validation' already exists at docs/subsystems/0001-validation'"
- SC #7: "`src/templates/subsystem_overview.md` contains a minimal placeholder template..."

The body's "This chunk builds upon" line also names `chunk 0014-subsystem_schemas_and_model` and asserts the directory structure follows the `{NNNN}-{short_name}` convention.

# Reality

The `ordering_remove_seqno` chunk and follow-up migrations removed the `{NNNN}-` directory prefix entirely. Verification against current code:

1. **No `0001-` prefixes anywhere in `docs/subsystems/`:**
   ```
   $ ls docs/subsystems/
   cluster_analysis
   cross_repo_operations
   friction_tracking
   orchestrator
   template_system
   workflow_artifacts
   ```

2. **`Subsystems.create_subsystem` (`src/subsystems.py:162-208`) creates `docs/subsystems/<shortname>/` directly** — there is no sequence number to increment. SC #2 is no longer implementable.

3. **`list_subsystems` (`src/cli/subsystem.py:56-94`) emits exit code 0, not 1, on empty:**
   ```python
   if not subsystem_list:
       ...
       click.echo("No subsystems found")
       raise SystemExit(0)
   ```
   SC #4 directly contradicted.

4. **The duplicate-detection error message no longer carries a `0001-` prefix** (`src/cli/subsystem.py:142`):
   ```python
   click.echo(f"Error: Subsystem '{shortname}' already exists at docs/subsystems/{existing}", err=True)
   ```
   `existing` is a bare shortname now.

5. **The template path is wrong**: SC #7 names `src/templates/subsystem_overview.md`. The actual template lives at `src/templates/subsystem/OVERVIEW.md.jinja2` — different directory layout (subdirectory + Jinja2 extension), per the workflow_artifacts subsystem's template layout.

# Workaround

None — the `ve subsystem discover` / `list` commands work; the doc just describes a long-superseded behavior.

# Fix paths

1. **Historicalize candidate.** This chunk's load-bearing claims are either (a) contradicted by current code, (b) owned by `ordering_remove_seqno` (the prefix removal), or (c) owned by the active `subsystems.py` / `cli/subsystem.py` files. Pattern B (intent fully superseded) holds for most claims, but SC #5 (`validate_identifier` shortname rejection) and SC #7's "minimal placeholder template with frontmatter (status: DISCOVERING) and section headers" are still uniquely held by this chunk's framing — historicalization would lose them. Recommended: a successor chunk that re-establishes the discover/list contract under post-prefix naming, then historicalize this one.
2. Sweep stale `{NNNN}-` SCs out in a post-`ordering_remove_seqno` cleanup chunk and update SC #4's exit code expectation.

# Audit context

Detected by `intent_active_audit` batch 10g. Veto fired hard — multiple SCs over-claim against current code. No prose rewrite attempted. Did not historicalize because at least one SC (#5, #7's template content) is still uniquely held by this chunk and isn't owned elsewhere; safer to log and let a successor chunk own the post-prefix discover contract first.
