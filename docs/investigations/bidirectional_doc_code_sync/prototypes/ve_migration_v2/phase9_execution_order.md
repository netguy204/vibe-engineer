# Phase 9: Migration Execution Order

## Migration Execution Order

### Phase A: Validate Migration Process (Low Risk)
**Subsystems**: orchestrator, cluster_analysis, friction_log
**Goal**: Prove the migration process works with self-contained, low-coupling subsystems

| Step | Action | Validation |
|------|--------|------------|
| A.1 | Create `docs/subsystems/orchestrator/` directory | Directory exists |
| A.2 | Copy `ve_migration_v2/subsystems/orchestrator/OVERVIEW.md` | File exists, valid YAML frontmatter |
| A.3 | Update backreferences in `src/orchestrator/*.py` (7 files) | `grep "# Chunk:" src/orchestrator/` returns 0 |
| A.4 | Add `# Subsystem: docs/subsystems/orchestrator` comments | `grep "# Subsystem:" src/orchestrator/` returns 7+ |
| A.5 | Run tests | `uv run pytest tests/` passes |
| A.6 | Create `docs/subsystems/cluster_analysis/` directory | Directory exists |
| A.7 | Copy cluster_analysis OVERVIEW.md | File exists, valid YAML |
| A.8 | Update backreferences in `src/cluster_analysis.py`, `src/cluster_rename.py` | Chunk refs replaced |
| A.9 | Run tests | All pass |
| A.10 | Create `docs/subsystems/friction_log/` directory | Directory exists |
| A.11 | Copy friction_log OVERVIEW.md | File exists, valid YAML |
| A.12 | Update backreferences in `src/friction.py` | Chunk refs replaced |
| A.13 | Run tests | All pass |
| A.14 | Commit Phase A changes | Clean commit |

**Estimated time**: 30 minutes
**Risk level**: LOW

---

### Phase B: Migrate Supporting Subsystems (Medium Risk)
**Subsystems**: template_system (update), cross_repo_operations (new)
**Goal**: Migrate subsystems with moderate coupling

| Step | Action | Validation |
|------|--------|------------|
| B.1 | Update `docs/subsystems/template_system/OVERVIEW.md` chunk relationships | Frontmatter updated |
| B.2 | Update backreferences in `src/template_system.py` | Chunk refs consolidated |
| B.3 | Update backreferences in `src/project.py` | Chunk refs consolidated |
| B.4 | Update backreferences in `src/constants.py` | Chunk refs replaced |
| B.5 | Run tests | All pass |
| B.6 | Create `docs/subsystems/cross_repo_operations/` directory | Directory exists |
| B.7 | Copy cross_repo_operations OVERVIEW.md | File exists, valid YAML |
| B.8 | Update backreferences in `src/task_utils.py` (~88 refs) | Chunk refs consolidated |
| B.9 | Update backreferences in `src/task_init.py` | Chunk refs consolidated |
| B.10 | Update backreferences in `src/external_refs.py` | Chunk refs consolidated |
| B.11 | Update backreferences in `src/external_resolve.py` | Chunk refs consolidated |
| B.12 | Update backreferences in `src/sync.py` | Chunk refs consolidated |
| B.13 | Run tests | All pass |
| B.14 | Commit Phase B changes | Clean commit |

**Estimated time**: 45 minutes
**Risk level**: MEDIUM

---

### Phase C: Migrate Core Domain (High Risk)
**Subsystems**: workflow_artifacts (update)
**Goal**: Complete core domain migration - highest coupling, most chunks

