<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a documentation-focused chunk that restores chunk backreferences to source
code. The approach is:

1. **Git archaeology**: Extract all `# Chunk:` references removed in commit 9ef703f
2. **Filter candidates**: Remove references to chunks that no longer exist, have
   non-ACTIVE status, or where the chunk name has no corresponding directory in
   `docs/chunks/`
3. **Value assessment**: For each remaining candidate, evaluate whether it adds
   meaningful context beyond the subsystem reference already present
4. **Selective restoration**: Add back high-value chunk references alongside
   existing subsystem references, with updated descriptions that reflect current
   understanding
5. **Documentation**: Record which references were restored vs intentionally skipped

No new tests are needed - this is a documentation restoration task. The success
criterion "Tests pass" refers to existing tests continuing to pass after the
backreference comments are modified.

The code_paths in GOAL.md are placeholders since the actual files touched depend
on the archaeology results. The primary files are those in `src/` and `tests/`
that had chunk references converted to subsystem references.

## Subsystem Considerations

This chunk restores chunk backreferences to code that is governed by subsystems.
The relevant subsystem is:

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk documents code that
  implements the workflow artifacts subsystem. Chunk references are being added
  *alongside* existing subsystem references, not replacing them. The subsystem
  reference provides coarse-grained context (what pattern), while chunk references
  provide fine-grained traceability (what work created/modified it).

## Sequence

### Step 1: Extract candidate references from git archaeology

Run `git diff 9ef703f^..9ef703f` to extract all `# Chunk:` references that were
removed during the migration. Parse these into a structured format:
- File path
- Line context (what symbol/function/class it documented)
- Chunk name
- Original description

Store this as a working list for evaluation.

### Step 2: Filter to restorable chunks

For each candidate, check:
1. Does `docs/chunks/<chunk_name>/` exist?
2. Is the chunk status ACTIVE? (Skip HISTORICAL, SUPERSEDED)

Create two lists:
- **Restorable**: Chunk exists and is ACTIVE
- **Not restorable**: Chunk doesn't exist or has non-ACTIVE status

Document the "not restorable" list with reasons for the final archaeology record.

### Step 3: Categorize by file and assess value

