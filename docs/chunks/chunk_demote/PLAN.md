

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

`ve task demote` already handles moving an artifact from the external
architecture repo into a single project's `docs/chunks/` directory — it
copies files, removes the external.yaml pointer, and updates the
`dependents` list.  `ve chunk demote` builds on that foundation and adds
four things `ve task demote` intentionally omits:

1. **Scope validation** — refuse if any `code_path` in the chunk's GOAL.md
   references a repo other than the target.
2. **Frontmatter rewriting** — strip `org/repo::` prefixes from
   `code_paths` and `code_references[].ref`, and remove the `dependents`
   block, from the files written into the target project.
3. **Full-cascade pointer cleanup** — delete `external.yaml` pointer
   directories in every non-target participating project.
4. **Architecture source removal** — `shutil.rmtree` the architecture
   chunk directory after all pointer clean-up is done. (Using
   `shutil.rmtree` rather than `git rm` keeps the command git-agnostic per
   DEC-005; the operator manages version-control operations.)

The command runs from a task directory (or accepts `--cwd`), resolves all
paths via the existing `load_task_config` / `resolve_repo_directory`
utilities, and is idempotent: if a step has already been completed, it
detects that and moves on without failing.

**Module location deviation:** The chunk's GOAL.md lists
`src/chunk/demote.py` as a code path. The codebase follows a flat module
pattern for chunk-related utilities (`src/chunk_validation.py`,
`src/chunks.py`). Creating a single-file package `src/chunk/` for one
module adds unnecessary hierarchy. The logic lands in `src/chunk_demote.py`
instead.

The plan follows the project's TDD workflow: write failing tests first,
implement to make them pass, verify.

## Subsystem Considerations

- **`docs/subsystems/cross_repo_operations`** (if documented): This chunk
  IMPLEMENTS a new cross-repo operation — the full-collapse demotion path.
- **`docs/subsystems/workflow_artifacts`** (if documented): This chunk USES
  the artifact manager pattern to find and copy chunk files.

## Sequence

### Step 1: Write failing tests (`tests/test_chunk_demote.py`)

Write the test file before any implementation. Tests must fail initially.

**Test class `TestValidateChunkScope`** — unit tests for the scope
validator:

- `test_accepts_bare_paths`: GOAL.md with `code_paths: [src/foo.py]` (no
  `::` prefix) passes validation.
- `test_accepts_target_prefixed_paths`: paths starting with
  `cloudcapitalco/myrepo::` where `myrepo` is the target pass.
- `test_rejects_other_repo_paths`: a path like `cloudcapitalco/otherrepo::src/bar.py`
  returns that path as an offending entry.
- `test_empty_code_paths_passes`: chunk with no code_paths is valid (nothing
  to validate).
- `test_multiple_violations_reported`: all offending paths are returned, not
  just the first.

**Test class `TestStripProjectPrefix`** — unit tests for prefix stripping:

- `test_strips_org_repo_prefix`: `"cloudcapitalco/myrepo::src/foo.py"` →
  `"src/foo.py"`.
- `test_leaves_bare_path_unchanged`: `"src/bar.py"` → `"src/bar.py"`.
- `test_leaves_other_org_repo_unchanged`: `"other/repo::src/x.py"` is not
  stripped (wrong org/repo).
- `test_strips_ref_with_symbol`: `"acme/proj::src/f.py#Cls"` → `"src/f.py#Cls"`.

**Test class `TestRewriteChunkFrontmatter`** — unit tests for the
frontmatter rewriter applied to a GOAL.md file on disk:

- `test_strips_code_path_prefixes`: after rewrite, `code_paths` contain bare
  paths.
- `test_strips_code_reference_ref_prefixes`: `code_references[].ref` fields
  have prefixes stripped.
- `test_removes_dependents_key`: after rewrite, `dependents` key is absent.
- `test_preserves_other_frontmatter_fields`: `status`, `ticket`,
  `created_after`, etc. are unchanged.
