
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Four distinct changes span three files. Each change is self-contained enough
to implement and test independently, but they compose into the full ergonomic
story the GOAL describes.

1. **Uncommitted-changes gate** (`src/entity_repo.py`): replace the
   `git status --porcelain` check in `merge_entity` with a helper that
   filters out `??` (untracked) lines, so intentionally-untracked entity
   artifacts (session transcripts in `episodic/`, decay logs, snapshot
   directories) don't block the operation.

2. **Optional SOURCE in merge** (`src/entity_repo.py` + `src/cli/entity.py`):
   make the `source` parameter of `merge_entity` optional (`None` resolves from
   the entity's configured `origin` remote). Mirror this in the CLI by making
   the `SOURCE` argument optional.

3. **`pull` auto-merge** (`src/entity_repo.py` + `src/cli/entity.py`): when
   `pull_entity` detects diverged histories (currently raises `MergeNeededError`),
   delegate to `merge_entity` instead. The CLI `pull` command handles
   `MergeConflictsPending` the same way `merge` does, including `--yes` bypass.

4. **Agent SDK resolver** (`src/entity_merge.py`): rewrite
   `resolve_wiki_conflict` to try the Claude Code agent SDK first (routes
   through the operator's Claude Max subscription — no `ANTHROPIC_API_KEY`
   required) and fall back to the Anthropic SDK. Replace the retired
   `claude-3-5-haiku-latest` with a single centralized model constant
   (`_RESOLVER_MODEL`) used only on the fallback path.

Tests are written first (TDD per TESTING_PHILOSOPHY.md). All tests must pass
before marking the chunk complete.

## Sequence

### Step 1: Add `_has_tracked_uncommitted_changes` helper to `entity_repo.py`

Create a private helper that returns `True` only when there are uncommitted
changes to *tracked* files — ignoring `??` untracked lines:

```python
# Chunk: docs/chunks/entity_sync_ergonomics - Uncommitted gate ignores untracked artifacts
def _has_tracked_uncommitted_changes(entity_path: Path) -> bool:
    """Return True if any tracked files have uncommitted changes.

    Ignores intentionally-untracked entity artifacts (session transcripts,
    decay logs, snapshot directories) which appear as '??' in git status --porcelain.
    """
    status_out = _run_git_output(entity_path, "status", "--porcelain")
    return any(
        line and not line.startswith("??")
        for line in status_out.splitlines()
    )
```

Place it near the existing `_run_git_output` helper (around line 330).

**Tests first** — add to `tests/test_entity_push_pull.py` in a new
`TestUncommittedGate` class:

- `test_clean_repo_not_flagged` — a newly created entity repo has no tracked
  changes; helper returns `False`.
- `test_untracked_file_not_flagged` — writing an untracked file returns `False`.
- `test_modified_tracked_file_flagged` — modifying a tracked file (e.g. `ENTITY.md`)
  returns `True`.
- `test_staged_change_flagged` — staging a new tracked file returns `True`.

### Step 2: Swap `merge_entity`'s uncommitted check to use the helper

Location: `src/entity_repo.py`, inside `merge_entity`, around line 1094.

Replace:
```python
status_out = _run_git_output(entity_path, "status", "--porcelain")
if status_out.strip():
    raise RuntimeError(
        f"Entity '{entity_path.name}' has uncommitted changes. "
        "Commit or stash changes before merging."
    )
```

With:
```python
if _has_tracked_uncommitted_changes(entity_path):
    raise RuntimeError(
        f"Entity '{entity_path.name}' has uncommitted changes to tracked files. "
        "Commit or stash changes before merging."
    )
```

**Tests first** — add to `tests/test_entity_fork_merge.py` (or
`tests/test_entity_push_pull.py`):

- `test_merge_not_blocked_by_untracked_transcript` — create an entity with a
  bare origin, make an untracked `episodic/session.jsonl` file, then call
  `merge_entity` and verify it does NOT raise `RuntimeError` for uncommitted
  changes (it may raise for other reasons like nothing to merge; that's fine to
  catch separately).

### Step 3: Make `source` optional in `merge_entity`

Change the signature from:
```python
def merge_entity(entity_path: Path, source: str, ...) -> ...:
```
to:
```python
def merge_entity(entity_path: Path, source: str | None = None, ...) -> ...:
```

When `source` is `None`, resolve it from the entity's configured origin:

```python
if source is None:
    remote_result = subprocess.run(
        ["git", "-C", str(entity_path), "remote", "get-url", "origin"],
        capture_output=True, text=True,
    )
    if remote_result.returncode != 0:
        raise RuntimeError(
            f"Entity '{entity_path.name}' has no remote origin configured. "
            "Provide SOURCE explicitly or use 've entity set-origin' to add one."
        )
    source = remote_result.stdout.strip()
```

Insert this block after the `is_entity_repo` validation, before the
`_has_tracked_uncommitted_changes` check.

**Tests first** — add to `tests/test_entity_push_pull.py` in a new
`TestMergeEntityOptionalSource` class (or extend the existing fork/merge test):

- `test_merge_without_source_uses_configured_remote` — set up an entity with
  a bare origin that has diverged commits; call `merge_entity(entity_path)` with
  no source and verify the merge succeeds (returns `MergeResult` with
  `commits_merged > 0`).
- `test_merge_without_source_raises_when_no_remote` — entity with no origin;
  calling `merge_entity(entity_path)` raises `RuntimeError` mentioning `origin`.

### Step 4: Make SOURCE optional in the `merge` CLI command

Location: `src/cli/entity.py`, the `merge` command definition around line 1044.

Change:
```python
@click.argument("source")
```
to:
```python
@click.argument("source", required=False, default=None)
```

Update the docstring to reflect that SOURCE is now optional.

Update the resolver logic: when `source is None` and the entity directory is
not an existing attached entity name, pass `None` directly to `merge_entity`
(the library will resolve from remote). The existing "check if it's an attached
entity name" block should only run when `source` is not `None`:

```python
# Resolve source: check if it's an attached entity name first (only when given)
if source is not None:
    candidate = project_dir / ".entities" / source
    resolved_source = str(candidate) if candidate.exists() else source
else:
    resolved_source = None
```

**Tests first** — add to `tests/test_entity_fork_merge_cli.py`:

- `test_merge_cli_without_source_uses_remote` — set up an entity with a remote
  that has new commits; invoke `ve entity merge <name>` (no SOURCE argument);
  assert exit code 0 and output mentions merged commits.
- `test_merge_cli_without_source_no_remote_fails` — entity with no remote;
  invoke `ve entity merge <name>` (no SOURCE); assert non-zero exit and error
  mentions remote/origin.

### Step 5: Update `pull_entity` to auto-merge on diverged histories

Location: `src/entity_repo.py`, inside `pull_entity`, around line 635.

Currently, diverged histories raise `MergeNeededError`. Replace both
`MergeNeededError` raises (the "both sides diverged" and "local-only ahead"
cases) with calls to `merge_entity`.

**Return type change**: `pull_entity` currently returns `PullResult`. After
this change it may also return `MergeConflictsPending` (when the auto-merge
encounters wiki conflicts). Update the type annotation to
`PullResult | MergeConflictsPending`.

Diverged case implementation sketch:
```python
if incoming and local_only:
    # Auto-merge: delegate to merge_entity using the known remote URL
    remote_url = remote_check.stdout.strip()
    return merge_entity(entity_path, remote_url)

if local_only and not incoming:
    # Local is strictly ahead — nothing to merge. Inform operator to push.
    raise RuntimeError(
        f"Entity '{entity_path.name}' is ahead of origin with "
        f"{len(local_only)} local commit(s). Push first."
    )
```

Note: the "local-only ahead" case stays as a `RuntimeError` (not a merge — no
remote commits to merge in). The "both diverged" case auto-merges.

Also: save the remote URL earlier in the function (after the remote check
succeeds) so it's available for the diverged case:
```python
remote_url = remote_check.stdout.strip()
```

**Tests first** — add to `tests/test_entity_push_pull.py` in `TestPullEntity`:

- `test_pull_diverged_auto_merges` — set up two diverged entities (local commit
  + remote commit); call `pull_entity`; assert the result is a `MergeResult`
  (not a `MergeNeededError`) and the remote file is present locally.
- `test_pull_diverged_returns_merge_result_with_commit_count` — verify
  `commits_merged` in the returned `MergeResult` is accurate.
- Keep `test_pull_diverged_raises_merge_needed` and **invert its expectation**:
  rename to `test_pull_diverged_auto_merges_not_raises` and assert no
  `MergeNeededError` is raised.

### Step 6: Update the `pull` CLI command

Location: `src/cli/entity.py`, the `pull` command (around line 838).

Changes:
1. Add `--yes / -y` flag (mirrors `merge` command).
2. Remove the `MergeNeededError` catch (the exception is no longer raised).
3. Add handling for `MergeConflictsPending` — same flow as in the `merge`
   command: display each resolution, prompt for approval (or auto-approve with
   `--yes`), then call `commit_resolved_merge` or `abort_merge`.
4. Handle both return types from `pull_entity`:
   - `PullResult` → existing up-to-date / commits-merged output
   - `MergeResult` → "Merged N commit(s)" output (auto-merge succeeded cleanly)
   - `MergeConflictsPending` → conflict resolution flow

Updated command skeleton:
```python
@entity.command("pull")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, default=False,
              help="Auto-approve all LLM conflict resolutions without prompting")
@click.option("--project-dir", ...)
def pull(name: str, yes: bool, project_dir: pathlib.Path | None) -> None:
    ...
    try:
        result = entity_repo.pull_entity(entity_path)
    except (ValueError, RuntimeError) as e:
        raise click.ClickException(str(e))

    if isinstance(result, entity_repo.PullResult):
        if result.up_to_date:
            click.echo("Already up to date")
        else:
            click.echo(f"Merged {result.commits_merged} new commit(s) from origin")
    elif isinstance(result, entity_repo.MergeResult):
        if result.commits_merged == 0:
            click.echo("Already up to date")
        else:
            click.echo(f"Auto-merged {result.commits_merged} diverged commit(s) from origin")
    elif isinstance(result, entity_repo.MergeConflictsPending):
        # conflict resolution flow (same as merge command)
        ...
```

**Tests first** — update `tests/test_entity_push_pull_cli.py`:

- Rename/update `test_pull_cli_diverged_warns_merge_needed` →
  `test_pull_cli_diverged_auto_merges` — assert exit 0 and output mentions
  "merged" or "auto-merged".
- Add `test_pull_cli_diverged_with_conflicts_prompts` — mock
  `MergeConflictsPending` being returned; verify the conflict flow runs.
- Add `test_pull_cli_yes_flag_auto_approves_conflicts` — with `--yes`, assert
  conflicts are resolved without prompting.

### Step 7: Centralize model constant and add agent SDK to `entity_merge.py`

Location: `src/entity_merge.py`.

**7a. Add agent SDK import guard** (pattern from `entity_shutdown.py`):
```python
# Chunk: docs/chunks/entity_sync_ergonomics - Guard claude_agent_sdk import for wiki resolver
try:
    from claude_agent_sdk import ClaudeSDKClient
    from claude_agent_sdk.types import ClaudeAgentOptions, ResultMessage
except ModuleNotFoundError:
    ClaudeSDKClient = None
    ClaudeAgentOptions = None
    ResultMessage = None
```

**7b. Add centralized model constant** for the Anthropic SDK fallback path:
```python
# Chunk: docs/chunks/entity_sync_ergonomics - Centralized model for Anthropic SDK fallback
_RESOLVER_MODEL = "claude-haiku-4-20250514"
```

**7c. Add an async helper** that runs the resolver via agent SDK:
```python
async def _resolve_with_agent_sdk(prompt: str, cwd: pathlib.Path) -> str:
    """Run the conflict-resolution prompt via Claude Code agent SDK.

    Uses the operator's claude CLI subscription — no ANTHROPIC_API_KEY needed.
    """
    options = ClaudeAgentOptions(
        cwd=str(cwd),
        permission_mode="bypassPermissions",
        max_turns=1,
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, ResultMessage):
                if message.is_error or not message.result:
                    raise RuntimeError(
                        f"Agent SDK conflict resolver returned an error: {message.result}"
                    )
                return message.result
    raise RuntimeError("Agent SDK conflict resolver did not return a result")
```

**7d. Rewrite `resolve_wiki_conflict`** to accept an optional `entity_dir`
parameter and try agent SDK first:

```python
def resolve_wiki_conflict(
    filename: str,
    conflicted_content: str,
    entity_name: str,
    entity_dir: pathlib.Path | None = None,
) -> str:
    """Use the Claude Code agent SDK (or Anthropic API fallback) to synthesize
    conflicting wiki page versions.
    ...
    """
    import asyncio, pathlib as _pathlib

    hunks = parse_conflict_markers(conflicted_content)
    n = len(hunks)
    prompt = _build_resolver_prompt(entity_name, filename, n, conflicted_content)

    cwd = entity_dir if entity_dir is not None else _pathlib.Path.cwd()

    # Primary: Claude Code agent SDK (uses operator's Max subscription)
    if ClaudeSDKClient is not None:
        return asyncio.run(_resolve_with_agent_sdk(prompt, cwd))

    # Fallback: Anthropic SDK (requires ANTHROPIC_API_KEY)
    if anthropic is None:
        raise RuntimeError(
            "Wiki conflict resolution requires either the 'claude_agent_sdk' package "
            "(install with: pip install claude-agent-sdk) or the 'anthropic' package "
            "with ANTHROPIC_API_KEY set."
        )

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=_RESOLVER_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
```

Extract the prompt-building logic into a `_build_resolver_prompt` helper to
keep both paths using the same prompt.

**7e. Pass `entity_path` through** the call chain from `merge_entity` →
`resolve_wiki_conflict`. In `merge_entity` (in `entity_repo.py`), update the
call to:
```python
synthesized = _entity_merge.resolve_wiki_conflict(
    relative_path, conflicted_content, entity_path.name,
    entity_dir=entity_path,
)
```

**Tests first** — in `tests/test_entity_merge.py`:

- `test_model_constant_is_not_haiku_latest` — assert
  `entity_merge._RESOLVER_MODEL != "claude-3-5-haiku-latest"`.
- `test_agent_sdk_path_used_when_available` — patch `ClaudeSDKClient` to a mock
  and verify `resolve_wiki_conflict` calls it (not `anthropic.Anthropic()`).
- `test_agent_sdk_result_returned` — mock agent SDK to return a known string;
  verify `resolve_wiki_conflict` returns that string.
- `test_fallback_to_anthropic_sdk_when_agent_unavailable` — patch
  `ClaudeSDKClient = None` and provide a mock anthropic module; verify the
  Anthropic SDK is called.
- `test_fallback_error_mentions_api_key` — patch both `ClaudeSDKClient = None`
  and `anthropic = None`; verify `RuntimeError` message mentions
  `ANTHROPIC_API_KEY`.
- Update `test_raises_if_anthropic_not_available` to also set
  `ClaudeSDKClient = None`, so the existing test still covers the "both
  unavailable" case consistently.

### Step 8: Run full test suite and fix any failures

```bash
uv run pytest tests/ -x -q
```

Expected: all existing tests still pass (no regressions), and all new tests
pass. Pay attention to:
- `test_entity_push_pull.py` — the renamed/inverted diverged-history tests
- `test_entity_push_pull_cli.py` — the updated pull-diverged CLI test
- `test_entity_merge.py` — new agent SDK path tests

## Dependencies

No new external libraries. `claude_agent_sdk` and `anthropic` are already
conditional dependencies (import-guarded). Both packages are already in the
project's dependency tree via other usages.

## Risks and Open Questions

- **`asyncio.run` in `resolve_wiki_conflict`**: If the caller is already in
  an async context (unlikely here — `merge_entity` is sync), `asyncio.run`
  will fail. Given the current call stack is fully synchronous, this is fine.
  If the concern materializes, wrap in `asyncio.get_event_loop().run_until_complete`.

- **Agent SDK `max_turns=1`**: The conflict resolver prompt asks for a single
  text output (no tool use). `max_turns=1` is appropriate. If the agent decides
  to use a tool (unlikely for a text-only prompt with
  `permission_mode="bypassPermissions"`), the turn count may exhaust.
  Watch for this in testing.

- **`_RESOLVER_MODEL` selection**: The fallback uses `claude-haiku-4-20250514`
  (current fast model, same family as the retired `claude-3-5-haiku-latest`).
  Validate this model identifier is accepted by the Anthropic API before
  finalizing.

- **`pull_entity` return type breadth**: The CLI must `isinstance`-check
  `MergeResult` vs `PullResult` — both have a `commits_merged` field but
  different semantics. Take care not to conflate them in the output messages.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->