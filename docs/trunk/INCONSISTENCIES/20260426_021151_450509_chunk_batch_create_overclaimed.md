---
discovered_by: audit batch 8i
discovered_at: 2026-04-26T02:11:51Z
severity: low
status: open
artifacts:
  - docs/chunks/chunk_batch_create/GOAL.md
  - src/templates/claude/CLAUDE.md.jinja2
---

## Claim

`docs/chunks/chunk_batch_create/GOAL.md` lists two CLAUDE.md-template success criteria:

> 5. CLAUDE.md template documents batch creation usage
> 6. CLAUDE.md template includes guidance to spawn sub-agents to refine goals in parallel when multiple chunks are created

## Reality

`src/templates/claude/CLAUDE.md.jinja2` does **not** mention batch chunk creation, the variadic `ve chunk create name1 name2 name3` syntax, or guidance to spawn sub-agents (Task tool) for parallel goal refinement after batch creation. Greps for `batch`, `multiple chunks`, `name1 name2`, and `sub-agent` against the template return no relevant matches in any chunk-creation context (only references to `/cluster-rename`, `/narrative-compact`, `/narrative-execute`, and the orchestrator subsystem).

The batch-creation documentation does exist, but it lives in `docs/trunk/ORCHESTRATOR.md` (lines 110-135 — section "Batch Creating Multiple Chunks"), which `code_references` correctly tracks. The CLAUDE.md template was never updated to point at it or to nudge agents toward sub-agent fan-out.

The CLI behavior itself (success criteria 1-4, 7) is implemented and tested:
- `src/cli/chunk.py#create` accepts variadic `short_names`.
- `src/cli/chunk.py#_start_task_chunks` handles task-directory batch mode.
- `tests/test_chunk_start.py#TestBatchCreation` covers batch behavior.

So this is a partial over-claim against the template-documentation half of the chunk's stated scope, not against the CLI half.

## Workaround

None applied this session — the audit veto rule fires when over-claim is detected, so no prose rewrite was attempted. The chunk's GOAL.md is left as-is; a follow-up chunk should either complete the template guidance or revise success criteria 5-6 to point at `docs/trunk/ORCHESTRATOR.md` as the documentation surface.

## Fix paths

1. **Add the missing guidance to the CLAUDE.md template.** A short subsection under "Available Commands" or "Creating Artifacts" mentioning the variadic syntax and recommending sub-agent fan-out for goal refinement would close criteria 5 and 6 with minimal scope.
2. **Revise success criteria 5-6** to acknowledge `docs/trunk/ORCHESTRATOR.md` as the canonical documentation surface for batch-creation guidance, if the project deems CLAUDE.md template the wrong place for this content.
