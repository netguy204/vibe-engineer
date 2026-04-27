
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk rewrites the `/chunk-complete` skill template (`src/templates/commands/chunk-complete.md.jinja2`) to replace the `bug_type`-based status routing with an intent-test-based approach, and removes the `bug_type` field from the schema and all code paths.

The work has two halves:

1. **Template rewrite** — Replace steps 2 (bug_type guidance for code_references) and 11 (bug_type-based status determination) with three new behaviors: retrospective-framing detection/rewrite, intent-test-based status routing (ACTIVE vs HISTORICAL), and a deletion prompt for HISTORICAL chunks.

2. **Schema cleanup** — Remove the `BugType` enum and `bug_type` field from `src/models/chunk.py`, the GOAL.md template, the `__init__.py` re-exports, and tests.

Per DEC-008 (Pydantic for frontmatter models), the schema change is straightforward: drop the field from `ChunkFrontmatter` and remove the enum. The field is optional with a default of `None`, so existing GOAL.md files that still carry `bug_type: null` will be handled gracefully by Pydantic (unknown fields are ignored by default, or we ensure the model allows extra fields during a transition period — but since all existing chunks use `bug_type: null`, removing it from the model should be clean).

Tests follow TESTING_PHILOSOPHY.md: we delete the trivial `TestChunkFrontmatterBugType` class (which tests Pydantic storage, not behavior) and add meaningful tests for the new behavior — specifically, that `ChunkFrontmatter` no longer accepts `bug_type` as a field, and that the GOAL.md template no longer contains it.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): This chunk IMPLEMENTS changes to the chunk completion workflow. The template being modified is a core artifact of this subsystem's lifecycle management.

## Sequence

### Step 1: Remove `BugType` enum and `bug_type` field from the model

Location: `src/models/chunk.py`

- Delete the `BugType` class (lines 36-45) and its backreference comment (line 35).
- Remove the `bug_type: BugType | None = None` field from `ChunkFrontmatter` (line 90).
- Remove the backreference comment `# Chunk: docs/chunks/bug_type_field - bug_type field added to ChunkFrontmatter model` (line 68).

Location: `src/models/__init__.py`

- Remove `BugType` from the import statement in the chunk domain section (line 77).
- Remove `"BugType"` from the `__all__` list (line 140).

### Step 2: Remove `bug_type` from the GOAL.md template

Location: `src/templates/chunk/GOAL.md.jinja2`

- Remove the `bug_type: null` line from the frontmatter block (line 11).
- Remove the entire `BUG_TYPE:` documentation section from the comment block (lines 136-147, the section starting with `BUG_TYPE:` and ending before `CHUNK ARTIFACTS:`).

### Step 3: Rewrite the chunk-complete skill template

Location: `src/templates/commands/chunk-complete.md.jinja2`

This is the core of the chunk. Replace the current steps 2 and 11 with the new intent-verification workflow. The new template flow is:

**Replace step 2's "Bug type guidance for code_references" block** (lines 88-95) with nothing — code references are always required under the new model (intent-less work doesn't flow through chunks at all).

**Replace step 11** (lines 136-155, the entire "Determine final status based on bug_type" section) with a new three-part completion verification:

**New step 11: Retrospective framing rewrite.**

Instruct the agent to re-read the chunk's GOAL.md and detect retrospective framing tells: `Currently,`, `was`, `we added`, `this chunk fixes`, `this chunk adds`, `the fix:`, `will change to`. The agent rewrites offending passages into present-tense descriptions of how the system works, using the implemented code as the source of truth.

- **Proceed silently** when the rewrite is mechanical (e.g., changing `we added X` to `X exists`; replacing `Currently the system does Y, we'll change it to Z` with `The system does Z because...`).
- **Escalate to the operator** only when: (a) the goal asserts something the agent can't reconcile against the current code, (b) the rewrite would materially change the goal's meaning rather than just its tense, or (c) the agent's confidence in the rewrite is low. When escalating, present a candidate rewrite alongside the specific reason the agent couldn't land it on its own.

Reference: docs/trunk/CHUNKS.md principle 3.

