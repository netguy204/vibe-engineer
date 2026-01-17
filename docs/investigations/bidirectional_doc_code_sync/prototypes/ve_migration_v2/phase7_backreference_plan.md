# Phase 7: Backreference Planning

## Current State Analysis

### Summary
- Files with `# Chunk:` comments: 30+ source files
- Total backreference count: ~500+ individual `# Chunk:` comments
- Files with 10+ chunk refs: src/ve.py (145), src/task_utils.py (88), src/models.py (62), src/chunks.py (77)
- Template files requiring special handling: 6 (src/templates/*/*.jinja2)

### Backreference Migration by Subsystem

---

## Subsystem: workflow_artifacts

### Migrations

| File | Current Refs | Action | New Ref | Granularity |
|------|--------------|--------|---------|-------------|
| src/chunks.py | ~77 chunk refs | consolidate | # Subsystem: docs/subsystems/workflow_artifacts | MODULE |
| src/narratives.py | ~15 chunk refs | consolidate | # Subsystem: docs/subsystems/workflow_artifacts | MODULE |
| src/investigations.py | ~14 chunk refs | consolidate | # Subsystem: docs/subsystems/workflow_artifacts | MODULE |
| src/subsystems.py | ~28 chunk refs | consolidate | # Subsystem: docs/subsystems/workflow_artifacts | MODULE |
| src/models.py | ~62 chunk refs | consolidate | # Subsystem: docs/subsystems/workflow_artifacts | MODULE |
| src/artifact_ordering.py | ~16 chunk refs | consolidate | # Subsystem: docs/subsystems/workflow_artifacts | MODULE |

### Template Files (special handling)

| Rendered File | Source Template | Action |
|---------------|-----------------|--------|
| - | src/templates/chunk/GOAL.md.jinja2 | Keep chunk template backrefs (meta) |
| - | src/templates/chunk/PLAN.md.jinja2 | Keep chunk template backrefs (meta) |
| - | src/templates/subsystem/OVERVIEW.md.jinja2 | Keep subsystem template backrefs (meta) |

---

## Subsystem: template_system

### Migrations

| File | Current Refs | Action | New Ref | Granularity |
|------|--------------|--------|---------|-------------|
| src/template_system.py | ~19 chunk refs | consolidate | # Subsystem: docs/subsystems/template_system | MODULE |
| src/project.py | ~12 chunk refs | consolidate | # Subsystem: docs/subsystems/template_system | MODULE |
| src/constants.py | 1 chunk ref | replace | # Subsystem: docs/subsystems/template_system | MODULE |

### Template Files (special handling)

| Rendered File | Source Template | Action |
|---------------|-----------------|--------|
| CLAUDE.md | src/templates/claude/CLAUDE.md.jinja2 | Update template with subsystem refs |

---

## Subsystem: orchestrator (NEW)

### Migrations

| File | Current Refs | Action | New Ref | Granularity |
|------|--------------|--------|---------|-------------|
| src/orchestrator/state.py | ~11 chunk refs | consolidate | # Subsystem: docs/subsystems/orchestrator | MODULE |
| src/orchestrator/scheduler.py | ~23 chunk refs | consolidate | # Subsystem: docs/subsystems/orchestrator | MODULE |
| src/orchestrator/daemon.py | ~6 chunk refs | consolidate | # Subsystem: docs/subsystems/orchestrator | MODULE |
| src/orchestrator/api.py | ~14 chunk refs | consolidate | # Subsystem: docs/subsystems/orchestrator | MODULE |
| src/orchestrator/agent.py | ~17 chunk refs | consolidate | # Subsystem: docs/subsystems/orchestrator | MODULE |
| src/orchestrator/models.py | ~8 chunk refs | consolidate | # Subsystem: docs/subsystems/orchestrator | MODULE |
| src/orchestrator/websocket.py | 1 chunk ref | replace | # Subsystem: docs/subsystems/orchestrator | MODULE |

---

## Subsystem: cross_repo_operations (NEW)

### Migrations

| File | Current Refs | Action | New Ref | Granularity |
|------|--------------|--------|---------|-------------|
| src/task_utils.py | ~88 chunk refs | consolidate | # Subsystem: docs/subsystems/cross_repo_operations | MODULE |
| src/task_init.py | ~9 chunk refs | consolidate | # Subsystem: docs/subsystems/cross_repo_operations | MODULE |
| src/external_refs.py | ~12 chunk refs | consolidate | # Subsystem: docs/subsystems/cross_repo_operations | MODULE |
| src/external_resolve.py | ~7 chunk refs | consolidate | # Subsystem: docs/subsystems/cross_repo_operations | MODULE |
| src/sync.py | ~4 chunk refs | consolidate | # Subsystem: docs/subsystems/cross_repo_operations | MODULE |

---

## Subsystem: cluster_analysis (NEW)

### Migrations

| File | Current Refs | Action | New Ref | Granularity |
|------|--------------|--------|---------|-------------|
| src/cluster_analysis.py | ~6 chunk refs | consolidate | # Subsystem: docs/subsystems/cluster_analysis | MODULE |
| src/cluster_rename.py | 0 chunk refs | add | # Subsystem: docs/subsystems/cluster_analysis | MODULE |

---

## Subsystem: friction_log (NEW)

### Migrations

| File | Current Refs | Action | New Ref | Granularity |
|------|--------------|--------|---------|-------------|
| src/friction.py | ~3 chunk refs | consolidate | # Subsystem: docs/subsystems/friction_log | MODULE |

---

## Multi-Subsystem File: src/ve.py

The CLI entry point (src/ve.py) contains commands from ALL subsystems. Strategy:

| Section | Current Refs | Action | New Ref | Granularity |
|---------|--------------|--------|---------|-------------|
| Chunk commands (lines ~72-900) | ~50 refs | consolidate | # Subsystem: docs/subsystems/workflow_artifacts | FUNCTION group |
| Narrative commands (lines ~941-1240) | ~15 refs | consolidate | # Subsystem: docs/subsystems/workflow_artifacts | FUNCTION group |
| Task commands (lines ~1241-1280) | ~5 refs | consolidate | # Subsystem: docs/subsystems/cross_repo_operations | FUNCTION group |
| Subsystem commands (lines ~1281-1518) | ~10 refs | consolidate | # Subsystem: docs/subsystems/workflow_artifacts | FUNCTION group |
| Investigation commands (lines ~1519-1709) | ~10 refs | consolidate | # Subsystem: docs/subsystems/workflow_artifacts | FUNCTION group |
| Sync/external commands (lines ~1710-2063) | ~15 refs | consolidate | # Subsystem: docs/subsystems/cross_repo_operations | FUNCTION group |
| Artifact commands (lines ~2064-2182) | ~5 refs | consolidate | # Subsystem: docs/subsystems/cross_repo_operations | FUNCTION group |
| Orch commands (lines ~2183-2918) | ~30 refs | consolidate | # Subsystem: docs/subsystems/orchestrator | FUNCTION group |
| Friction commands (lines ~2919-end) | ~8 refs | consolidate | # Subsystem: docs/subsystems/friction_log | FUNCTION group |

**Recommendation for ve.py**: Use FUNCTION-level granularity. Place subsystem comment above command group definitions.

---

## Removals (Infrastructure)

| File | Current Ref | Reason |
|------|-------------|--------|
| src/validation.py | 2 chunk refs | Infrastructure, no domain backref needed |
| src/git_utils.py | 7 chunk refs | Infrastructure, no domain backref needed |
| src/repo_cache.py | 1 chunk ref | Infrastructure, no domain backref needed |
| src/symbols.py | 8 chunk refs | Infrastructure (symbol parsing), no domain backref |

---

## Migration Priority Order

### Priority 1: HIGH IMPACT, LOW RISK
**Goal**: Validate migration process with self-contained subsystems

| Priority | Files | Subsystem | Risk Level | Chunk Refs | Notes |
|----------|-------|-----------|------------|------------|-------|
| 1.1 | src/orchestrator/*.py (7 files) | orchestrator | LOW | ~80 | Self-contained, clear boundary |
| 1.2 | src/cluster_analysis.py, src/cluster_rename.py | cluster_analysis | LOW | ~6 | Small, self-contained |
| 1.3 | src/friction.py | friction_log | LOW | ~3 | Small, self-contained |

### Priority 2: MEDIUM IMPACT, MEDIUM RISK
**Goal**: Migrate supporting subsystems

| Priority | Files | Subsystem | Risk Level | Chunk Refs | Notes |
|----------|-------|-----------|------------|------------|-------|
| 2.1 | src/template_system.py, src/project.py, src/constants.py | template_system | MEDIUM | ~32 | Already has subsystem |
| 2.2 | src/task_utils.py, src/task_init.py, src/external_refs.py, src/external_resolve.py, src/sync.py | cross_repo_operations | MEDIUM | ~120 | Large but self-contained |

### Priority 3: HIGH COUPLING, MIGRATE LAST
**Goal**: Complete core domain migration

| Priority | Files | Subsystem | Risk Level | Chunk Refs | Notes |
|----------|-------|-----------|------------|------------|-------|
| 3.1 | src/chunks.py, src/narratives.py, src/investigations.py, src/subsystems.py, src/models.py, src/artifact_ordering.py | workflow_artifacts | HIGH | ~210 | Core domain, highest coupling |
| 3.2 | src/ve.py | multiple | HIGH | ~145 | CLI entry point, mixed subsystems |

### Priority 4: CLEANUP
**Goal**: Remove infrastructure refs, final validation

| Priority | Files | Action | Notes |
|----------|-------|--------|-------|
| 4.1 | src/validation.py, src/git_utils.py, src/repo_cache.py, src/symbols.py | Remove backrefs | Infrastructure |
| 4.2 | All template files | Update templates | Special handling |

---

## Validation Steps

After each priority group:
1. Run: `grep -r "# Chunk:" src/` - count should decrease
2. Run: `grep -r "# Subsystem:" src/` - count should increase
3. Verify: Each migrated file has subsystem comment at appropriate level
4. Verify: Subsystem OVERVIEW.md code_references match migrated files
5. Run: Full test suite passes (`uv run pytest tests/`)

---

## Rollback Strategy

- Keep chunk directories until ALL validation passes
- Git history preserves all chunk content (`git log --all -- docs/chunks/chunk_name/`)
- If issues found: revert backreference commits, investigate
- Migration commits should be atomic per priority group

---

## Migration Statistics

| Metric | Count |
|--------|-------|
| Files with `# Chunk:` before | ~30 |
| Expected files with `# Subsystem:` after | ~25 |
| Backreferences to consolidate | ~500 |
| Backreferences to remove (infrastructure) | ~18 |
| New backreferences to add | ~2 (cluster_rename.py) |
| Template files requiring update | 6 |
| Multi-subsystem files (ve.py) | 1 |

---

## Template Migration Notes

Template files use Jinja2 comment syntax `{# ... #}` for backreferences:

**Current pattern** (in .jinja2 files):
```jinja2
{# Chunk: docs/chunks/template_unified_module - Brief description #}
```

**New pattern**:
```jinja2
{# Subsystem: docs/subsystems/template_system - Brief description #}
```

Files to update:
- `src/templates/claude/CLAUDE.md.jinja2`
- `src/templates/chunk/GOAL.md.jinja2`
- `src/templates/chunk/PLAN.md.jinja2`
- `src/templates/subsystem/OVERVIEW.md.jinja2`
- `src/templates/narrative/OVERVIEW.md.jinja2`
- `src/templates/investigation/OVERVIEW.md.jinja2`

After template updates, run `ve init` to re-render CLAUDE.md.
