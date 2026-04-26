---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models/chunk.py
- src/models/__init__.py
- src/templates/commands/chunk-complete.md.jinja2
- src/templates/chunk/GOAL.md.jinja2
- tests/test_models.py
- tests/test_reviewer_decision_create.py
code_references:
  - ref: src/models/chunk.py#ChunkFrontmatter
    implements: "Removed bug_type field and added ConfigDict(extra='ignore') for backward compatibility with existing GOAL.md files"
  - ref: src/templates/commands/chunk-complete.md.jinja2
    implements: "Replaced bug_type-based status routing with retrospective framing rewrite (step 11), intent test (step 12), and HISTORICAL deletion prompt (step 13)"
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "Removed bug_type from chunk GOAL.md frontmatter template and its documentation block"
  - ref: tests/test_models.py#TestChunkFrontmatterBugTypeRemoved
    implements: "Tests verifying bug_type is no longer a model field and is silently ignored in existing frontmatter"
narrative: intent_ownership
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- intent_principles
---

# Chunk Goal

## Minor Goal

The `/chunk-complete` skill enforces principle 3 (present-tense GOAL.md) and principle 2 (intent-bearing only) at completion. The agent rewrites retrospective framing itself, applies the intent test to choose ACTIVE vs HISTORICAL, and prompts the operator to delete chunks that land HISTORICAL with no ongoing intent. The `bug_type` field no longer exists in the schema; `ChunkFrontmatter` silently ignores it in existing GOAL.md files via `ConfigDict(extra="ignore")`.

Behavior at completion, before any status transition:

1. **Re-read GOAL.md.** Detect retrospective framing tells: `Currently,`, `was`, `we added`, `this chunk fixes`, `the fix:`, `will change to`. The agent rewrites offending passages into present-tense descriptions of how the system works, using the implemented code as the source of truth. Proceed silently when the rewrite is mechanical (changing `we added X` to `X exists`; replacing `Currently the system does Y, we'll change it to Z` with `The system does Z because...`). Escalate to the operator only when (a) the goal asserts something the agent can't reconcile against the current code, (b) the rewrite would materially change the goal's meaning rather than just its tense, or (c) the agent's confidence in the rewrite is low. When escalating, present a candidate rewrite alongside the specific reason the agent couldn't land it on its own.

2. **Apply the intent test the same way `/chunk-create` (chunk 2) does.** Does this code need to remember why it exists? If yes → status: ACTIVE. If no → status: HISTORICAL.

3. **When the agent decides HISTORICAL, prompt the operator.** *"This chunk has no ongoing intent to remember — its job was to coordinate execution. Consider deleting it. The work is preserved in git; the chunk no longer earns its keep in `docs/chunks/`."* Operator chooses delete or keep. If keep, the chunk lands HISTORICAL with a brief note in its goal explaining why it was retained.

4. **`bug_type` is collapsed.** Implementation-bug work doesn't flow through the chunk system at all (handled by chunk 2's gate); semantic-bug work is just intent-bearing work that happens to start from a bug. The `BugType` enum and `bug_type` field are absent from `src/models/chunk.py` (`ChunkFrontmatter`), the GOAL.md template, and all skill templates.

The deletion prompt is the load-bearing piece: it lets chunks function as coordination mechanisms for orchestrator execution without permanently bloating the chunk corpus. A pure-execution chunk does its job, sequences alongside intent-bearing work, then gets cleaned up. The principle "chunks exist for intent-bearing work" stays a true description of what survives in `docs/chunks/`.

## Success Criteria

1. `src/templates/commands/chunk-complete.md.jinja2` instructs the agent to detect retrospective framing tells and rewrite them.
2. The skill instructs the agent to proceed silently for mechanical rewrites and to escalate only on the three named cases (irreconcilable assertion / meaning change / low confidence), with a candidate rewrite when escalating.
3. The skill instructs the agent to apply the intent test to choose between ACTIVE and HISTORICAL.
4. When the agent decides HISTORICAL, the skill instructs it to prompt the operator to consider deleting the chunk.
5. The `bug_type` field does not exist in `src/models/chunk.py` (`ChunkFrontmatter`; no `BugType` enum), in `src/templates/chunk/GOAL.md.jinja2` frontmatter, in the chunk-complete skill template, or in any other code path or skill.
6. Tests verify that `bug_type` is no longer a model field and that existing frontmatter with `bug_type: null` parses cleanly.
7. `uv run ve init` runs cleanly.
8. `uv run pytest tests/` passes.

## Out of Scope

- Auditing existing ACTIVE chunks for retrospective framing (chunk 6).
- The intent-test gate at `/chunk-create` (chunk 2).
- Changing how SUPERSEDED is handled (chunks 5 and 7).
- Migrating existing chunks that carry `bug_type` values: the field disappears, but no chunk's status changes as a result of that. If the field's removal causes any existing chunk to fail validation, document the chunks affected and surface to operator.