- `test_noop_on_bare_paths`: file with no prefixed paths is written back
  unchanged (no spurious diff).

**Test class `TestDemoteChunkCore`** — integration tests for
`demote_chunk()`:

- `test_happy_path`: set up a task dir with architecture repo containing a
  chunk (GOAL.md + PLAN.md), two participating projects each with
  external.yaml pointers.  Run `demote_chunk()` targeting project 1.
  Assert:
  - target project has GOAL.md + PLAN.md (no external.yaml)
  - GOAL.md in target has no `dependents` key and no `org/repo::` prefixes
  - non-target project's `docs/chunks/<name>/` directory is deleted
  - architecture source dir no longer exists
- `test_scope_violation_rejected`: a chunk whose GOAL.md has
  `code_paths: [cloudcapitalco/other::src/x.py]` raises `ChunkDemoteError`
  listing the offending path; no filesystem changes occur.
- `test_refuses_non_pointer_in_other_project`: if project 2 has GOAL.md
  instead of external.yaml, `demote_chunk()` raises `ChunkDemoteError`
  with a clear message pointing at the conflicting directory.
- `test_idempotent_rerun_after_copy`: simulate partial completion where the
  target already has GOAL.md but architecture source and other pointers
  still exist.  Re-running finishes the cascade (cleanup + source removal)
  without error.
- `test_idempotent_rerun_after_full_completion`: everything is already done
  (no architecture dir, no other pointers).  Re-running succeeds and
  reports nothing to do.
- `test_returns_summary_dict`: return value contains
  `demoted_chunk`, `target_project`, `pointers_removed`, `source_removed`.

**Test class `TestDemoteChunkCLI`** — CLI integration tests:

- `test_command_exists`: `ve chunk demote --help` exits 0.
- `test_happy_path_cli`: invoke `ve chunk demote my_chunk proj1 --cwd <task_dir>`,
  assert exit 0, output mentions demoted chunk name.
- `test_scope_violation_exits_nonzero`: pass a chunk with cross-repo paths;
  assert exit 1 and error message lists offending paths.
- `test_missing_chunk_exits_nonzero`: chunk not in architecture; exit 1.
- `test_no_git_operations_performed`: confirm no git commands run (check git
  status is unchanged before and after).

Location: `tests/test_chunk_demote.py`

---

### Step 2: Create `src/chunk_demote.py`

New flat module containing:

```python
# Chunk: docs/chunks/chunk_demote - Full-collapse demotion of cross-repo chunks

class ChunkDemoteError(Exception):
    """Raised when chunk demotion cannot proceed."""

def validate_chunk_scope(chunk_dir: Path, target_repo: str) -> list[str]:
    """Return offending code_paths that reference a repo other than target_repo.

    A code_path is offending if it contains '::' and the prefix before '::'
    is not 'cloudcapitalco/<target_repo>' (or any org/repo where repo != target_repo).

    Args:
        chunk_dir: Path to the chunk directory containing GOAL.md.
        target_repo: Short repo name (e.g. 'dotter'), matched against the
                     repo component in any 'org/repo::' prefix.

    Returns:
        List of offending code_path strings (empty means all-clear).
    """

def strip_project_prefix(value: str, org_repo: str) -> str:
    """Strip 'org_repo::' prefix from value if present.

    Args:
        value: A code_path or code_reference ref string.
        org_repo: The full 'org/repo' string to strip (e.g. 'cloudcapitalco/dotter').

    Returns:
        Value with prefix stripped, or original value if prefix not present.
    """

def rewrite_chunk_frontmatter(file_path: Path, org_repo: str) -> None:
    """Rewrite frontmatter in-place: strip org_repo prefixes, remove dependents.

    Reads the file, parses frontmatter, applies transformations, writes back.
    Idempotent: re-running on already-rewritten frontmatter is a no-op.

    Transformations:
    - code_paths: strip 'org_repo::' prefix from each entry
    - code_references[].ref: strip 'org_repo::' prefix
    - dependents: remove key entirely

    Args:
        file_path: Path to the markdown file (GOAL.md or PLAN.md).
        org_repo: The full 'org/repo' string to strip from prefixes.
    """

def demote_chunk(
    task_dir: Path,
    chunk_name: str,
    target_project_ref: str,
) -> dict:
    """Demote a cross-repo chunk to a single project, collapsing all bookkeeping.

    Full-collapse demotion sequence:
    1. Load task config, resolve architecture path and target project path.
    2. Validate architecture/docs/chunks/<name>/ exists (or detect already-removed).
    3. Validate target project has external.yaml (or detect already-copied).
    4. Check no other participating project has non-pointer chunk content.
    5. Validate scope: all code_paths must be bare or target-prefixed.
    6. Copy GOAL.md + PLAN.md to target project (skip if already done).
    7. Rewrite frontmatter in target (strip prefixes, remove dependents).
    8. Delete external.yaml pointer dirs in all non-target projects.
    9. shutil.rmtree the architecture source dir (skip if already gone).

    Returns:
        {
            "demoted_chunk": str,        # chunk name
            "target_project": str,       # org/repo of target
            "pointers_removed": int,     # count of non-target pointer dirs deleted
            "source_removed": bool,      # whether architecture source was removed
        }

    Raises:
        ChunkDemoteError: with a user-friendly message if any precondition fails.
    """
```

