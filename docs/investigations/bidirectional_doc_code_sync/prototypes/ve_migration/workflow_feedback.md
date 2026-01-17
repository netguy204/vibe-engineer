# Workflow Feedback: Chunk Migration Bootstrap

This document captures feedback from executing the chunk migration bootstrap workflow against the vibe-engineer repository.

---

## What Worked Well

### 1. Phase 1 Prompt Structure

The Phase 1 prompt's four-part structure (INVENTORY, OVERLAP MATRIX, CLUSTER IDENTIFICATION, ORPHAN DETECTION) produced comprehensive, well-organized output.

**Strengths:**
- Clear output format with tables made results easy to parse
- The overlap matrix (file-to-chunks mapping) was particularly valuable for identifying high-touch areas
- Cluster identification by "business language, not chunk names" guided good naming
- Orphan detection caught both stale references and documentation-only chunks

### 2. Business Capability Framing (Phase 2)

Asking "What business problem do these chunks collectively solve?" and "Who benefits?" produced insights that pure code analysis would miss.

**Example:** The orchestrator cluster could have been described technically as "daemon + worktree + agent code," but the business framing revealed it as "parallel agent management for throughput optimization."

### 3. Chunk Success Criteria as Invariant Sources (Phase 4)

The instruction to "MINE CHUNK SUCCESS CRITERIA" for business rules was highly effective. Success criteria are already stated as constraints that must hold, making them natural sources of invariants.

**Example:** "Only one IMPLEMENTING chunk allowed per repo" from chunk_create_guard's success criteria directly maps to a subsystem invariant.

### 4. Entity Discovery from Chunk Content (Phase 3)

Looking for status enums and state transitions in chunk content worked well. Chunks naturally describe entity states ("chunk can be PLANNED -> IMPLEMENTING -> ACTIVE") because that's what they're implementing.

### 5. Intermediate Output Files

Saving each phase's output enabled iterative refinement and review. The `phase1_chunk_inventory.md` file was referenced repeatedly in later phases.

---

## What Was Confusing or Needed Clarification

### 1. "Cluster" Terminology Overload

The workflow uses "cluster" to mean:
- Groups of chunks with shared naming prefixes
- Groups of chunks with overlapping file references
- Groups of chunks implementing the same capability

These are related but distinct concepts. The prompt should clarify which type of clustering is being requested at each step.

**Suggestion:** Define cluster types upfront:
- **Naming cluster**: Chunks sharing a prefix (e.g., `orch_*`)
- **File cluster**: Chunks sharing >50% of code_references
- **Capability cluster**: Chunks solving the same business problem

### 2. Phase 5 "Right Granularity" Guidance

The prompt says "Merge if: always change together, shared vocabulary. Split if: distinct user workflows, different change cadence."

This is helpful but abstract. Without examples, it's unclear how to apply these criteria in practice.

**Suggestion:** Add concrete examples:
- "Merge example: chunk_frontmatter_model and chunk_validate both serve chunk lifecycle -> merge into workflow_artifacts"
- "Split example: orch_dashboard serves operators, orch_scheduling serves infrastructure -> keep in same subsystem (same capability, different user types is OK)"

### 3. Handling Existing Subsystem Documentation

The vibe-engineer repository already has `docs/subsystems/` with documented subsystems. The workflow doesn't address how to reconcile chunk analysis with existing subsystem documentation.

**Suggestion:** Add a step: "If subsystems already exist, compare chunk-derived boundaries with existing subsystem boundaries. Note agreements and divergences."

### 4. Phase 7 Output Format

The backreference migration plan output format is specified but incomplete. It doesn't capture:
- Priority ordering (which files to migrate first)
- Validation steps (how to verify migrations are correct)
- Rollback strategy (if something goes wrong)

**Suggestion:** Expand the output format with priority and validation sections.

### 5. Narrative vs. Investigation vs. Subsystem Distinction

The workflow mentions all three artifact types but doesn't clearly explain when each applies:
- When should a group of chunks become a narrative?
- When should it become a subsystem?
- How do investigations fit in?

**Suggestion:** Add a decision tree or table explaining artifact type selection.

---

## Suggested Prompt Refinements

### Phase 1: Add Prefix Cluster Analysis

The current prompt asks for "CLUSTER IDENTIFICATION: Name each cluster by concept" but doesn't explicitly request analysis of naming prefix clusters.

**Add:**
```
5. PREFIX CLUSTER ANALYSIS: Identify clusters by naming prefix:
   - Which chunks share a common prefix (e.g., orch_*, task_*)?
   - How well do prefix clusters align with file overlap clusters?
   - Are there mismatch cases where naming suggests one cluster but file overlap suggests another?
```

### Phase 2: Add Existing Subsystem Reconciliation

**Add:**
```
RECONCILE WITH EXISTING SUBSYSTEMS:
1. If docs/subsystems/ exists, read existing subsystem documentation
2. For each existing subsystem, compare:
   - Its documented scope vs. chunk-derived capability boundaries
   - Its code_references vs. chunk code_references
3. Note: agreements, divergences, gaps (capabilities with no subsystem)
```

### Phase 3: Clarify Entity vs. Value Object

The prompt asks for "primary entities" but doesn't distinguish entities (things with identity) from value objects (things compared by value).

**Add:**
```
For each entity, determine:
- Is this an Entity (has identity, tracked across states)?
- Or a Value Object (compared by content, no lifecycle)?

Example:
- Chunk: Entity (has identity, tracked across FUTURE->IMPLEMENTING->ACTIVE)
- SymbolicReference: Value Object (compared by content, no lifecycle)
```

