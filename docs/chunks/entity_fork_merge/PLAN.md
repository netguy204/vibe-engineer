

# Implementation Plan

## Approach

We implement `ve entity fork` and `ve entity merge` by extending `entity_repo.py` with
two new library functions and creating a new `entity_merge.py` module for LLM-assisted
conflict resolution. The CLI commands live in `src/cli/entity.py` alongside the existing
push/pull commands.

**Fork** is a `git clone` operation followed by a metadata update: clone the source entity
repo to a new directory, rewrite ENTITY.md to carry the new name and fork lineage, and make
an initial commit recording the fork origin. Full history is preserved.

**Merge** adds the source as a temporary git remote (`ve-merge-source`), fetches it, and
attempts `git merge`. If clean, it commits immediately. If there are conflicts, each
conflicting wiki markdown file is resolved using the `anthropic` API (same pattern as
`entity_shutdown.py`): both sides are submitted to the LLM with a synthesis prompt, and the
resolved content is returned for operator approval. Non-wiki binary/config conflicts are left
for the operator to handle manually. The merge does not commit until the operator approves.

**LLM conflict resolution** lives in `entity_merge.py`. It parses git conflict markers from
each conflicting `.md` file, submits both sides to the Anthropic API with a wiki-synthesis
prompt, and returns the resolved text. The `anthropic` import is guarded (like
`entity_shutdown.py`) to avoid hard-failing when the package is absent.

**Operator approval gate** lives in the CLI: after `merge_entity()` returns a pending
conflict result, the CLI displays each conflicting file's LLM resolution and asks for
approval (`y/N`). Only on approval does it call `commit_resolved_merge()` to stage the
resolved files and commit. Rejection calls `abort_merge()` (`git merge --abort`) to restore
the entity to its pre-merge state.

This mirrors the push/pull pattern: library functions (testable, no I/O side effects beyond
git) and thin CLI wrappers.

## Subsystem Considerations

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): This subsystem governs
  task-level cross-repo operations (task_init, external artifact ops). Entity fork/merge
  is a different domain (entity specialist repos, not VE task repos), so this subsystem
  does not apply. No deviations to note.

## Sequence

### Step 1: Add `forked_from` to `EntityRepoMetadata`

In `src/entity_repo.py`, add an optional `forked_from` field to `EntityRepoMetadata`:

```python
class EntityRepoMetadata(BaseModel):
    name: str
    created: str
    specialization: Optional[str] = None
    origin: Optional[str] = None
    role: Optional[str] = None
    forked_from: Optional[str] = None   # ← NEW: name of source entity if forked
```

This field is `None` for freshly created entities and set by `fork_entity()`.
No template change needed: the field is written programmatically during fork.

Location: `src/entity_repo.py`

### Step 2: Add result dataclasses for fork and merge

In `src/entity_repo.py`, add:

```python
@dataclass
class ForkResult:
    """Result of a fork_entity operation."""
    source_name: str        # name of the entity that was forked
    new_name: str           # name of the new fork
    dest_path: Path         # path to the new entity repo

@dataclass
class MergeResult:
    """Result of a clean merge_entity operation."""
    source: str             # URL or name of the merged source
    commits_merged: int     # number of new commits integrated
    new_pages: int          # wiki pages that were newly added
    updated_pages: int      # wiki pages that were modified

@dataclass
class ConflictResolution:
    """A single LLM-resolved conflict, pending operator approval."""
    relative_path: str      # path within entity repo (e.g., "wiki/domain/databases.md")
    synthesized: str        # LLM-synthesized content replacing the conflict markers
    is_wiki: bool           # True for .md files in wiki/; False for other files

@dataclass
class MergeConflictsPending:
    """Merge halted at conflicts; operator must approve before committing."""
    source: str
    resolutions: list[ConflictResolution]  # LLM-resolved (wiki) + raw conflicts (non-wiki)
    unresolvable: list[str]  # paths that couldn't be resolved (binary, non-wiki)
```

