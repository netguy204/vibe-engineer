# Chunk Migration Bootstrap Workflow

A workflow for migrating a legacy vibe-engineering repository (code + existing chunks) to a wiki-based subsystem model.

## Overview

**Input**: A codebase with existing chunk documentation (`docs/chunks/`)

**Phases**:
1. Chunk Inventory & Clustering
2. Business Capability Discovery (chunk-informed)
3. Entity & Lifecycle Mapping
4. Business Rule Extraction
5. Domain Boundary Refinement
6. Infrastructure Annotation
7. Backreference Planning
8. Chunk Synthesis & Archive

**Output**:
- 8 intermediate analysis artifacts (saved for review at each phase)
- Final subsystem proposals with chunk provenance
- Migration plan for backreferences (`# Chunk:` → `# Subsystem:`)
- Archive strategy for chunk directories

**Key Principle**: Chunks are work-item-sized artifacts that cluster into concept-sized subsystems. This workflow aggregates chunks into wiki pages while preserving their archaeological value in git history.

## When to Use This Workflow

Use this workflow when:
- Repository has `docs/chunks/` with existing chunk documentation
- Chunks have `code_references` in their frontmatter
- Goal is to migrate to subsystem-based documentation

Use the code-only workflow (`domain_oriented_bootstrap_workflow.md`) when:
- Repository has no existing chunk documentation
- Starting fresh with wiki-based documentation

---

## Phase 1: Chunk Inventory & Clustering

**Goal**: Build a map of existing chunks and identify natural concept clusters.

**Prompt for agent**:
```
Analyze the existing chunk documentation in docs/chunks/.

1. INVENTORY: For each chunk directory, extract:
   - Chunk name (directory name)
   - Status (from GOAL.md frontmatter)
   - code_references (from GOAL.md frontmatter)
   - Brief summary of what the chunk accomplishes (from GOAL.md content)

2. OVERLAP MATRIX: Build a file-to-chunks mapping:
   - Which files are referenced by multiple chunks?
   - Group chunks that share >50% of their code_references

3. CLUSTER IDENTIFICATION: Name each cluster by concept:
   - What domain concept unifies chunks in this cluster?
   - Use business language, not chunk names
   - A cluster of "chunk_frontmatter_model", "chunk_schema_validation",
     "symbolic_code_refs" might be → "Chunk Schema & Validation"

4. ORPHAN DETECTION: Identify:
   - Chunks with no code_references (documentation-only?)
   - Chunks referencing files that no longer exist (stale?)
   - Code files with no chunk references (undocumented?)

Output format:

## Chunk Inventory
| Chunk | Status | Files Referenced | Summary |
|-------|--------|------------------|---------|
| ... | ... | ... | ... |

## File Overlap Analysis
| File | Chunks Referencing |
|------|-------------------|
| src/models.py | chunk_a, chunk_b, chunk_c |
| ... | ... |

## Concept Clusters
### Cluster: [Concept Name]
- Chunks: [list]
- Shared files: [list]
- Rationale: [why these belong together]

## Orphans & Anomalies
- Documentation-only chunks: [list]
- Stale references: [list]
- Undocumented code areas: [list]
```

**Intermediate output**: Save as `phase1_chunk_inventory.md`

---

## Phase 2: Business Capability Discovery (Chunk-Informed)

**Goal**: Identify business capabilities using chunk clusters as initial hypothesis.

**Prompt for agent**:
```
Using the chunk clusters from Phase 1 as starting hypotheses, discover
the business capabilities this system provides.

FOR EACH CLUSTER from Phase 1:
1. Read the GOAL.md files for chunks in this cluster
2. What business problem do these chunks collectively solve?
3. Who benefits from this capability? (users, operators, developers?)
4. Does the cluster boundary make sense from a business perspective?
   - Should it be split? (multiple distinct user needs)
   - Should it merge with another cluster? (artificial separation)

VALIDATE AGAINST CODE:
1. Do the code_references support the business capability hypothesis?
2. Are there code areas that serve this capability but weren't in chunks?
3. Are there chunks that span multiple business capabilities?

DISCOVER UNCLUSTERED CAPABILITIES:
1. Review "undocumented code areas" from Phase 1
2. What business capabilities exist in code but have no chunks?
3. These need subsystems too, even without chunk input

Output format:

## Chunk-Derived Capabilities
### [Capability Name]
- Source clusters: [from Phase 1]
- Contributing chunks: [list]
- Business intent: [what problem this solves]
- Validation: [how code supports this]
- Boundary adjustments: [splits/merges from cluster]

## Code-Discovered Capabilities
### [Capability Name]
- Code locations: [files/modules]
- Business intent: [what problem this solves]
- Why no chunks: [new code? infrastructure? oversight?]

## Capability Relationships
- [Capability A] depends on [Capability B] for [reason]
```

