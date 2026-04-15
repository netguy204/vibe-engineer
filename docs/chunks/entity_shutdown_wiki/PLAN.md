

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The wiki-based shutdown pipeline replaces the fragile timeout-sensitive memory extraction with two reliable steps: (1) mechanical `git diff` on the entity's `wiki/` directory produces journal entries at zero LLM cost, then (2) an Agent SDK consolidation session reads the diffs alongside existing memory tiers and writes updated consolidated and core memories directly to disk. Legacy entities (no `wiki/` directory) continue using the current `run_consolidation()` pipeline — no behavior change there.

Key components touched:
- `src/entity_shutdown.py` — adds `extract_wiki_diff()`, `run_wiki_consolidation()`, and a `run_shutdown()` dispatcher
- `src/cli/entity.py` — updates the `shutdown` command to auto-detect wiki vs. legacy entities
- `src/templates/commands/entity-shutdown.md.jinja2` — wiki branch skips manual extraction
- `tests/test_entity_shutdown.py` — TDD: write failing tests before implementing

The Agent SDK consolidation session runs in `cwd=entity_dir` with `bypassPermissions`, giving the agent file-system access to read existing memories and write updated ones. No MCP servers or hooks are needed — this is a focused, bounded task. Reference `src/orchestrator/agent.py` for the `ClaudeSDKClient` usage pattern.

The async Agent SDK call is wrapped in `asyncio.run()` so `run_wiki_consolidation()` presents a synchronous interface matching the existing `run_consolidation()` signature.

## Subsystem Considerations

No documented subsystems are directly relevant. The implementation follows the `ClaudeSDKClient` pattern already established in `src/orchestrator/agent.py`.

## Sequence

### Step 1: Write failing tests (TDD)

**Before writing any implementation code**, write the following failing tests in `tests/test_entity_shutdown.py`. Check `tests/conftest.py` for existing helpers (git repo init, entity dir setup) before writing new ones.

**`TestExtractWikiDiff`** — tests for the new `extract_wiki_diff(entity_dir)` function:

- `test_returns_none_when_no_wiki_dir`: `entity_dir` exists but has no `wiki/` subdirectory → returns `None`
- `test_returns_empty_string_when_wiki_unchanged`: entity git repo with a committed wiki, no changes since commit → returns `""`
- `test_returns_diff_text_for_modified_wiki_page`: entity git repo where `wiki/identity.md` is modified → diff text contains `+` lines with the change
- `test_returns_diff_text_for_new_wiki_page`: entity git repo where `wiki/domain/new_thing.md` is an untracked new file → diff text contains the new file (requires staging via `git add wiki/`)

All tests use a `tmp_path`-backed git repo (`git init`, initial commit with `wiki/identity.md`, then modify/add files). No Agent SDK calls.

**`TestRunWikiConsolidation`** — tests for the dispatch and session launch. Mock `_run_consolidation_agent()` (the internal async Agent SDK call):

- `test_returns_empty_summary_when_no_wiki_changes`: wiki exists but `extract_wiki_diff()` returns `""` → returns `{"journals_added": 0, ...}` without launching Agent SDK
- `test_launches_agent_sdk_when_wiki_has_changes`: wiki has diff → Agent SDK helper is called once with the diff text and entity dir
- `test_legacy_entity_uses_legacy_pipeline`: entity without `wiki/` dir → `run_shutdown()` dispatcher calls `run_consolidation()` not `run_wiki_consolidation()`

**`TestShutdownCLI`** (integration) — update existing CLI tests or add new class:

- `test_wiki_shutdown_requires_no_memories_file`: `ve entity shutdown <wiki-entity>` succeeds without `--memories-file`
- `test_legacy_shutdown_requires_memories_file`: `ve entity shutdown <legacy-entity>` without `--memories-file` errors with a helpful message

### Step 2: Implement `extract_wiki_diff()` in `entity_shutdown.py`

Add this function to `entity_shutdown.py`. It is purely mechanical — no LLM.

```
# Chunk: docs/chunks/entity_shutdown_wiki - Mechanical wiki diff extraction
def extract_wiki_diff(entity_dir: Path) -> str | None:
```

