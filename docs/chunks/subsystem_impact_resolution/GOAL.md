---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/subsystems.py
- src/ve.py
- src/templates/commands/chunk-complete.md.jinja2
- tests/test_subsystem_overlap_logic.py
- tests/test_subsystem_overlap_cli.py
code_references:
- ref: src/subsystems.py#Subsystems::find_overlapping_subsystems
  implements: Business logic to find subsystems with code_references overlapping a
    chunk's changes
- ref: src/subsystems.py#Subsystems::_find_overlapping_refs
  implements: Helper method for hierarchical reference comparison using is_parent_of
- ref: src/ve.py#overlap
  implements: CLI command 've subsystem overlap <chunk_id>' that surfaces overlap
    detection
- ref: src/templates/commands/chunk-complete.md.jinja2
  implements: Workflow steps 8-10 for subsystem analysis during chunk completion
- ref: tests/test_subsystem_overlap_logic.py
  implements: Tests for find_overlapping_subsystems business logic
- ref: tests/test_subsystem_overlap_cli.py
  implements: Tests for ve subsystem overlap CLI command
narrative: subsystem_documentation
subsystems: []
created_after:
- spec_docs_update
---

# Chunk Goal

## Minor Goal

Integrate subsystem code references into the chunk completion workflow so that changes touching subsystem-tracked code automatically surface for documentation review.

When a chunk is completed, its code changes may overlap with files or symbols tracked by subsystems. Without explicit detection, subsystem documentation can drift out of sync with the actual implementation. This chunk adds `ve subsystem overlap <chunk_id>` to identify overlapping subsystems and updates the `/chunk-complete` workflow to verify subsystem documentation accuracy when overlap is detected.

This advances the narrative's goal of maintaining document health over time: subsystem documentation stays accurate because changes to subsystem code are automatically flagged during chunk completion.

## Success Criteria

1. **`ve subsystem overlap <chunk_id>` command exists** - Takes a chunk ID and reports which subsystems have `code_references` that overlap with the chunk's `code_references` or `code_paths`. Output includes subsystem status.

2. **Overlap detection is file-level and symbol-level** - A subsystem overlaps if:
   - Any of its `code_references` file paths match a chunk's `code_references` or `code_paths`
   - Any of its symbolic references (e.g., `src/foo.py#Bar`) match or are ancestors/descendants of chunk references

3. **`/chunk-complete` workflow includes subsystem analysis** - After running `ve chunk overlap`, the workflow runs `ve subsystem overlap` and then:
   - Reads each overlapping subsystem's OVERVIEW.md to understand its intent, invariants, and scope
   - Analyzes whether the chunk's changes are semantic (affecting behavior/contracts) or non-semantic (refactoring, comments, formatting)
   - If non-semantic: no operator notification needed
   - If semantic: proceeds to status-based decision

4. **Status-based agent behavior for semantic changes**:
   - **STABLE**: Changes should follow existing patterns. Agent verifies alignment and flags deviations for operator review
   - **DOCUMENTED**: Agent should NOT expand scope to fix inconsistencies. Reports overlap but recommends deferring documentation updates unless chunk explicitly addresses the subsystem
   - **REFACTORING**: Agent MAY recommend documentation updates or scope expansion for consistency. Proposes next steps to operator
   - **DISCOVERING**: Agent assists with documentation updates as part of ongoing discovery
   - **DEPRECATED**: Agent warns if chunk is using deprecated patterns and suggests alternatives

5. **No false negatives** - If a chunk touches code tracked by a subsystem, the overlap command must detect it

6. **Agent proposes next steps** - When semantic overlap is detected, agent recommends concrete actions based on status (update docs, add chunk to subsystem's `chunks` list, expand scope, etc.) and confirms with operator before proceeding

## Post-Completion

This is the final chunk in narrative `0002-subsystem_documentation`. After completing this chunk, mark the narrative status as `COMPLETED` in `docs/narratives/0002-subsystem_documentation/OVERVIEW.md`.