The function reads the architecture source's `dependents` list to discover
all participating projects (for the pointer cleanup in step 8). When the
architecture source is already removed at entry (idempotent re-run), the
function reads the target project's `external.yaml` pointer (which was
already replaced with GOAL.md) — or falls back to looking in all sibling
project directories for external.yaml files pointing at the same artifact.

Backreference comment at module level:
```python
# Chunk: docs/chunks/chunk_demote - Full-collapse demotion path for cross-repo chunks
```

---

### Step 3: Add `ve chunk demote` to `src/cli/chunk.py`

Append a new Click command to the `chunk` group:

```python
@chunk.command("demote")
@click.argument("chunk_name")
@click.argument("target_project")
@click.option(
    "--cwd",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=".",
    help="Task directory (default: current directory).",
)
def demote_cmd(chunk_name, target_project, cwd):
    """Demote a cross-repo chunk to a single project.

    Moves CHUNK_NAME from architecture/docs/chunks/ into
    TARGET_PROJECT/docs/chunks/, rewrites frontmatter to remove cross-repo
    prefixes and the dependents block, removes external.yaml pointers in
    all other participating projects, and deletes the architecture source
    directory.

    Must be run from a task directory (or pass --cwd pointing at one).

    \b
    Example:
        ve chunk demote my_feature dotter
        ve chunk demote my_feature dotter --cwd /path/to/task
    """
    from chunk_demote import demote_chunk, ChunkDemoteError

    try:
        result = demote_chunk(
            task_dir=cwd,
            chunk_name=chunk_name,
            target_project_ref=target_project,
        )
        click.echo(
            f"Demoted chunk '{result['demoted_chunk']}' to {result['target_project']}"
        )
        click.echo(f"  Pointer dirs removed: {result['pointers_removed']}")
        if result["source_removed"]:
            click.echo("  Architecture source directory removed")
        else:
            click.echo("  Architecture source was already absent (idempotent)")
    except ChunkDemoteError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
```

Add the backreference at the call site:
```python
# Chunk: docs/chunks/chunk_demote - ve chunk demote command
```

---

### Step 4: Create `src/templates/commands/chunk-demote.md.jinja2`

A `/chunk-demote` skill template that wraps the CLI with operator
confirmation and a summary report.