**Logic**:
1. If `(entity_dir / "wiki")` does not exist → return `None` (legacy entity)
2. Run `git -C <entity_dir> add wiki/` — stage all wiki changes including new untracked files. This is safe (staging is reversible) and ensures new pages appear in the diff.
3. Run `git -C <entity_dir> diff --cached HEAD -- wiki/` — get comprehensive diff of all staged wiki changes vs HEAD.
4. On `returncode != 0` (e.g., entity repo has no prior commits yet): return `""` rather than crashing. Log a warning.
5. Return `result.stdout` (empty string if no wiki changes; diff text otherwise).

Use `subprocess.run` with `capture_output=True, text=True`.

### Step 3: Implement `_build_consolidation_prompt()` in `entity_shutdown.py`

Add a helper that builds the Agent SDK prompt from wiki diff + entity context:

```
def _build_consolidation_prompt(entity_name: str, wiki_diff: str) -> str:
```

The prompt must:
- Present the wiki diff as "what this entity learned this session"
- Instruct the agent to read `memories/consolidated/*.md` and `memories/core/*.md`
- Instruct the agent to integrate new learning: update matching consolidated memories, create new ones where no match exists
- **Encode the identity/values constraint explicitly**: "Core memories are NOT wiki summaries. They are identity-level abstractions — who I am, what I value, hard-won judgment. Ask: 'What has this work taught me about who I am?' Not: 'What happened today?'"
- Instruct the agent to write updated memory files directly to `memories/consolidated/` and `memories/core/` (overwriting or creating files as needed), following the existing YAML frontmatter schema (see `src/models/entity.py` for `MemoryFrontmatter`)
- Instruct the agent to finish by staging the written memories: `git add memories/` (wiki was already staged in Step 2)
- Instruct the agent to commit: `git commit -m "Session consolidation: <one-line description>"`
- If no significant patterns emerged (thin session), it's okay to write zero or one consolidated memory — quality over quantity

Do NOT include a transcript or ask the agent to summarize. The wiki diff is sufficient input.

### Step 4: Implement `_run_consolidation_agent()` and `run_wiki_consolidation()` in `entity_shutdown.py`

**Internal async function** (testable in isolation):
```
async def _run_consolidation_agent(entity_dir: Path, prompt: str) -> dict:
```

Uses `ClaudeSDKClient` following `src/orchestrator/agent.py` pattern:
```python
options = ClaudeAgentOptions(
    cwd=str(entity_dir),
    permission_mode="bypassPermissions",
    max_turns=50,
)
async with ClaudeSDKClient(options=options) as client:
    await client.query(prompt)
    async for message in client.receive_response():
        if isinstance(message, ResultMessage):
            ...
```

Returns `{"success": bool, "session_id": str | None, "error": str | None}`.

**Public sync function**:
```
# Chunk: docs/chunks/entity_shutdown_wiki - Wiki-based consolidation pipeline
def run_wiki_consolidation(
    entity_name: str,
    entity_dir: Path,
    project_dir: Path,
) -> dict:
```

1. Call `extract_wiki_diff(entity_dir)` → `wiki_diff`
2. If `wiki_diff` is `None`: legacy entity leaked into here — raise `ValueError`
3. If `wiki_diff == ""`: no changes, return `{"journals_added": 0, "consolidated": 0, "core": 0, "skipped": "no wiki changes"}`
4. Build prompt: `_build_consolidation_prompt(entity_name, wiki_diff)`
5. `_snapshot_tiers(entity_dir)` — reuse existing snapshot helper for rollback safety
6. `asyncio.run(_run_consolidation_agent(entity_dir, prompt))`
7. On failure: log error and return summary with `"error"` key (do NOT raise — caller should report but not crash)
8. Read back the consolidated/core memory counts from disk (for reporting)
9. Return `{"journals_added": <diff_line_count>, "consolidated": M, "core": K, ...}`

Import note: `from claude_agent_sdk import ClaudeSDKClient` is already imported in the project (see `src/orchestrator/agent.py`). Add guarded import similar to the existing `anthropic` guard.

### Step 5: Add `run_shutdown()` dispatcher in `entity_shutdown.py`

```
# Chunk: docs/chunks/entity_shutdown_wiki - Shutdown dispatcher (wiki vs legacy)
def run_shutdown(
    entity_name: str,
    project_dir: Path,
    extracted_memories_json: str | None = None,
    api_key: str | None = None,
    decay_config: DecayConfig | None = None,
) -> dict:
```