| Step | Action | Validation |
|------|--------|------------|
| C.1 | Update `docs/subsystems/workflow_artifacts/OVERVIEW.md` | Frontmatter current |
| C.2 | Update backreferences in `src/chunks.py` (~77 refs) | Chunk refs consolidated |
| C.3 | Update backreferences in `src/narratives.py` (~15 refs) | Chunk refs consolidated |
| C.4 | Update backreferences in `src/investigations.py` (~14 refs) | Chunk refs consolidated |
| C.5 | Update backreferences in `src/subsystems.py` (~28 refs) | Chunk refs consolidated |
| C.6 | Update backreferences in `src/models.py` (~62 refs) | Chunk refs consolidated |
| C.7 | Update backreferences in `src/artifact_ordering.py` (~16 refs) | Chunk refs consolidated |
| C.8 | Run tests | All pass |
| C.9 | Update backreferences in `src/ve.py` (~145 refs) | Function-group level refs |
| C.10 | Run tests | All pass |
| C.11 | Commit Phase C changes | Clean commit |

**Estimated time**: 1 hour
**Risk level**: HIGH

---

### Phase D: Cleanup and Finalization
**Goal**: Remove infrastructure refs, update templates, delete chunks

| Step | Action | Validation |
|------|--------|------------|
| D.1 | Remove backreferences from `src/validation.py` | No `# Chunk:` comments |
| D.2 | Remove backreferences from `src/git_utils.py` | No `# Chunk:` comments |
| D.3 | Remove backreferences from `src/repo_cache.py` | No `# Chunk:` comments |
| D.4 | Remove backreferences from `src/symbols.py` | No `# Chunk:` comments |
| D.5 | Update template files with subsystem refs | Templates updated |
| D.6 | Run `uv run ve init` to re-render CLAUDE.md | CLAUDE.md updated |
| D.7 | Run full test suite | All pass |
| D.8 | Final grep verification | `grep -r "# Chunk:" src/` returns 0 (except template examples) |
| D.9 | Delete migrated chunk directories | `docs/chunks/` significantly reduced |
| D.10 | Keep orch_unblock_transition (FUTURE) | FUTURE chunk preserved |
| D.11 | Commit Phase D changes | Clean commit |

**Estimated time**: 30 minutes
**Risk level**: LOW

---

## Rollback Procedures

If issues at any phase:

| Phase | Rollback Action |
|-------|-----------------|
| A (any step fails) | `git reset --hard HEAD~N` to before Phase A |
| B (any step fails) | Keep Phase A, revert Phase B commits |
| C (any step fails) | Keep A+B, revert Phase C commits |
| D (cleanup fails) | Restore chunk directories from git |

---

## Dependency Graph

```
Phase A (Low Risk)           Phase B (Medium Risk)        Phase C (High Risk)
┌─────────────────┐         ┌─────────────────────┐      ┌──────────────────┐
│ orchestrator    │         │ template_system     │      │ workflow_artifacts│
│ cluster_analysis│─────────│ cross_repo_operations│─────│ (core domain)    │
│ friction_log    │         │                     │      │ ve.py            │
└─────────────────┘         └─────────────────────┘      └──────────────────┘
         │                           │                           │
         └───────────────────────────┴───────────────────────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │ Phase D: Cleanup │
                            │ - Infrastructure │
                            │ - Templates     │
                            │ - Delete chunks │
                            └─────────────────┘
```

---

## Success Criteria

Migration is complete when:
- [x] All subsystem OVERVIEW.md files exist and are valid
- [ ] All code backreferences use `# Subsystem:` (no `# Chunk:` except templates)
- [ ] `docs/chunks/` directory contains only FUTURE chunks
- [ ] All tests pass
- [ ] Documentation is coherent and navigable
- [ ] Subsystem code_references validated against actual files

---

## Estimated Total Time

| Phase | Duration | Cumulative |
|-------|----------|------------|
| A | 30 min | 30 min |
| B | 45 min | 1 hr 15 min |
| C | 1 hr | 2 hr 15 min |
| D | 30 min | 2 hr 45 min |

**Total estimated time**: ~3 hours

---

## Pre-Migration Checklist

Before starting Phase A:
- [ ] All chunk GOAL.md files are readable (no parse errors)
- [ ] Proposed subsystem names don't conflict with existing directories
- [ ] Git working tree is clean (commit or stash changes)
- [ ] All tests pass on current state
- [ ] Backup exists (branch or tag for rollback)
- [ ] Review [NEEDS_HUMAN] sections in synthesized OVERVIEW.md files