Content outline:
```
---
name: chunk-demote
description: Demote a cross-repo chunk to a single project ...
---

## Tips
{% include "partials/common-tips.md.jinja2" %}

## Instructions

1. Identify the chunk to demote and the target project:
   - Ask the operator: "Which chunk name and target project?"
   - OR read the chunk name from the current IMPLEMENTING chunk
     (`ve chunk list --current`).

2. Read `architecture/docs/chunks/<name>/GOAL.md` and summarise:
   - Current code_paths (highlight any cross-repo prefixed ones)
   - Number of participating projects (dependents list)
   - Decision docs that will be preserved:
     `architecture/docs/reviewers/baseline/decisions/<name>_*.md`

3. Present the demotion plan to the operator and ask for confirmation:
   "This will:
   - Copy GOAL.md + PLAN.md to <target>/docs/chunks/<name>/
   - Strip org/repo prefixes from code_paths and code_references
   - Remove the dependents block
   - Delete external.yaml pointer dirs in: [other projects]
   - Remove architecture/docs/chunks/<name>/

   Proceed? (y/n)"

4. Run `ve chunk demote <name> <target_project> --cwd <task_dir>`

5. Report results:
   - Files moved
   - Pointers removed
   - Decision docs left in place at architecture/docs/reviewers/...
   - Next steps: commit changes in each affected repo
```

---

### Step 5: Update `docs/trunk/EXTERNAL.md`

Append a "Demoting External Artifacts" section that explains:

- When to demote (scope has collapsed to one project after implementation)
- The two available commands:
  - `ve task demote <name>` — standard task-context demotion, leaves
    architecture source in place, updates `dependents` list
  - `ve chunk demote <name> <target>` — full-collapse demotion: strips
    cross-repo prefixes, removes all other pointers, deletes architecture
    source
- Invariants the full-collapse operation enforces (no dangling pointers,
  no prefix pollution, decision docs preserved)
- When NOT to use `ve chunk demote` (multi-project chunks where scope
  hasn't collapsed)

---

### Step 6: Run tests and iterate

```bash
uv run pytest tests/test_chunk_demote.py -v
```

Fix any issues until all tests pass, then confirm the broader suite is
green:

```bash
uv run pytest tests/ -q
```

---

### Step 7: Update GOAL.md code_paths

After implementation, update `docs/chunks/chunk_demote/GOAL.md`
`code_paths` to reflect the actual module location:

```yaml
code_paths:
- src/cli/chunk.py
- src/chunk_demote.py        # flat module, not src/chunk/demote.py (see plan)
- src/templates/commands/chunk-demote.md.jinja2
- docs/trunk/EXTERNAL.md
```

## Dependencies

- `src/task/demote.py` — `read_artifact_frontmatter()` utility for reading
  chunk frontmatter from the architecture source (already implemented).
- `src/task/config.py` — `load_task_config()`, `resolve_repo_directory()`,
  `resolve_project_ref()` for resolving task paths (already implemented).
- `src/frontmatter.py` — `extract_frontmatter_dict()` and
  `update_frontmatter_field()` for frontmatter I/O (already implemented).

## Risks and Open Questions

- **Idempotency when architecture source is gone**: after a full successful
  run, the architecture source no longer exists. On re-run we can't read
  `dependents` from it. The fallback is to scan all sibling project
  directories in the task for external.yaml files pointing at the same
  artifact_id. This is slightly heuristic but safe: if an external.yaml
  still exists, we delete it; if not, we skip. Worst case we miss a
  stale pointer in a project that wasn't in the task, but those would have
  been out-of-scope anyway.
- **`git rm` vs `shutil.rmtree`**: GOAL.md's success criterion #6
  mentions `git rm -r architecture/docs/chunks/<name>/`. The project uses
  DEC-005 (no prescribed git operations). We use `shutil.rmtree` instead
  and the skill template instructs the operator to commit the resulting
  deletions. This is the correct behaviour for this codebase.
- **Multi-repo prefix formats**: The GOAL.md mentions `cloudcapitalco/<repo>::`
  as the prefix format to strip. We strip any `org/repo::` prefix where the
  `repo` component matches `target_repo`, regardless of org. This is more
  general and avoids hard-coding `cloudcapitalco`. The scope validator
  likewise checks the repo component only when determining if a path is
  cross-repo.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