Location: `src/entity_repo.py`

### Step 3: Implement `fork_entity()` in `entity_repo.py`

```python
def fork_entity(
    source_path: Path,
    dest_dir: Path,
    new_name: str,
) -> ForkResult:
```

Steps:
1. Validate `source_path` is an entity repo (use `is_entity_repo()`). Raise `ValueError` if not.
2. Validate `new_name` matches `ENTITY_REPO_NAME_PATTERN`. Raise `ValueError` if not.
3. Validate `dest_dir / new_name` does not already exist. Raise `ValueError` if it does.
4. Run `git clone <source_path> <dest_dir/new_name>` with `protocol.file.allow=always`
   to perform a full local clone (all history preserved).
5. Read the current ENTITY.md frontmatter from the clone.
6. Write updated ENTITY.md frontmatter: set `name = new_name`, set
   `forked_from = source_metadata.name`, keep all other fields intact.
   Use a simple YAML round-trip: read the file, replace frontmatter block, rewrite.
7. Run `git add ENTITY.md && git commit -m "Forked from <source_name>"` in the clone.
8. Return `ForkResult(source_name=source_metadata.name, new_name=new_name,
   dest_path=dest_dir/new_name)`.

The clone retains the original `origin` remote (pointing to the source's origin). Callers
that want an independent origin should run `ve entity set-origin` afterwards.

Location: `src/entity_repo.py`

### Step 4: Create `src/entity_merge.py` — conflict marker parsing

New module. Add backreference comment at module level:
```python
# Chunk: docs/chunks/entity_fork_merge - LLM-assisted wiki conflict resolution
```

Implement:

```python
@dataclass
class ConflictHunk:
    ours: str       # content between <<<<<<< and =======
    theirs: str     # content between ======= and >>>>>>>

def parse_conflict_markers(content: str) -> list[ConflictHunk]:
    """Parse all conflict hunks from a file with git conflict markers.

    Returns an empty list if no conflicts are present.
    """
```

The regex should handle the standard format:
```
<<<<<<< HEAD
<ours>
=======
<theirs>
>>>>>>> <ref>
```

Return all hunks found. If the file has no conflicts, return `[]`.

Location: `src/entity_merge.py`

### Step 5: Implement `resolve_wiki_conflict()` in `entity_merge.py`

```python
def resolve_wiki_conflict(
    filename: str,
    conflicted_content: str,
    entity_name: str,
) -> str:
    """Use the Anthropic API to synthesize conflicting wiki page versions.

    Args:
        filename: Relative path of the file (for context in prompt)
        conflicted_content: Full file content including git conflict markers
        entity_name: Name of the entity being merged (for prompt context)

    Returns:
        Synthesized content with all conflict markers resolved.

    Raises:
        RuntimeError: If anthropic is not installed or API call fails.
    """
```

Implementation:
1. Guard import: `if anthropic is None: raise RuntimeError("anthropic not installed")`
2. Parse conflict hunks from `conflicted_content` using `parse_conflict_markers()`.
3. Build a synthesis prompt:
   ```
   You are {entity_name}, an AI specialist with persistent knowledge across projects.
   You are merging two versions of your wiki page: {filename}.

   The file has {n} conflict(s) where your knowledge diverged. For each conflict,
   Version A reflects knowledge from one context and Version B reflects knowledge
   from another context.

   Your task: synthesize these conflicts into a single coherent version that preserves
   ALL valuable knowledge from both contexts. Do not discard either side — find the
   synthesis that a single expert would write having had both experiences.

   Return the COMPLETE file content with all conflict markers resolved.
   Output only the file content, no commentary.

   --- File with conflict markers ---
   {conflicted_content}
   ```
4. Call `anthropic.Anthropic().messages.create(...)` using `claude-3-5-haiku-latest`
   (cheap, fast — this is a synthesis task, not a reasoning task).
5. Return the response text.

Location: `src/entity_merge.py`

### Step 6: Implement `merge_entity()` in `entity_repo.py`

```python
def merge_entity(
    entity_path: Path,
    source: str,
    resolve_conflicts: bool = True,
) -> MergeResult | MergeConflictsPending:
```

Steps:
1. Validate `entity_path` is an entity repo. Raise `ValueError` if not.
2. Check no uncommitted changes in `entity_path`. Raise `RuntimeError` if dirty (merge
   would be ambiguous).
3. Add source as temporary remote `ve-merge-source`:
   `git remote add ve-merge-source <source>`
   Use `protocol.file.allow=always` for local paths.
4. `git fetch ve-merge-source` to fetch all refs.
5. Attempt `git merge ve-merge-source/main --no-commit --no-ff` (or `FETCH_HEAD`).
   Use `--no-commit` so we can inspect and potentially modify before committing.
6. Check `git status --porcelain` for conflict markers (lines starting with `UU`, `AA`,
   `DD`, etc.).
7. **If no conflicts**: count new commits (`git rev-list HEAD..ve-merge-source/main`
   before merge), count new/updated pages in `wiki/`. Stage all changes
   (`git add -A`), commit with message `"Merge learnings from <source_name>"`.
   Remove temp remote. Return `MergeResult(...)`.
8. **If conflicts and `resolve_conflicts=True`**:
   a. For each conflicted file: read content (which contains conflict markers).
   b. If file is a wiki markdown file (`wiki/**/*.md` or `wiki/*.md`) and `anthropic`
      is available: call `entity_merge.resolve_wiki_conflict()`.
   c. Otherwise: add to `unresolvable` list.
   d. Remove temp remote.
   e. Return `MergeConflictsPending(source, resolutions, unresolvable)`.
   f. Note: git merge is left in-progress (not aborted). The CLI will either
      commit or abort based on operator decision.
9. **If conflicts and `resolve_conflicts=False`**: abort merge, remove temp remote,
   raise `RuntimeError` with conflict list.
10. Always remove `ve-merge-source` remote in a `finally` block to avoid state leakage.

Location: `src/entity_repo.py`

### Step 7: Implement `commit_resolved_merge()` and `abort_merge()` in `entity_repo.py`

```python
def commit_resolved_merge(
    entity_path: Path,
    resolutions: list[ConflictResolution],
    source_name: str,
) -> None:
    """Write resolved content, stage all files, and complete the merge commit."""

def abort_merge(entity_path: Path) -> None:
    """Abort an in-progress merge, restoring the entity to pre-merge state."""
```

`commit_resolved_merge()`:
1. For each resolution in `resolutions`: write `entity_path / resolution.relative_path`
   with `resolution.synthesized` content.
2. `git add -A` to stage all resolved files.
3. `git commit -m "Merge learnings from <source_name>"` — git will use the
   in-progress merge commit message automatically.

`abort_merge()`:
1. `git merge --abort` in `entity_path`.

Location: `src/entity_repo.py`

### Step 8: Add `fork` and `merge` CLI commands to `src/cli/entity.py`

**`ve entity fork <name> <new-name>`**:

```python
@entity.command("fork")
@click.argument("name")
@click.argument("new_name")
@click.option("--output-dir", type=click.Path(path_type=pathlib.Path), default=None,
              help="Directory to create fork in (default: same parent as source entity)")
@click.option("--project-dir", ...)
def fork(name, new_name, output_dir, project_dir):
```

- Resolves `entity_path = project_dir / ".entities" / name`
- `output_dir` defaults to `entity_path.parent` (so fork lands alongside original in `.entities/`)
- Calls `entity_repo.fork_entity(entity_path, output_dir, new_name)`
- Prints:
  ```
  Forked 'name' → 'new_name' at <dest_path>
  Original origin: <url> (use 've entity set-origin' to point fork at a new remote)
  ```

**`ve entity merge <name> <source>`**:

```python
@entity.command("merge")
@click.argument("name")
@click.argument("source")
@click.option("--yes", "-y", is_flag=True, default=False,
              help="Auto-approve all LLM conflict resolutions without prompting")
@click.option("--project-dir", ...)
def merge(name, source, yes, project_dir):
```

- Resolves `entity_path = project_dir / ".entities" / name`
- If `source` matches an entity name in `.entities/`, resolves to that path.
  Otherwise treats `source` as a URL or local path.
- Calls `entity_repo.merge_entity(entity_path, resolved_source)`
- **If `MergeResult`**: prints summary (`Merged N commits — X new pages, Y updated pages`)
- **If `MergeConflictsPending`**:
  - For each resolution in `resolutions`: print filename + synthesized content
  - If `--yes`: approve all and call `commit_resolved_merge()`
  - Otherwise: prompt `Approve this resolution? [y/N]` for each file
    - If all approved: call `commit_resolved_merge()`
    - If any rejected: call `abort_merge()`, exit with non-zero code
  - Reports unresolvable files (if any) and directs user to resolve manually

Location: `src/cli/entity.py`

Add backreference comment at each new command:
```python
# Chunk: docs/chunks/entity_fork_merge - Fork entity CLI command
# Chunk: docs/chunks/entity_fork_merge - Merge entity CLI command
```

### Step 9: Write unit tests for `fork_entity()` — `tests/test_entity_fork_merge.py`

New test file. Reuse `make_entity_with_origin` helper from `test_entity_push_pull.py`
by extracting it to `conftest.py` (it's now needed in a second file — per testing
philosophy, extract when reusing).

Tests:

**`TestForkEntity`**:
- `test_fork_creates_independent_clone`: after fork, `dest/new_name` exists as valid
  entity repo (ENTITY.md present, is_entity_repo passes)
- `test_fork_preserves_full_history`: fork has same number of commits as source
  (full history, not shallow)
- `test_fork_updates_entity_name`: ENTITY.md in fork has `name = new_name`
- `test_fork_records_forked_from`: ENTITY.md in fork has `forked_from = source_name`
- `test_fork_commit_message_contains_source`: fork's HEAD commit message contains
  "Forked from"
- `test_fork_raises_if_source_not_entity_repo`: `ValueError` for non-entity path
- `test_fork_raises_if_dest_exists`: `ValueError` if `dest_dir/new_name` already exists
- `test_fork_raises_if_invalid_name`: `ValueError` for names with spaces or capitals
- `test_fork_is_independent`: after forking, adding a commit to source does NOT appear
  in fork (they are independent)

### Step 10: Write unit tests for `merge_entity()` — clean merge path

In `tests/test_entity_fork_merge.py`:

**`TestMergeEntityClean`**:
- `test_clean_merge_integrates_new_pages`: after merge, wiki pages from source appear
  in target
- `test_clean_merge_returns_merge_result`: returns `MergeResult` (not
  `MergeConflictsPending`)
- `test_clean_merge_commits_with_summary_message`: HEAD commit message contains
  "Merge learnings from"
- `test_clean_merge_counts_new_pages`: `MergeResult.new_pages` equals number of newly
  added wiki pages
- `test_merge_raises_if_target_not_entity_repo`: `ValueError` for non-entity path
- `test_merge_raises_if_dirty`: `RuntimeError` when target has uncommitted changes

### Step 11: Write unit tests for `parse_conflict_markers()` and `entity_merge.py`

In `tests/test_entity_merge.py`:

**`TestParseConflictMarkers`**:
- `test_parses_single_conflict`: correct ours/theirs for a file with one conflict
- `test_parses_multiple_conflicts`: correct list for file with two conflict hunks
- `test_returns_empty_for_clean_file`: `[]` for a file with no conflict markers
- `test_ours_and_theirs_content_correct`: verifies exact text of each side

**`TestResolveWikiConflict`** (using `unittest.mock` to mock `anthropic`):
- `test_calls_anthropic_messages_create`: verifies the API is called with both
  ours and theirs content in the prompt
- `test_returns_synthesized_content`: returns the text from the API response
- `test_raises_if_anthropic_not_available`: `RuntimeError` when `anthropic=None`

### Step 12: Write unit tests for `merge_entity()` — conflict path

In `tests/test_entity_fork_merge.py`, using `unittest.mock.patch` to mock
`entity_merge.resolve_wiki_conflict`:

**`TestMergeEntityWithConflicts`**:
- `test_conflict_returns_merge_conflicts_pending`: conflicting edits to same wiki
  line return `MergeConflictsPending` (not `MergeResult`)
- `test_conflict_resolutions_contain_synthesized_content`: resolution content
  comes from the (mocked) LLM
- `test_commit_resolved_merge_writes_files_and_commits`: after approval,
  `commit_resolved_merge()` writes files and HEAD commit is a merge commit
- `test_abort_merge_restores_clean_state`: after abort, git status is clean and
  conflicting files are not present

### Step 13: Write CLI tests — `tests/test_entity_fork_merge_cli.py`

Use Click's `CliRunner`. Set up a git project dir with an entity submodule using
`make_entity_with_origin` (now in conftest.py).

**Fork CLI tests**:
- `test_fork_command_creates_entity_in_entities_dir`: `ve entity fork name new-name`
  creates `.entities/new-name/` with valid entity repo
- `test_fork_command_exit_code_0`: command exits 0 on success
- `test_fork_command_output_contains_new_name`: output mentions the new name
- `test_fork_command_fails_on_unknown_entity`: exit code non-zero for unknown entity

**Merge CLI tests**:
- `test_merge_clean_exits_0`: `ve entity merge name <url>` exits 0 on clean merge
- `test_merge_clean_output_shows_summary`: output mentions merged pages
- `test_merge_conflicts_with_yes_flag_commits`: `--yes` approves all resolutions
  without prompting (mocked LLM)
- `test_merge_conflicts_rejection_aborts`: when user inputs `n`, merge is aborted
  and entity is back to clean state
- `test_merge_unknown_entity_fails`: non-zero exit for unknown entity name

### Step 14: Move shared test helpers to `conftest.py`

Before writing `test_entity_fork_merge.py`, move `make_entity_with_origin` from
`tests/test_entity_push_pull.py` to `tests/conftest.py` (per testing philosophy:
extract when a second file needs the helper). Update `test_entity_push_pull.py` to
import from conftest.

## Dependencies

- `entity_push_pull` chunk (DONE): provides the push/pull/set-origin infrastructure and
  git helper patterns (`_run_git`, `_run_git_output`, `is_entity_repo`) that fork/merge builds on
- `anthropic` Python package (already a project dependency via `entity_shutdown.py`)
- `claude_agent_sdk` is NOT needed here (no interactive agent sessions; direct Anthropic
  API call suffices for text synthesis)

## Risks and Open Questions

- **Conflict in non-wiki files** (e.g., `memories/core/*.md`, `ENTITY.md`): same-line
  edits to ENTITY.md metadata will conflict. The plan marks these as `unresolvable` and
  asks the operator to resolve manually. We could extend LLM resolution to
  `memories/` files in the future, but starting conservative is safer.

- **Anthropic API availability during merge**: if the API is unavailable or the key is
  missing, `resolve_wiki_conflict()` raises `RuntimeError`. The merge will be left
  in-progress. The CLI should catch this and tell the user to either resolve manually
  or abort the merge.

- **Large wiki pages**: very long markdown files may hit token limits. For the initial
  implementation, send the full conflicted content and trust the model; add truncation
  only if we see failures in practice.

- **Source resolution**: `ve entity merge specialist <source>` where `<source>` is
  an entity name currently in `.entities/` must resolve to the entity path. The CLI
  implementation must check `.entities/<source>` before treating the argument as a URL.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION, not at planning time. -->