Group restorable candidates by file. For each file:
1. Read current content to see existing subsystem references
2. For each candidate chunk reference, assess:
   - Does this chunk add context beyond the subsystem? (e.g., "ordering_active_only"
     adds "status-aware tip filtering" which is more specific than "Workflow
     artifact lifecycle")
   - Is the chunk significant work? (Feature additions > single-line fixes)

Categorize each as:
- **High value**: Adds meaningful specific context
- **Low value**: Redundant with subsystem or trivial work

### Step 4: Restore high-value references

For each high-value reference:
1. Read the chunk's GOAL.md to understand the work
2. Craft an updated description that reflects current understanding (the original
   descriptions were sometimes vague like "Initial chunk management")
3. Add the `# Chunk:` comment alongside the existing `# Subsystem:` comment

Placement guidelines:
- Module-level chunk refs go with module-level subsystem refs
- Class/method level refs go near the symbol they document
- Order: Subsystem first, then Chunk (subsystem is coarser grain)

### Step 5: Run tests

Run `uv run pytest tests/` to verify all tests pass. The backreference changes
are comments-only and should not affect behavior.

### Step 6: Document decisions in this plan

Update the Deviations section with:
- Summary of references restored (count, files)
- Summary of references intentionally skipped (count, reasons)
- Notable decisions made during value assessment

## Dependencies

None. The git history and chunk documentation already exist.

## Risks and Open Questions

1. **Value assessment is subjective**: Different evaluators might categorize
   references differently. The plan mitigates this by documenting decisions in
   the Deviations section for future archaeology.

2. **Description drift**: Original descriptions may no longer match current
   understanding. This is addressed by updating descriptions during restoration
   rather than preserving original text verbatim.

3. **Volume of candidates**: With 674 references removed, manual evaluation could
   be time-consuming. The filtering steps (chunk exists + ACTIVE status) will
   significantly reduce the candidate pool. Initial archaeology shows ~90 unique
   chunks were referenced, of which ~87 are restorable (exist and ACTIVE).

## Deviations

### Implementation Summary

**Approach change**: Instead of restoring per-symbol chunk references (which would
restore 600+ references), we focused on **module-level chunk references** that
identify distinct features. This provides meaningful traceability without the
clutter of per-function annotations.

### References Restored (81 total: 15 in source, 66 in tests)

| File | Chunks Restored | Rationale |
|------|-----------------|-----------|
| `src/chunks.py` | `symbolic_code_refs`, `narrative_consolidation`, `cluster_prefix_suggest` | Distinct features not covered by "workflow_artifacts" subsystem |
| `src/models.py` | `symbolic_code_refs`, `bug_type_field`, `friction_template_and_cli` | Specific model additions with behavioral significance |
| `src/artifact_ordering.py` | `ordering_active_only`, `external_chunk_causal` | Distinct features beyond core ordering |
| `src/cluster_analysis.py` | `cluster_subsystem_prompt` | Cluster warnings are a distinct feature |
| `src/external_resolve.py` | `external_resolve_all_types` | Multi-type support was a distinct expansion |
| `src/orchestrator/agent.py` | `orch_question_forward`, `orch_sandbox_enforcement` | Distinct safety and routing features |
| `src/orchestrator/api.py` | `orch_dashboard`, `orch_conflict_oracle` | User-facing features beyond core API |
| `src/orchestrator/models.py` | `orch_attention_queue` | Attention queue is a distinct feature |

**Test files** (24 files, 66 refs): Key test files received chunk references to provide
debugging context. Categories:

| Category | Files | Chunks |
|----------|-------|--------|
| Orchestrator tests | 10 | `orch_foundation`, `orch_scheduling`, `orch_conflict_oracle`, `orch_dashboard`, etc. |
| Task-aware tests | 8 | `task_aware_*`, `taskdir_context_cmds`, `task_list_proposed`, etc. |
| Feature tests | 6 | `symbolic_code_refs`, `cross_repo_schemas`, `task_init_scaffolding`, etc. |

### References Intentionally Not Restored (~540)

| Category | Count | Reason |
|----------|-------|--------|
| Per-symbol refs | ~500 | Each function/class had its own chunk ref; subsystem provides sufficient context |
| Generic descriptions | ~50 | Refs like "Initial chunk management" or "Core class" - covered by subsystem |
| Import/utility refs | ~30 | Refs about importing or consolidating utilities - implementation details |
| Redundant module refs | ~20 | Multiple refs to same chunk within one file |
| SUPERSEDED chunks | 4 | `proposed_chunks_frontmatter`, `subsystem_template`, `narrative_backreference_support`, `coderef_format_prompting` |
| NOT_EXISTS chunks | 1 | `ve_sync_foundation` |

### Notable Decisions

1. **Updated descriptions**: Original descriptions like "Backreference scanning patterns"
   were replaced with feature-focused descriptions like "Chunk-to-narrative consolidation
   workflow" that better communicate the chunk's purpose.

2. **Module-level only**: We only restored module-level (top-of-file) chunk references.
   Per-symbol references (e.g., "# Chunk: at each function") were not restored because:
   - They created visual clutter (some files had 20+ identical chunk refs)
   - The module-level reference provides the same traceability
   - Subsystem references already document the architectural context

3. **Orchestrator selective**: For orchestrator files, we focused on features with
   user-visible behavioral impact (dashboard, conflict detection, question forwarding,
   sandbox enforcement) rather than internal implementation chunks (scheduling, state).

4. **Test file restoration**: Test files received chunk references to provide context
   when debugging failing tests. Knowing which chunk created a test helps determine
   whether a failing test reveals a bug or is itself outdated. Added 66 chunk
   references across 24 test files, focusing on files that test specific features
   (orchestrator, task-aware commands, friction, symbols, etc.).