**New step 12: Apply the intent test.**

Instruct the agent to apply the intent test from docs/trunk/CHUNKS.md principle 2: *"Does this code need to remember why it exists?"*

- If yes → status: **ACTIVE** (or **COMPOSITE** if co-owning intent with peers).
- If no → status: **HISTORICAL**.

**New step 13: HISTORICAL deletion prompt.**

When the agent decides HISTORICAL, instruct it to prompt the operator:

> *"This chunk has no ongoing intent to remember — its job was to coordinate execution. Consider deleting it. The work is preserved in git; the chunk no longer earns its keep in `docs/chunks/`."*

- If the operator chooses **delete**: delete the chunk directory.
- If the operator chooses **keep**: land the chunk as HISTORICAL with a brief note in the goal explaining why it was retained.

**Renumber subsequent steps** (friction check becomes step 14, etc.).

After the status determination steps, **update the existing status-setting instruction** to use the determined status (ACTIVE, COMPOSITE, or HISTORICAL) instead of the old bug_type-based logic. Remove the comment block as before.

### Step 4: Remove `bug_type` tests and add replacement tests

Location: `tests/test_models.py`

- Delete the entire `TestChunkFrontmatterBugType` class (lines 413-471). These tests are trivial by TESTING_PHILOSOPHY.md standards — they test Pydantic storage, not behavior.
- Add a new test verifying that `bug_type` is no longer accepted as a field (Pydantic should reject it or ignore it — verify the expected behavior).

Location: `tests/test_reviewer_decision_create.py`

- Remove `bug_type: null` from all inline GOAL.md YAML frontmatter fixtures used in test helpers. There are ~9 occurrences where `bug_type: null` appears in test fixture YAML strings. Remove the line from each.

### Step 5: Handle existing chunks with `bug_type` in frontmatter

The `ChunkFrontmatter` Pydantic model uses `BaseModel` which by default rejects extra fields. When `bug_type` is removed from the model, any existing chunk GOAL.md that still has `bug_type: null` in its frontmatter will fail validation.

Two approaches:
- **Option A**: Add `model_config = ConfigDict(extra="ignore")` to `ChunkFrontmatter` so unknown fields are silently dropped. Check if the base `ArtifactManager` already handles this.
- **Option B**: Since all existing chunks have `bug_type: null` (the default), and the field is being removed, we can let validation fail and fix the chunks. But with 290 chunks containing the field, this is impractical in this chunk's scope.

**Decision**: Check the existing Pydantic model configuration. If extra fields are already ignored, no action needed. If not, add `model_config = ConfigDict(extra="ignore")` to `ChunkFrontmatter` so existing chunks parse cleanly. This is the pragmatic choice — the `bug_type: null` lines in existing GOAL.md files are inert and will be cleaned up organically as chunks are completed going forward.

### Step 6: Verify

- Run `uv run ve init` to re-render the templates and confirm no errors.
- Run `uv run pytest tests/` to confirm all tests pass.
- Manually verify the rendered `.agents/skills/chunk-complete/SKILL.md` contains the new intent-test workflow and no `bug_type` references.

## Dependencies

- `intent_principles` (ACTIVE) — docs/trunk/CHUNKS.md must exist with the four principles, which this chunk's template references. Already landed.

## Risks and Open Questions

- **Pydantic extra field handling**: If `ChunkFrontmatter` strict-rejects unknown fields, removing `bug_type` will break validation for all ~290 existing chunks that still have `bug_type: null` in their YAML. Step 5 addresses this — check the current model config and add `extra="ignore"` if needed.
- **Existing chunks with `bug_type: semantic` or `bug_type: implementation`**: Search confirms all existing chunks use `bug_type: null`. No migration needed for non-null values. The `bug_type_field` chunk itself (docs/chunks/bug_type_field/) has `bug_type: null` in its GOAL.md.
- **Template rendering with Jinja2**: The chunk-complete template uses conditional blocks (`{% if task_context %}`). The new steps must integrate cleanly with these conditionals, particularly the final commit step which is task-context-dependent.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->