---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
- src/entity_shutdown.py
- src/cli/entity.py
- src/templates/commands/entity-shutdown.md.jinja2
code_references: []
narrative: null
investigation: entity_wiki_memory
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_wiki_schema
- entity_startup_wiki
created_after:
- board_watch_reconnect_fix
---
# Chunk Goal

## Minor Goal

Revise the entity-shutdown skill to use the new wiki-based pipeline: mechanical git diff for journal creation, then Agent SDK consolidation for memory synthesis, then commit to entity repo. This eliminates the fragile timeout-based journal extraction that currently fails silently.

### Context for implementing agent

**Read the investigation first**: `docs/investigations/entity_wiki_memory/OVERVIEW.md` — especially the "Shutdown Sequence" section in the Appendix and the H1 exploration log showing how wiki diffs produce journal entries.

**The big picture**: The wiki maintained during the session (by chunk 3's startup contract) is the source of truth for what the entity learned. At shutdown, `git diff` mechanically extracts what changed — these diffs ARE the journal entries. Then an Agent SDK session (not the Messages API, not a CLI prompt) performs the higher-value consolidation work: merging concrete session changes into abstract cross-session patterns and distilling identity-level core memories. This replaces the current fragile pipeline entirely for wiki-based entities.

**Existing shutdown code** — this is what you're replacing:
- `src/entity_shutdown.py` (721 lines) — the current pipeline. Key functions:
  - `run_consolidation()` — main orchestration: calls Anthropic Messages API for both memory extraction and consolidation
  - `extract_memories_from_transcript()` — uses `anthropic.Anthropic` client to extract memories from session transcript (this is the step that times out)
  - `shutdown_from_transcript()` — fallback when the in-session extraction fails
  - Uses `anthropic` SDK directly with API key — costs API rates, no Claude Max pricing
  - Two API calls: extraction (max_tokens: 4096) then consolidation (max_tokens: 8192)
- `src/templates/commands/entity-shutdown.md.jinja2` — the `/entity-shutdown` skill. Prompts the entity to extract memories as JSON with categories (correction, skill, domain, confirmation, coordination, autonomy), then calls `ve entity shutdown` CLI
- `src/cli/entity.py` — `ve entity shutdown <name>` command (line ~171), also `ve entity claude` which wraps the full lifecycle with a configurable 300s timeout for the consolidation step

**Agent SDK integration exists in the codebase**: `src/orchestrator/agent.py` (956 lines) already uses `claude_agent_sdk` with `ClaudeSDKClient`, `@tool` decorator, pre/post-tool hooks, and MCP server integration. Use this as a reference for how to launch Agent SDK sessions in this project. The Agent SDK runs via Claude Max (no API key costs) and has no arbitrary timeout — the session runs to completion.

**Current problem**: When shutting down an entity via `ve entity claude`, the journal writing phase often exceeds the shutdown timeout and falls back to transcript scanning. This fallback is unreliable — it frequently produces zero journal entries. The deeper issue is that consolidation runs as a prompted task inside the restored CLI session with limited observability.

**New pipeline**:
```
1. git diff wiki vs last commit → these diffs ARE the journal entries (mechanical, no LLM)
2. Agent SDK consolidation (agentic, no timeout):
   - reads: wiki diffs + existing consolidated memories
   - produces: updated consolidated memories (abstract cross-session patterns)
3. Agent SDK core memory update:
   - reads: updated consolidated memories
   - produces: updated core memories (identity-level — who I am, what I value)
4. git commit all changes to entity repo
```

**Key insight from investigation**: Wiki diffs from a real session produced 137 lines of structured, contextualized journal entries — superior to LLM-extracted journals because knowledge is already structured and positioned relative to existing knowledge. Journal creation becomes zero-cost.

**Core memory abstraction level**: Core memories are NOT wiki summaries. They are highly abstracted derivations — internalized principles, hard-won judgment, aesthetic preferences, domain intuitions. The consolidation prompt must target: "What has this work taught you about who you are and what matters?" — not "Summarize what happened."

### What to build

1. **Wiki diff → journal entries**: At shutdown, run `git diff` on the entity's wiki/ directory against the last commit. Parse the diff into per-file change summaries. These become journal entries without any LLM processing.

2. **Agent SDK consolidation**: Launch a Claude Agent SDK session (not the Messages API, not a CLI prompt) that:
   - Receives the wiki diffs as input
   - Reads existing consolidated memories from `memories/consolidated/`
   - Produces updated consolidated memories that merge concrete session changes into abstract cross-session patterns
   - Runs to completion with no timeout — the Agent SDK session handles its own lifecycle
   - Uses Claude Max pricing (via Agent SDK) instead of API key rates

3. **Agent SDK core memory update**: Same Agent SDK session (or a second pass) that:
   - Reads updated consolidated memories
   - Reads existing core memories from `memories/core/`
   - Produces updated core memories targeting the identity/values abstraction level
   - Prompt: "Based on these consolidated patterns, what has this work taught you about who you are, what you value, and what you've learned? Write core memories that would help you quickly re-establish your identity and judgment in a new session."

4. **Commit to entity repo**: After consolidation, `git add -A && git commit` in the entity repo with a session summary message.

5. **Backward compatibility**: Legacy entities (no wiki) should continue using the current shutdown pipeline.

### Design constraints

- The Agent SDK is the consolidation runtime — not the Messages API, not a CLI prompt
- No arbitrary timeouts — the consolidation runs to completion
- Core memories must be identity/values, not summaries — encode this in the prompt
- The diff-to-journal transformation is mechanical (no LLM) — this is a key reliability improvement
- Must handle the case where wiki has no changes (entity didn't update wiki during session)
- Entity repo commit should include both wiki changes and memory tier updates in a single commit

## Success Criteria

- Wiki diff correctly produces structured journal entries from real wiki changes
- Agent SDK consolidation session launches and completes without timeout
- Consolidated memories reflect abstract cross-session patterns, not raw session events
- Core memories read as identity/values statements, not factual summaries
- Entity repo committed with all changes after consolidation
- Legacy entities without wiki/ use the current shutdown pipeline
- No data loss — the fragile transcript scanning fallback is eliminated for wiki entities
- Tests cover: wiki with changes, wiki without changes, legacy entity, consolidation output quality