**Intermediate output**: Save as `phase2_business_capabilities.md`

---

## Phase 3: Entity & Lifecycle Mapping

**Goal**: Map domain entities and their state machines, using chunk content as hints.

**Prompt for agent**:
```
For each business capability, identify the core domain entities.

USE CHUNK CONTENT AS HINTS:
- Chunk GOAL.md files often describe entities implicitly
- Success criteria may reveal entity states
- Code references point to entity implementations

FOR EACH CAPABILITY:
1. What are the primary entities? (Things with identity that persist)
   - Look at chunk code_references for model definitions
   - Check for enums that suggest state machines

2. What states can each entity be in?
   - Chunk success criteria often describe state transitions
   - Example: "Chunk can be PLANNED → IMPLEMENTING → ACTIVE"

3. What relationships exist between entities?
   - Chunk references to multiple models suggest relationships
   - One-to-many, ownership hierarchies

4. How do chunks document entity behavior?
   - Which chunks describe creation?
   - Which chunks describe state transitions?
   - Which chunks describe validation?

Output format:

## Entity Catalog
### [Entity Name]
- Capability: [which capability owns this]
- Source chunks: [chunks that document this entity]
- States: [STATE_A → STATE_B → STATE_C]
- Key attributes: [important fields]
- Relationships: [owns X, belongs to Y]

## Entity Relationship Diagram
[ASCII diagram showing relationships]

## Chunk-to-Entity Mapping
| Chunk | Entities Affected | Aspect Documented |
|-------|-------------------|-------------------|
| chunk_a | Entity1, Entity2 | Creation, validation |
```

**Intermediate output**: Save as `phase3_entity_lifecycle.md`

---

## Phase 4: Business Rule Extraction

**Goal**: Extract invariants from chunk success criteria and code.

**Prompt for agent**:
```
Identify business rules that must never be violated.

MINE CHUNK SUCCESS CRITERIA:
- Chunk GOAL.md success criteria often encode invariants
- "Validation must reject invalid references" → invariant
- "Status can only transition forward" → state machine rule

FOR EACH CAPABILITY:
1. What constraints exist on entity states?
   - From chunk success criteria
   - From validation code in code_references

2. What validation rules exist?
   - Required fields, valid transitions
   - Chunks often document these explicitly

3. What authorization/isolation rules exist?
   - Multi-tenancy constraints
   - Role-based access rules

4. What consistency rules exist?
   - Cross-entity constraints
   - Calculation rules

CONFLICT DETECTION:
- Do any chunks document contradictory rules?
- Are there rules in code not documented in chunks?
- Are there chunk rules not enforced in code?

Output format:

## Business Rules by Capability

### [Capability Name]
| Rule | Source | Enforcement |
|------|--------|-------------|
| [description] | chunk_x GOAL.md | src/validation.py |
| [description] | code only | src/models.py |

## Rule Conflicts
| Rule A | Rule B | Resolution Needed |
|--------|--------|-------------------|
```

**Intermediate output**: Save as `phase4_business_rules.md`

---

## Phase 5: Domain Boundary Refinement

**Goal**: Finalize subsystem boundaries, reconciling chunk clusters with business analysis.

**Prompt for agent**:
```
Refine the capability boundaries into final subsystem proposals.

RECONCILE CHUNK CLUSTERS WITH BUSINESS ANALYSIS:
1. Where do chunk clusters align with business capabilities?
   - These are strong subsystem candidates

2. Where do they diverge?
   - Chunks that span capabilities → split across subsystems
   - Capabilities served by scattered chunks → consolidate

3. What's the right granularity?
   - Merge if: always change together, shared vocabulary
   - Split if: distinct user workflows, different change cadence

NAMING:
- Use business language from Phase 2
- Prefer nouns over verbs
- ✓ "artifact_ordering" (what it manages)
- ✗ "ordering_implementation" (too technical)

CHUNK ASSIGNMENT:
- For each proposed subsystem, list contributing chunks
- Some chunks may contribute to multiple subsystems (split content)
- Some chunks may be deprecated (superseded by others)

Output format:

## Proposed Subsystems

### [Subsystem Name]
- Business intent: [from Phase 2]
- Core entities: [from Phase 3]
- Key invariants: [from Phase 4]
- Contributing chunks: [list with notes]
  - chunk_a: fully absorbed
  - chunk_b: partial (validation rules only)
  - chunk_c: deprecated by chunk_d
- Code locations: [consolidated code_references]

## Chunk Disposition
| Chunk | Disposition | Target Subsystem(s) |
|-------|-------------|---------------------|
| chunk_a | absorbed | subsystem_x |
| chunk_b | split | subsystem_x (rules), subsystem_y (schema) |
| chunk_c | deprecated | n/a |
| chunk_d | absorbed | subsystem_x |
```

