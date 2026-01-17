# Phase 7: Backreference Migration Plan

## Overview

Migrate `# Chunk: docs/chunks/<name>` backreferences to `# Subsystem: docs/subsystems/<subsystem>` references.

**Current state**:
- 638 `# Chunk:` references across 33 Python files
- 36 `# Chunk:` references across 13 template files
- 33 `# Subsystem:` references already exist

**Target state**:
- All code governed by a subsystem has `# Subsystem:` reference
- Multiple chunk references to same subsystem → single subsystem reference
- Chunk references only for code not absorbed into a subsystem

---

## Migration Rules

### Rule 1: Multiple chunks → single subsystem
When a file has multiple `# Chunk:` references that all belong to the same subsystem, replace with a single `# Subsystem:` reference at the module level.

**Before**:
```python
# Chunk: docs/chunks/narrative_cli_commands - Narrative creation
# Chunk: docs/chunks/template_system_consolidation - Template integration
# Chunk: docs/chunks/proposed_chunks_frontmatter - Frontmatter parsing
```

**After**:
```python
# Subsystem: docs/subsystems/workflow_artifacts - Narrative lifecycle management
```

### Rule 2: Mixed subsystem chunks → multiple subsystem references
When a file has chunks from different subsystems, use multiple `# Subsystem:` references.

**Before**:
```python
# Chunk: docs/chunks/task_init - Task initialization
# Chunk: docs/chunks/template_system_consolidation - Template rendering
```

**After**:
```python
# Subsystem: docs/subsystems/cross_repo_operations - Task initialization
# Subsystem: docs/subsystems/template_system - Template rendering
```

### Rule 3: Keep existing subsystem references
Files already using `# Subsystem:` references should have those preserved.

### Rule 4: Template files → edit source templates
For files in src/templates/, edit the .jinja2 source template, then regenerate with `ve init`.

---

## File Mapping

### Files by Target Subsystem

#### orchestrator (24 files, ~100 backrefs)

| File | Current Refs | Action |
|------|-------------|--------|
| src/orchestrator/__init__.py | 2 | → `# Subsystem: docs/subsystems/orchestrator` |
| src/orchestrator/models.py | 11 | → `# Subsystem: docs/subsystems/orchestrator` |
| src/orchestrator/state.py | 12 | → `# Subsystem: docs/subsystems/orchestrator` |
| src/orchestrator/daemon.py | 6 | → `# Subsystem: docs/subsystems/orchestrator` |
| src/orchestrator/api.py | 17 | → `# Subsystem: docs/subsystems/orchestrator` |
| src/orchestrator/client.py | 3 | → `# Subsystem: docs/subsystems/orchestrator` |
| src/orchestrator/agent.py | 20 | → `# Subsystem: docs/subsystems/orchestrator` |
| src/orchestrator/scheduler.py | 24 | → `# Subsystem: docs/subsystems/orchestrator` |
| src/orchestrator/worktree.py | 2 | → `# Subsystem: docs/subsystems/orchestrator` |
| src/orchestrator/oracle.py | 3 | → `# Subsystem: docs/subsystems/orchestrator` |
| src/orchestrator/websocket.py | 1 | → `# Subsystem: docs/subsystems/orchestrator` |
| tests/test_orchestrator_*.py | (multiple) | → `# Subsystem: docs/subsystems/orchestrator` |

#### cross_repo_operations (8 files, ~130 backrefs)

| File | Current Refs | Action |
|------|-------------|--------|
| src/task_init.py | 11 | → `# Subsystem: docs/subsystems/cross_repo_operations` |
| src/task_utils.py | 88 | → `# Subsystem: docs/subsystems/cross_repo_operations` |
| src/external_refs.py | 12 | → `# Subsystem: docs/subsystems/cross_repo_operations` (+ workflow_artifacts) |
| src/external_resolve.py | 7 | → `# Subsystem: docs/subsystems/cross_repo_operations` |
| src/sync.py | 4 | → `# Subsystem: docs/subsystems/cross_repo_operations` |
| src/git_utils.py | 7 | → `# Subsystem: docs/subsystems/cross_repo_operations` |
| src/repo_cache.py | 1 | → `# Subsystem: docs/subsystems/cross_repo_operations` |

#### workflow_artifacts (10 files, ~250 backrefs)

