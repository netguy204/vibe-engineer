---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/chunks.py
- src/narratives.py
- src/investigations.py
- src/ve.py
- .claude/commands/chunk-complete.md
- .claude/commands/investigation-create.md
- docs/subsystems/workflow_artifacts/OVERVIEW.md
- tests/test_transitions.py
code_references:
- ref: src/models.py#VALID_CHUNK_TRANSITIONS
  implements: Chunk state transition rules (FUTURE->IMPLEMENTING->ACTIVE->SUPERSEDED->HISTORICAL)
- ref: src/models.py#VALID_NARRATIVE_TRANSITIONS
  implements: Narrative state transition rules (DRAFTING->ACTIVE->COMPLETED)
- ref: src/models.py#VALID_INVESTIGATION_TRANSITIONS
  implements: Investigation state transition rules (ONGOING->SOLVED/NOTED/DEFERRED)
- ref: src/chunks.py#Chunks::get_status
  implements: Get current chunk status from frontmatter
- ref: src/chunks.py#Chunks::update_status
  implements: Update chunk status with transition validation
- ref: src/narratives.py#Narratives::get_status
  implements: Get current narrative status from frontmatter
- ref: src/narratives.py#Narratives::update_status
  implements: Update narrative status with transition validation
- ref: src/narratives.py#Narratives::_update_overview_frontmatter
  implements: Helper to update OVERVIEW.md frontmatter fields
- ref: src/investigations.py#Investigations::get_status
  implements: Get current investigation status from frontmatter
- ref: src/investigations.py#Investigations::update_status
  implements: Update investigation status with transition validation
- ref: src/investigations.py#Investigations::_update_overview_frontmatter
  implements: Helper to update OVERVIEW.md frontmatter fields
- ref: tests/test_transitions.py
  implements: Tests for transition dict structure and CLI commands
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after:
- external_chunk_causal
---

# Chunk Goal

## Minor Goal

Add explicit state transition validation for chunks, narratives, and investigations to `models.py`, following the pattern established by `VALID_STATUS_TRANSITIONS` for subsystems.

Currently, only subsystems have code-level state transition validation. This creates a gap where invalid lifecycle transitions (e.g., marking a FUTURE chunk as HISTORICAL without going through IMPLEMENTING/ACTIVE) can occur without runtime validation. This violates the workflow_artifacts subsystem's Hard Invariant #10: "Status transitions must be defined in both template and code."

This chunk addresses the "No Code-Level State Transitions" known deviation in the workflow_artifacts subsystem by:

1. **Adding transition dicts to `models.py`**:
   - `VALID_CHUNK_TRANSITIONS` - defining valid state paths for chunks
   - `VALID_NARRATIVE_TRANSITIONS` - defining valid state paths for narratives
   - `VALID_INVESTIGATION_TRANSITIONS` - defining valid state paths for investigations

2. **Adding manager class methods** (following the subsystems pattern):
   - `Chunks.get_status()`, `Chunks.update_status()`
   - `Narratives.get_status()`, `Narratives.update_status()`
   - `Investigations.get_status()`, `Investigations.update_status()`

3. **Adding CLI commands**:
   - `ve chunk status [chunk_id] [new_status]` - show/update chunk status
   - `ve narrative status [narrative_id] [new_status]` - show/update narrative status
   - `ve investigation status [investigation_id] [new_status]` - show/update investigation status

4. **Updating slash commands** to use official status commands instead of direct frontmatter editing:
   - `/chunk-complete` - use `ve chunk status` for IMPLEMENTING → ACTIVE
   - `/investigation-create` - reference `ve investigation status` for resolution

This enables runtime validation of lifecycle transitions and ensures agents cannot accidentally put artifacts into invalid states.

## Success Criteria

### Transition Dicts in models.py

1. `VALID_CHUNK_TRANSITIONS` dict exists mapping each `ChunkStatus` to its valid next states:
   - FUTURE → {IMPLEMENTING, HISTORICAL}
   - IMPLEMENTING → {ACTIVE, HISTORICAL}
   - ACTIVE → {SUPERSEDED, HISTORICAL}
   - SUPERSEDED → {HISTORICAL}
   - HISTORICAL → {} (terminal)

2. `VALID_NARRATIVE_TRANSITIONS` dict exists mapping each `NarrativeStatus` to its valid next states:
   - DRAFTING → {ACTIVE}
   - ACTIVE → {COMPLETED}
   - COMPLETED → {} (terminal)

3. `VALID_INVESTIGATION_TRANSITIONS` dict exists mapping each `InvestigationStatus` to its valid next states:
   - ONGOING → {SOLVED, NOTED, DEFERRED}
   - SOLVED → {} (terminal)
   - NOTED → {} (terminal)
   - DEFERRED → {ONGOING} (can be resumed)

### Manager Class Methods

4. `Chunks` class has `get_status(chunk_id)` and `update_status(chunk_id, new_status)` methods following the subsystems pattern

5. `Narratives` class has `get_status(narrative_id)` and `update_status(narrative_id, new_status)` methods

6. `Investigations` class has `get_status(investigation_id)` and `update_status(investigation_id, new_status)` methods

7. All `update_status()` methods validate transitions against their respective `VALID_*_TRANSITIONS` dict

### CLI Commands

8. `ve chunk status [chunk_id] [new_status]` command exists - shows status without new_status arg, updates with validation when provided

9. `ve narrative status [narrative_id] [new_status]` command exists with same pattern

10. `ve investigation status [investigation_id] [new_status]` command exists with same pattern

### Slash Command Updates

11. `/chunk-complete` (`.claude/commands/chunk-complete.md`) step 11 updated to use `ve chunk status <chunk_id> ACTIVE` instead of direct frontmatter editing

12. `/investigation-create` (`.claude/commands/investigation-create.md`) step 6 updated to reference `ve investigation status` for resolution

### Verification

13. All tests pass (`uv run pytest tests/`)

14. The workflow_artifacts subsystem's "No Code-Level State Transitions" known deviation is marked as RESOLVED