**Intermediate output**: Save as `phase5_domain_boundaries.md`

---

## Phase 6: Infrastructure Annotation

**Goal**: Identify infrastructure patterns as supporting material.

**Prompt for agent**:
```
Identify cross-cutting infrastructure patterns.

INFRASTRUCTURE VS DOMAIN:
- Domain subsystems: owned by business capabilities
- Infrastructure: serves multiple domains equally

COMMON INFRASTRUCTURE PATTERNS:
- Logging, tracing, metrics
- Authentication, authorization
- Caching, persistence patterns
- Error handling, validation frameworks

FOR EACH PATTERN:
1. Which subsystems use it?
2. Is it consistent or fragmented?
3. Are there chunks that document infrastructure?
   - These chunks may not map to domain subsystems
   - They may become "Supporting Patterns" documentation

SUBSYSTEM OR SUPPORTING PATTERN?
Only promote to subsystem if:
- Has complex business rules (not just technical patterns)
- Engineers frequently misunderstand it
- Has known deviations that need tracking

Usually: infrastructure → "Supporting Patterns" section, not subsystem

Output format:

## Infrastructure Patterns

### [Pattern Name]
- Used by subsystems: [list]
- Documented in chunks: [list or "none"]
- Consistency: [consistent / fragmented / varies]
- Recommendation: supporting pattern / subsystem

## Infrastructure Chunks
| Chunk | Pattern | Recommendation |
|-------|---------|----------------|
| chunk_x | error handling | fold into Supporting Patterns |
```

**Intermediate output**: Save as `phase6_infrastructure.md`

---

## Phase 7: Backreference Planning

**Goal**: Plan the migration from chunk backreferences to subsystem backreferences.

**Prompt for agent**:
```
Create the migration plan for code backreferences.

CURRENT STATE ANALYSIS:
1. Find all `# Chunk:` comments in the codebase
2. Map each to the target subsystem (from Phase 5)
3. Identify files with multiple chunk references

MIGRATION RULES:
1. Single chunk → single subsystem:
   `# Chunk: chunk_a` → `# Subsystem: subsystem_x`

2. Multiple chunks → single subsystem:
   ```
   # Chunk: chunk_a
   # Chunk: chunk_b
   ```
   → `# Subsystem: subsystem_x`

3. Multiple chunks → multiple subsystems:
   Review the code location. Usually one subsystem is primary:
   `# Subsystem: primary_subsystem`
   (The secondary relationship is captured in subsystem OVERVIEW.md)

4. Chunk reference with no target subsystem:
   - Infrastructure chunk → remove backreference
   - Deprecated chunk → remove backreference
   - Orphan code → add to appropriate subsystem

GRANULARITY DECISIONS:
- MODULE level: entire file serves one subsystem
- CLASS level: class within multi-concern file
- FUNCTION level: only specific functions

NEW BACKREFERENCES:
- Code areas discovered in Phase 2 that need subsystem refs
- Use same granularity rules

Output format:

## Backreference Migration Plan

### Subsystem: [name]
| File | Current Refs | Action | New Ref |
|------|--------------|--------|---------|
| src/foo.py | # Chunk: a, b | consolidate | # Subsystem: name |
| src/bar.py | (none) | add | # Subsystem: name |

### Removals
| File | Current Ref | Reason |
|------|-------------|--------|
| src/util.py | # Chunk: infra_x | infrastructure, no backref needed |

## Migration Statistics
- Files with chunk refs: N
- Refs to consolidate: M
- Refs to remove: P
- New refs to add: Q
```

**Intermediate output**: Save as `phase7_backreference_plan.md`

---

## Phase 8: Chunk Synthesis & Archive

**Goal**: Synthesize subsystem documentation from chunk content and plan archive.

**Prompt for agent**:
```
Create subsystem OVERVIEW.md content by synthesizing chunk GOAL.md files.

FOR EACH SUBSYSTEM:
1. Gather contributing chunks (from Phase 5)
2. Extract from each chunk GOAL.md:
   - Problem statement → contributes to Intent
   - Success criteria → contributes to Invariants
   - Code references → validates code_references list
   - Rationale/context → contributes to Scope