| File | Current Refs | Action |
|------|-------------|--------|
| src/chunks.py | 85 | → `# Subsystem: docs/subsystems/workflow_artifacts` |
| src/models.py | 66 | → `# Subsystem: docs/subsystems/workflow_artifacts` |
| src/narratives.py | 15 | → `# Subsystem: docs/subsystems/workflow_artifacts` |
| src/investigations.py | 12 | → `# Subsystem: docs/subsystems/workflow_artifacts` |
| src/subsystems.py | 29 | → `# Subsystem: docs/subsystems/workflow_artifacts` |
| src/artifact_ordering.py | 16 | → `# Subsystem: docs/subsystems/workflow_artifacts` |
| src/symbols.py | 8 | → `# Subsystem: docs/subsystems/workflow_artifacts` |
| src/validation.py | 2 | → `# Subsystem: docs/subsystems/workflow_artifacts` |

#### template_system (3 files, ~38 backrefs)

| File | Current Refs | Action |
|------|-------------|--------|
| src/template_system.py | 19 | → Keep existing `# Subsystem: docs/subsystems/template_system` |
| src/project.py | 19 | → Keep existing + workflow_artifacts refs |
| src/constants.py | 1 | → `# Subsystem: docs/subsystems/template_system` |

#### cluster_analysis (2 files, ~12 backrefs)

| File | Current Refs | Action |
|------|-------------|--------|
| src/cluster_analysis.py | 6 | → `# Subsystem: docs/subsystems/cluster_analysis` |
| src/cluster_rename.py | 6 | → `# Subsystem: docs/subsystems/cluster_analysis` |

#### friction_tracking (1 file, ~3 backrefs)

| File | Current Refs | Action |
|------|-------------|--------|
| src/friction.py | 3 | → `# Subsystem: docs/subsystems/friction_tracking` |

#### Mixed (CLI - spans all subsystems)

| File | Current Refs | Action |
|------|-------------|--------|
| src/ve.py | 149 | → Multiple subsystem refs by command group |

---

## Template Files Migration

Template files need special handling - edit the source .jinja2, then run `ve init`.

| Template | Refs | Target Subsystem |
|----------|------|------------------|
| src/templates/claude/CLAUDE.md.jinja2 | 11 | workflow_artifacts |
| src/templates/chunk/GOAL.md.jinja2 | 5 | workflow_artifacts |
| src/templates/chunk/PLAN.md.jinja2 | 4 | workflow_artifacts |
| src/templates/commands/chunk-*.jinja2 | 6 | workflow_artifacts |
| src/templates/commands/cluster-*.jinja2 | 2 | cluster_analysis |
| src/templates/subsystem/OVERVIEW.md.jinja2 | 1 | workflow_artifacts |

---

## Migration Order

Execute in this order to minimize conflicts:

### Phase A: Pure subsystem files (no overlap)
1. src/orchestrator/* → orchestrator
2. src/cluster_analysis.py, src/cluster_rename.py → cluster_analysis
3. src/friction.py → friction_tracking
4. src/task_init.py → cross_repo_operations
5. src/sync.py, src/git_utils.py, src/repo_cache.py → cross_repo_operations

### Phase B: Mixed subsystem files
6. src/external_refs.py → cross_repo_operations + workflow_artifacts
7. src/task_utils.py → cross_repo_operations + workflow_artifacts
8. src/project.py → template_system + workflow_artifacts

### Phase C: Core workflow files
9. src/chunks.py → workflow_artifacts
10. src/models.py → workflow_artifacts
11. src/artifact_ordering.py → workflow_artifacts
12. src/narratives.py, src/investigations.py, src/subsystems.py → workflow_artifacts (keep existing # Subsystem:)

### Phase D: CLI (largest, most complex)
13. src/ve.py → Multiple subsystem refs by section

### Phase E: Templates
14. Edit .jinja2 templates
15. Run `ve init` to regenerate

### Phase F: Test files
16. tests/test_*.py (optional - lower priority)

---

## Execution Script

A migration script should:

1. **Read chunk-to-subsystem mapping** from phase3_6 analysis
2. **For each file**:
   - Parse all `# Chunk:` comments
   - Map chunks to subsystems
   - Group by subsystem
   - Generate new `# Subsystem:` comments
   - Replace in file
3. **Handle ve.py specially** - segment by Click command group
4. **Handle templates** - edit source, note for regeneration
5. **Generate report** of changes made

---

## Validation Checklist

After migration:

- [ ] `grep -r "# Chunk:" src/` returns only intentional chunk refs
- [ ] All new subsystems referenced in code
- [ ] `ve init` regenerates templates successfully
- [ ] Tests pass
- [ ] Code references in subsystem OVERVIEW.md still resolve