Logic:
```
entities = Entities(project_dir)
if entities.has_wiki(entity_name):
    entity_dir = entities.entity_dir(entity_name)
    return run_wiki_consolidation(entity_name, entity_dir, project_dir)
else:
    if not extracted_memories_json:
        raise ValueError(
            f"Entity '{entity_name}' is a legacy entity (no wiki/). "
            "Provide --memories-file with extracted memories."
        )
    return run_consolidation(entity_name, extracted_memories_json, project_dir, api_key, decay_config)
```

This preserves `run_consolidation()` unchanged — existing callers are unaffected.

### Step 6: Update `cli/entity.py` `shutdown` command

The `shutdown` command currently requires `--memories-file`. Update it to:

1. Make `--memories-file` optional (`required=False`, `default=None`)
2. After entity validation, import and call `run_shutdown()` instead of `run_consolidation()`
3. `run_shutdown()` internally handles the wiki vs. legacy dispatch and raises `ValueError` if `--memories-file` is missing for a legacy entity
4. Catch `ValueError` and surface as `click.ClickException` (same as current pattern)
5. Update the `click.echo` summary to handle the wiki pipeline's summary dict (which may omit `journals_consolidated` key)

Add backreference comment:
```python
# Chunk: docs/chunks/entity_shutdown_wiki - Wiki-aware shutdown routing
```

### Step 7: Update `entity-shutdown.md.jinja2` skill template

Replace the current fixed 5-step flow with a branching flow:

**Step 1** (unchanged): Identify the entity. Run `ve entity list --project-dir .` to verify.

**Step 2 (NEW)**: Check entity type:
```bash
ls .entities/<entity_name>/wiki/ 2>/dev/null && echo "WIKI_ENTITY" || echo "LEGACY_ENTITY"
```

**If WIKI entity** — skip manual extraction:
```
### Step 3 (Wiki path): Run shutdown

Your wiki maintained session knowledge in real time. The shutdown command will
diff the wiki against the last commit — these diffs ARE the journal entries.

Run:
```bash
ve entity shutdown <entity_name>
```

This will:
1. Diff your wiki vs. the last commit (mechanical — no LLM)
2. Launch a consolidation session to merge changes into cross-session patterns
3. Commit all changes to the entity repo
```

**If LEGACY entity** — keep current Steps 2–4 (extract memories, write temp file, run with `--memories-file`).

**Step 4/5 (both paths)**: Report results.

Include `{% raw %}...{% endraw %}` wrapping to match the template's existing Jinja2 escaping convention.

### Step 8: Run tests and verify no regressions

```bash
uv run pytest tests/ -x
```

Confirm:
- All new tests pass
- All existing entity tests pass (legacy pipeline unchanged)
- `uv run ve entity shutdown` CLI help text reflects optional `--memories-file`

## Dependencies

- `entity_wiki_schema` (ACTIVE): provides `entities.has_wiki()` — already committed per chunk GOAL.md code_references
- `entity_startup_wiki` (ACTIVE): provides `Entities.has_wiki()` — same
- `claude_agent_sdk` package: already a project dependency (used in `src/orchestrator/agent.py`)

## Risks and Open Questions

- **Agent SDK session from within a Claude session**: `ve entity shutdown` is called from within `/entity-shutdown` (a slash command in a running Claude session). The Agent SDK spawns a separate `claude` subprocess. This should work (it's a new process, not a nested SDK call), but warrants testing in the actual `ve entity claude` flow.
- **First session / no prior commit**: If the entity repo was just created and has no commits, `git diff HEAD` fails. The `extract_wiki_diff()` implementation handles this by returning `""` (skip consolidation). This is the correct behavior for a brand-new entity.
- **Long consolidation sessions**: The Agent SDK session has no arbitrary timeout (`max_turns=50` is the only bound). For entities with large wikis and many memory files, consolidation may take time. This is intentional — reliability over speed.
- **Memory file format**: The consolidation agent writes memory files directly. It must follow the YAML frontmatter schema (`MemoryFrontmatter` in `src/models/entity.py`). The prompt must include sufficient schema guidance or a reference to an existing memory file for the agent to follow.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?
-->