3. Synthesize into OVERVIEW.md structure:
   ```markdown
   ---
   status: DOCUMENTED
   ---

   ## Intent
   [Synthesized from chunk problem statements]

   ## Scope
   [What's in/out, from chunk boundaries]

   ## Invariants
   [Synthesized from chunk success criteria]

   ## Code References
   [Consolidated from all contributing chunks]

   ## Chunk Provenance
   [List of chunks that were synthesized into this subsystem,
    preserved for archaeological reference]
   ```

4. Handle content conflicts:
   - Overlapping success criteria → merge or note deviation
   - Contradictory statements → flag for resolution

ARCHIVE STRATEGY:
For chunk directories after migration:

Option A: Delete immediately
- Subsystem captures all value
- Git history preserves archaeology
- Cleanest outcome

Option B: Archive directory
- Move to docs/archive/chunks/
- Preserves files for reference
- Clutters repository

Option C: Gradual deprecation
- Mark chunks as DEPRECATED in frontmatter
- Delete after N months
- Allows validation period

Recommendation: Option A (delete) with careful synthesis.
Git history + subsystem provenance section preserves archaeology.

Output format:

## Subsystem Documentation Drafts

### docs/subsystems/[name]/OVERVIEW.md
```markdown
[Full draft of synthesized OVERVIEW.md]
```

Contributing chunks:
- chunk_a: [what was extracted]
- chunk_b: [what was extracted]

Conflicts requiring resolution:
- [description of conflict]

### [Next subsystem...]

## Archive Plan
| Chunk | Disposition | Notes |
|-------|-------------|-------|
| chunk_a | delete after migration | fully synthesized |
| chunk_b | delete after migration | fully synthesized |
| chunk_c | keep temporarily | needs validation |

## Migration Execution Order
1. Create subsystem directories
2. Write OVERVIEW.md files
3. Update code backreferences
4. Verify subsystem coverage
5. Delete chunk directories
6. Commit with clear message
```

**Intermediate output**: Save as `phase8_synthesis_archive.md`

---

## Final Report Format

After all phases, produce a consolidated report:

```markdown
# Chunk Migration Report

## Executive Summary
- Chunks analyzed: N
- Subsystems created: M
- Code files migrated: P
- Backreferences updated: Q

## Migration Map

### Chunk → Subsystem Mapping
| Chunk | Target Subsystem | Disposition |
|-------|------------------|-------------|
| ... | ... | absorbed / split / deprecated |

### Subsystem Summary
| Subsystem | Intent | Chunks Absorbed | Code Locations |
|-----------|--------|-----------------|----------------|
| ... | ... | N | M files |

## Subsystem Documentation

[For each subsystem: synthesized OVERVIEW.md content]

## Backreference Migration

[Summary of backreference changes]

## Archive Execution

[Ordered steps to complete migration]

## Validation Checklist
- [ ] Each subsystem has clear business intent
- [ ] All chunk content is preserved in subsystems or git history
- [ ] Code backreferences updated
- [ ] No orphan code (undocumented areas)
- [ ] Infrastructure documented in Supporting Patterns
```

---

## Intermediate Output Summary

| Phase | Output File | Purpose |
|-------|-------------|---------|
| 1 | `phase1_chunk_inventory.md` | Chunk map and clustering |
| 2 | `phase2_business_capabilities.md` | Chunk-informed capability discovery |
| 3 | `phase3_entity_lifecycle.md` | Entity mapping with chunk hints |
| 4 | `phase4_business_rules.md` | Invariants from chunks and code |
| 5 | `phase5_domain_boundaries.md` | Subsystem boundaries with chunk assignment |
| 6 | `phase6_infrastructure.md` | Infrastructure patterns |
| 7 | `phase7_backreference_plan.md` | Migration plan for code refs |
| 8 | `phase8_synthesis_archive.md` | Synthesized docs and archive plan |
| Final | `chunk_migration_report.md` | Complete migration report |

---

## Validation Checklist

Before executing migration:

- [ ] Every chunk is accounted for (absorbed, split, or deprecated)
- [ ] Every subsystem has clear business intent (not technical description)
- [ ] Chunk success criteria are preserved as subsystem invariants
- [ ] Backreference migration plan covers all `# Chunk:` comments
- [ ] Infrastructure is documented but not over-promoted to subsystems
- [ ] Archive strategy is clear and reversible if needed
- [ ] Git history will preserve chunk archaeology after deletion
