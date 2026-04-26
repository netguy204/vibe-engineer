# Implementation Plan

## Approach

Land the seed doc and propagate the new status taxonomy through three layers, in inside-out order so each layer rests on a working foundation:

1. **Runtime** — Add `COMPOSITE` to `ChunkStatus` and the state machine. Update every code path that reasons about post-IMPLEMENTING statuses. SUPERSEDED stays in the runtime (12 existing chunks still use it; retirement is narrative chunk 7).
2. **Tests** — Extend state-machine tests to cover the new transitions; add an inject-validation test for COMPOSITE parallel to the existing SUPERSEDED case; verify nothing else regresses.
3. **Documentation** — Create `docs/trunk/CHUNKS.md` (verbatim text from GOAL.md), update the status table in `src/templates/chunk/GOAL.md.jinja2`, mirror the change in `docs/trunk/SPEC.md`, add the cross-reference in `docs/trunk/ARTIFACTS.md`.

The runtime extension is conservative: COMPOSITE is added everywhere SUPERSEDED is referenced, treated equivalently (settled, post-IMPLEMENTING, can't be re-injected). Removing SUPERSEDED is explicitly the work of narrative chunk 7 and is out of scope here.

After all edits, run `uv run ve init` to re-render templates from `src/templates/`, then `uv run pytest tests/` to catch regressions.

## Subsystem Considerations

- **`docs/subsystems/template_system`** (STABLE): This chunk USES the subsystem. The edit to `src/templates/chunk/GOAL.md.jinja2` is content-only (the STATUS VALUES comment block); no change to the rendering pipeline, no new conditional rendering, no new variables. Re-running `uv run ve init` regenerates downstream artifacts and is the standard verification step.
- **`docs/subsystems/workflow_artifacts`** (STABLE per `src/models/chunk.py:2`): This chunk USES the subsystem. The `ChunkStatus` enum addition is a schema extension, not a structural change to the workflow artifact pattern.

No new subsystems emerge from this work; no deviations discovered.

## State machine transitions for COMPOSITE

The new `VALID_CHUNK_TRANSITIONS` table (only changed entries shown):

```python
ChunkStatus.IMPLEMENTING: {ChunkStatus.ACTIVE, ChunkStatus.COMPOSITE, ChunkStatus.HISTORICAL},
ChunkStatus.ACTIVE: {ChunkStatus.SUPERSEDED, ChunkStatus.COMPOSITE, ChunkStatus.HISTORICAL},
ChunkStatus.COMPOSITE: {ChunkStatus.ACTIVE, ChunkStatus.HISTORICAL},
ChunkStatus.SUPERSEDED: {ChunkStatus.HISTORICAL},  # unchanged; SUPERSEDED is being retired
```

Rationale:
- `IMPLEMENTING → COMPOSITE` allowed: a chunk may complete already knowing it co-owns intent with an existing ACTIVE chunk.
- `ACTIVE → COMPOSITE`: when a new sibling chunk creates intent overlap, both can move to COMPOSITE.
- `COMPOSITE → ACTIVE`: if a co-owner is later HISTORICAL'd or merged, the remaining chunk regains sole ownership.
- `COMPOSITE → HISTORICAL`: terminal abandonment.
- No `COMPOSITE → SUPERSEDED` transition — SUPERSEDED is being retired and would conflate cleanly with HISTORICAL.

## Sequence

### Step 1: Add COMPOSITE to the runtime enum and state machine

File: `src/models/chunk.py`

- Insert `COMPOSITE = "COMPOSITE"` in `ChunkStatus` between ACTIVE and SUPERSEDED with comment: `# Shares ownership of intent with other chunks; must be read alongside co-owners`
- Update `VALID_CHUNK_TRANSITIONS` per the table above.
- Add a `# Chunk: docs/chunks/intent_principles - COMPOSITE status added` backreference comment above the enum.

### Step 2: Extend `chunk_validation.py` to treat COMPOSITE as terminal-for-injection

File: `src/chunk_validation.py:461`

Change `(ChunkStatus.SUPERSEDED, ChunkStatus.HISTORICAL)` to `(ChunkStatus.SUPERSEDED, ChunkStatus.COMPOSITE, ChunkStatus.HISTORICAL)`. COMPOSITE is a settled status — chunks already in COMPOSITE can't be re-injected for implementation.

### Step 3: Update CLI help text

File: `src/cli/chunk.py:270`

Change `"Valid statuses: FUTURE, IMPLEMENTING, ACTIVE, SUPERSEDED, HISTORICAL"` to `"Valid statuses: FUTURE, IMPLEMENTING, ACTIVE, COMPOSITE, SUPERSEDED, HISTORICAL"`.

### Step 4: Update comments in `src/chunks.py`

File: `src/chunks.py:209,214`

Add COMPOSITE to the list of statuses being filtered out:
- Line 209 comment: `Returns the first IMPLEMENTING chunk in causal order, ignoring FUTURE/ACTIVE/COMPOSITE/SUPERSEDED/HISTORICAL`
- Line 214 docstring: `ignoring FUTURE, ACTIVE, COMPOSITE, SUPERSEDED, and HISTORICAL chunks.`

### Step 5: Verify activation.py needs no manual change

File: `src/orchestrator/activation.py:44-55`

`_is_post_implementing` derives reachable post-IMPLEMENTING statuses dynamically from `VALID_CHUNK_TRANSITIONS`. With the Step 1 transition table change, `IMPLEMENTING → COMPOSITE` is reachable, so `_is_post_implementing(COMPOSITE)` returns `True` automatically. **No edit needed**, but update the docstring comments at lines 47 and 63 to mention COMPOSITE.

### Step 6: Extend state-machine tests

File: `tests/test_state_machine.py`

- The error-message check at line 120 (`assert "SUPERSEDED" in error_msg or "HISTORICAL" in error_msg`) should also accept "COMPOSITE". Update to accept any of the three.
- Add tests:
  - `test_active_to_composite_allowed` — `sm.validate_transition(ACTIVE, COMPOSITE)` doesn't raise
  - `test_composite_to_active_allowed` — `sm.validate_transition(COMPOSITE, ACTIVE)` doesn't raise
  - `test_composite_to_historical_allowed` — terminal transition
  - `test_implementing_to_composite_allowed` — completion-time direct transition

### Step 7: Extend inject-validation tests

File: `tests/test_chunk_validate_inject.py`

After the existing SUPERSEDED test (line 206-222), add a parallel test:
- `test_composite_chunk_cannot_be_injected` — write a chunk with `status: COMPOSITE`, validate, assert error containing "terminal status" or "COMPOSITE".

### Step 8: Create `docs/trunk/CHUNKS.md`

Copy the four-principle text from `docs/chunks/intent_principles/GOAL.md` (the "The four principles (final wording — land verbatim)" subsection) into a new `docs/trunk/CHUNKS.md`. Wrap with a brief preamble linking it to the project goal.

Do not add headings beyond what the principles already structure. The doc is a punchy reference, not an essay — fits on one screen.

### Step 9: Update the template's STATUS VALUES block

File: `src/templates/chunk/GOAL.md.jinja2:29-34`

Replace the existing block with the new taxonomy:

```
STATUS VALUES (status answers: how much of the intent does this chunk own?):
- FUTURE: Not yet owned. Queued for later.
- IMPLEMENTING: Being taken into ownership. At most one per worktree.
- ACTIVE: Fully owns the intent that governs the code.
- COMPOSITE: Shares ownership with other chunks. Must be read alongside its co-owners.
- HISTORICAL: No longer owns intent. Kept for archaeological context.

See docs/trunk/CHUNKS.md for the full principle.
```

Note: SUPERSEDED is intentionally omitted from the documented taxonomy even though the runtime still accepts it. Twelve existing chunks still carry it; the migration chunk in this narrative will move them off, and a final chunk will retire SUPERSEDED from the runtime.

### Step 10: Mirror the change in SPEC.md

File: `docs/trunk/SPEC.md:214-219`

Replace the existing block with the same five-status taxonomy (text matching CHUNKS.md). Drop "or recently-merged work" from the ACTIVE description. Add a leading line: `These statuses answer a single question — how much of the intent does this chunk own? See docs/trunk/CHUNKS.md.`

### Step 11: Add cross-reference in ARTIFACTS.md

File: `docs/trunk/ARTIFACTS.md`

Add a one-line cross-reference at the top of the file or near the existing "Beyond chunks (the core unit of work)" preamble:

```markdown
> Before working with chunks, read [docs/trunk/CHUNKS.md](CHUNKS.md) — the canonical statement of what chunks are for and how their status is interpreted.
```

### Step 12: Re-render templates and verify

```bash
uv run ve init
```

Verify rendered artifacts re-render cleanly. The template change is comment-only inside the Jinja file, so the only visible diff in rendered output should be in chunk GOAL.md template content — verify no template syntax errors.

### Step 13: Run the test suite

```bash
uv run pytest tests/
```

Address any failures. New test additions should pass; pre-existing tests should continue to pass. If any test fails for reasons unrelated to status taxonomy, investigate before silencing.

### Step 14: Update GOAL.md frontmatter

After implementation, update `docs/chunks/intent_principles/GOAL.md` frontmatter:
- `code_paths`: list every file touched
- (`code_references` will be populated at /chunk-complete)

---

**Backreference comments**: Add `# Chunk: docs/chunks/intent_principles - <brief description>` comments to:
- The `ChunkStatus` enum in `src/models/chunk.py` (above the class)
- The `VALID_CHUNK_TRANSITIONS` dict in `src/models/chunk.py` (above the dict)

These two are the canonical homes of the runtime taxonomy. Other touched files (chunk_validation.py, chunks.py comments, cli/chunk.py help text, activation.py docstrings) are mechanical follow-on edits, not architectural — they don't need backreferences.

## Risks and Open Questions

- **Pre-existing untracked files in the working tree.** `git status` at session start showed several unrelated unstaged/untracked files (site changes, documentor entity, pip artifacts in src/). The previous chunk-creation commit accidentally bundled `.entities/documentor` and `.gitmodules`. For this implementation, stage **only** the files this plan touches. Do not `git add -A` or `git add .`.
- **Test coverage may surface a hidden code path.** Adding COMPOSITE could trip a test that hard-codes the set of valid statuses. The plan explicitly extends `test_state_machine.py:120` and `test_chunk_validate_inject.py`, but other tests (e.g., `test_models_chunk.py` which iterates `for status in ChunkStatus`) may need adjustment. Treat any unexpected failure as a signal that a code path needs to handle COMPOSITE, not as a test to silence.
- **The verification pass and intent-test gate are out of scope.** When implementing CHUNKS.md and the principle of present-tense framing, resist the urge to also update `/chunk-create` or `/chunk-complete`. Those are narrative chunks 2 and 3.
- **Doc-vs-runtime divergence on SUPERSEDED.** CHUNKS.md and the SPEC.md table do not mention SUPERSEDED, even though the runtime still accepts it. This is intentional — SUPERSEDED is a transition artifact that gets retired by chunk 7 of the narrative. Anyone who reads the doc and sees an existing SUPERSEDED chunk in the corpus may be momentarily confused; this is acceptable for the migration window.

## Deviations

None — implementation followed the plan as written. The reviewer caught one missed location (`docs/trunk/SPEC.md:200` YAML schema example) that the plan should have called out explicitly; it has been corrected in iteration 1.