### Phase 5: Add Granularity Examples

**Add concrete examples:**
```
GRANULARITY EXAMPLES:

Merge these:
- chunk_frontmatter_model + chunk_validate + chunk_list_command
  -> All serve "chunk lifecycle" capability
  -> Same entity (Chunk), same status model

Split these:
- orch_dashboard (operator-facing)
  -> Keep with orchestrator (same capability, different touchpoint)
  NOT a separate subsystem (would create artificial boundary)

Keep separate:
- workflow_artifacts vs. orchestrator
  -> Different entities (Chunk vs WorkUnit)
  -> Different change cadence (stable vs active development)
  -> Different operators (all users vs parallel work users)
```

### Phase 7: Add Priority and Validation

**Expand output format:**
```
## Migration Priority Order
1. High-touch files (10+ chunk refs) - migrate first for maximum impact
2. Orchestrator files - self-contained, low risk
3. Core model files - higher coupling, migrate after validation
4. CLI files - highest touch, migrate last

## Validation Steps
1. After migration, run: grep -r "# Chunk:" src/ (should find no legacy refs)
2. After migration, verify: each file has at most one # Subsystem: comment
3. After migration, test: subsystem OVERVIEW.md references match migrated files

## Rollback Strategy
- Keep old chunk directories until subsystem validation passes
- Git history preserves all chunk content for archaeology
```

### Phase 8: Add Conflict Resolution Guidance

The prompt mentions "Handle content conflicts" but doesn't explain how.

**Add:**
```
CONFLICT RESOLUTION STRATEGIES:

Overlapping success criteria:
- If semantically identical, dedupe to single invariant
- If semantically different, keep both with attribution
  Example: "Reference format must be symbolic (from symbolic_code_refs)"

Contradictory statements:
- Check HISTORICAL status - one may supersede the other
- Check created_after ordering - newer chunk wins
- If unresolved, flag for human decision with both statements

Example conflict:
- chunk_a: "Line numbers are acceptable"
- chunk_b: "Only symbolic references allowed"
Resolution: chunk_b (newer, chunk_a marked HISTORICAL)
```

---

## Missing Steps or Considerations

### 1. Chunk Status Handling

The workflow doesn't address how to handle chunks with non-ACTIVE status:
- FUTURE: Not yet implemented, should it be included?
- HISTORICAL: Superseded, should it contribute to synthesis?
- SUPERSEDED: Replaced by another chunk

**Suggestion:** Add guidance:
- "Include ACTIVE chunks fully"
- "Include HISTORICAL chunks in provenance only (for archaeology)"
- "Exclude FUTURE chunks (not yet implemented)"

### 2. Cross-Repository Chunks

The workflow assumes all chunks are in the same repository. For cross-repo scenarios (task directories with external chunks), additional considerations apply.

**Suggestion:** Add:
```
CROSS-REPO CONSIDERATIONS:
- External chunks (from other repos) cannot be migrated directly
- Subsystem boundaries should respect repository boundaries
- External references may need different handling than local references
```

### 3. Template-Rendered Files

Some files in vibe-engineer are rendered from templates (CLAUDE.md from CLAUDE.md.jinja2). Backreferences in these files need special handling.

**Suggestion:** Add:
```
TEMPLATE FILE HANDLING:
- If a file is rendered from a template, update the SOURCE template, not the rendered file
- Identify rendered files by checking for AUTO-GENERATED headers
- Template backreferences use Jinja2 comment syntax: {# Subsystem: ... #}
```

### 4. Incremental Migration Strategy

The workflow assumes a big-bang migration. In practice, incremental migration is often safer.

**Suggestion:** Add a Phase 8.5:
```
## Phase 8.5: Migration Execution Order

Prioritize subsystems for migration:

1. STABLE subsystems first (template_system)
   - Already well-bounded
   - Low risk of boundary changes
   - Validates migration process

2. Well-clustered capabilities second (orchestrator)
   - Clear boundaries
   - Self-contained code
   - Moderate risk

3. Core domain last (workflow_artifacts)
   - Highest coupling
   - Most chunks
   - Requires most validation
```

### 5. Verification Checklist Before Execution

The workflow ends with a validation checklist, but it's for after migration. A pre-execution checklist would be valuable.

**Suggestion:** Add:
```
## Pre-Execution Verification

Before running the migration:
- [ ] All chunk GOAL.md files are readable (no parse errors)
- [ ] Proposed subsystem names don't conflict with existing directories
- [ ] Git working tree is clean (commit or stash changes)
- [ ] All tests pass on current state
- [ ] Backup exists (branch or tag)
```

---

## Summary

The workflow prompts are well-structured and produce useful analysis. The main areas for improvement are:

1. **Terminology clarification** - Distinguish between naming clusters, file clusters, and capability clusters
2. **Concrete examples** - Add examples for abstract guidance (granularity decisions, conflict resolution)
3. **Existing artifact reconciliation** - Address how to handle existing subsystem documentation
4. **Edge case handling** - Non-ACTIVE chunks, cross-repo scenarios, template files
5. **Incremental strategy** - Support phased migration rather than big-bang

Overall, the workflow successfully guided discovery of 4 core subsystems and 40+ chunk assignments in the vibe-engineer codebase, validating its effectiveness for medium-sized repositories with mature chunk documentation.
