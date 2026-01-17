# Chunk Migration Bootstrap Workflow v2

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
9. Migration Execution Order

**Output**:
- 9 intermediate analysis artifacts (saved for review at each phase)
- Final subsystem proposals with chunk provenance
- Migration plan for backreferences (`# Chunk:` → `# Subsystem:`)
- Prioritized execution order with validation steps

**Key Principle**: Chunks are work-item-sized artifacts that cluster into concept-sized subsystems. This workflow aggregates chunks into wiki pages while preserving their archaeological value in git history.

---

## Key Terminology

This workflow uses specific cluster types. Understand these before proceeding:

| Cluster Type | Definition | Example |
|--------------|------------|---------|
| **Naming cluster** | Chunks sharing a naming prefix | `orch_*` chunks (orch_daemon, orch_scheduling, orch_dashboard) |
| **File cluster** | Chunks sharing >50% of code_references | Chunks all touching src/models.py and src/chunks.py |
| **Capability cluster** | Chunks solving the same business problem | Chunks implementing "parallel agent management" |

These often align but can diverge. The workflow identifies mismatches as signals for boundary refinement.

---

## Chunk Status Handling

Different chunk statuses require different treatment:

| Status | Include in Analysis? | Include in Synthesis? | Notes |
|--------|---------------------|----------------------|-------|
| ACTIVE | Yes, fully | Yes, fully | Primary source of content |
| IMPLEMENTING | Yes, fully | Yes, with caution | Work in progress, may change |
| FUTURE | No | No | Not yet implemented |
| HISTORICAL | Yes, for context | Provenance only | Superseded, archaeological value |
| SUPERSEDED | Yes, for context | Provenance only | Explicitly replaced |

---

## Pre-Execution Verification

Before starting the workflow, verify:

- [ ] All chunk GOAL.md files are readable (no parse errors)
- [ ] Proposed subsystem names don't conflict with existing directories
- [ ] Git working tree is clean (commit or stash changes)
- [ ] All tests pass on current state
- [ ] Backup exists (branch or tag for rollback)

---

## Phase 1: Chunk Inventory & Clustering

**Goal**: Build a comprehensive map of existing chunks and identify natural concept clusters.

**Prompt for agent**:
```
Analyze the existing chunk documentation in docs/chunks/.

1. INVENTORY: For each chunk directory, extract:
   - Chunk name (directory name)
   - Status (from GOAL.md frontmatter: ACTIVE, HISTORICAL, FUTURE, etc.)
   - code_references (from GOAL.md frontmatter)
   - Brief summary of what the chunk accomplishes (from GOAL.md content)

   Filter by status:
   - Include ACTIVE and IMPLEMENTING chunks fully
   - Include HISTORICAL/SUPERSEDED for context (mark as such)
   - Exclude FUTURE chunks (not yet implemented)

2. OVERLAP MATRIX: Build a file-to-chunks mapping:
   - Which files are referenced by multiple chunks?
   - Group chunks that share >50% of their code_references (FILE CLUSTERS)
   - Identify high-touch files (10+ chunk references) as integration points

3. PREFIX CLUSTER ANALYSIS: Identify clusters by naming prefix:
   - Which chunks share a common prefix (e.g., orch_*, task_*, chunk_*)?
   - How well do PREFIX CLUSTERS align with FILE CLUSTERS?
   - Flag mismatches: naming suggests one cluster but file overlap suggests another
     Example: "orch_dashboard shares more files with cli_* than with orch_*"

4. CAPABILITY CLUSTER IDENTIFICATION: Name each cluster by business concept:
   - What domain concept unifies chunks in this cluster?
   - Use business language, not chunk names
   - A cluster of "chunk_frontmatter_model", "chunk_schema_validation",
     "symbolic_code_refs" might be → "Chunk Schema & Validation"

5. ORPHAN DETECTION: Identify:
   - Chunks with no code_references (documentation-only?)
   - Chunks referencing files that no longer exist (stale?)
   - Code files with no chunk references (undocumented?)
   - HISTORICAL chunks that may have valuable context

Output format:

## Chunk Inventory
| Chunk | Status | Files Referenced | Summary |
|-------|--------|------------------|---------|
| ... | ACTIVE | N files | ... |
| ... | HISTORICAL | N files | (superseded by X) |

## File Overlap Analysis
| File | Chunk Count | Chunks Referencing |
|------|-------------|-------------------|
| src/models.py | 27 | chunk_a, chunk_b, ... |

## Prefix Clusters
| Prefix | Chunks | Primary Files |
|--------|--------|---------------|
| orch_* | 8 | src/orchestrator.py, src/worktree.py |

## Prefix vs File Cluster Alignment
| Prefix Cluster | Aligns With File Cluster? | Notes |
|----------------|---------------------------|-------|
| orch_* | Yes | All share orchestrator files |
| task_* | Partial | task_agent shares files with orch_* |

## Capability Clusters
### Cluster: [Concept Name]
- Chunks: [list with status annotations]
- Shared files: [list]
- Prefix alignment: [which prefix clusters map here]
- Rationale: [why these belong together]

## Orphans & Anomalies
- Documentation-only chunks: [list]
- Stale references: [list with specific missing files]
- Undocumented code areas: [list]
- HISTORICAL chunks with context value: [list]
```

**Intermediate output**: Save as `phase1_chunk_inventory.md`

---

## Phase 2: Business Capability Discovery (Chunk-Informed)

**Goal**: Identify business capabilities using chunk clusters as initial hypothesis.

**Prompt for agent**:
```
Using the capability clusters from Phase 1 as starting hypotheses, discover
the business capabilities this system provides.

FOR EACH CAPABILITY CLUSTER from Phase 1:
1. Read the GOAL.md files for chunks in this cluster
2. What business problem do these chunks collectively solve?
3. Who benefits from this capability?
   - End users? Operators? Developers? The system itself?
4. Does the cluster boundary make sense from a business perspective?
   - Should it be split? (multiple distinct user needs)
   - Should it merge with another cluster? (artificial separation)

VALIDATE AGAINST CODE:
1. Do the code_references support the business capability hypothesis?
2. Are there code areas that serve this capability but weren't in chunks?
3. Are there chunks that span multiple business capabilities?
   - These may need to be SPLIT across subsystems

RECONCILE WITH EXISTING SUBSYSTEMS:
(Skip if docs/subsystems/ doesn't exist)
1. Read existing subsystem OVERVIEW.md files
2. For each existing subsystem, compare:
   - Its documented scope vs. chunk-derived capability boundaries
   - Its code_references vs. chunk code_references
   - Its status (DISCOVERING, DOCUMENTED, STABLE, etc.)
3. Note for each existing subsystem:
   - AGREEMENT: chunk analysis confirms subsystem boundaries
   - DIVERGENCE: chunk analysis suggests different boundaries
   - GAP: capability exists with no corresponding subsystem
   - OVERLAP: multiple subsystems cover same capability

DISCOVER UNCLUSTERED CAPABILITIES:
1. Review "undocumented code areas" from Phase 1
2. What business capabilities exist in code but have no chunks?
3. These need subsystems too, even without chunk input

Output format:

## Chunk-Derived Capabilities
### [Capability Name]
- Source clusters: [from Phase 1]
- Contributing chunks: [list with status]
- Business intent: [what problem this solves]
- Beneficiaries: [who uses this capability]
- Validation: [how code supports this]
- Boundary assessment: STRONG / NEEDS_MERGE / NEEDS_SPLIT
- Boundary adjustments: [specific splits/merges if needed]

## Existing Subsystem Reconciliation
(If applicable)
| Existing Subsystem | Status | Chunk Agreement | Notes |
|--------------------|--------|-----------------|-------|
| template_system | STABLE | AGREEMENT | Chunks confirm scope |
| ... | ... | DIVERGENCE | Chunks suggest broader scope |

## Code-Discovered Capabilities
### [Capability Name]
- Code locations: [files/modules]
- Business intent: [what problem this solves]
- Why no chunks: [new code? infrastructure? oversight?]

## Capability Relationships
```
[ASCII diagram showing relationships]

Example:
workflow_artifacts <-- orchestrator (uses)
       |
       v
  cross_repo_tasks (extends)
```

## Proposed Subsystem Structure
| Proposed Subsystem | Source Capabilities | Chunk Count | Confidence |
|--------------------|---------------------|-------------|------------|
| workflow_artifacts | Chunk Lifecycle, ... | 40+ | HIGH |
| orchestrator | Parallel Execution | 21 | HIGH |
```

**Intermediate output**: Save as `phase2_business_capabilities.md`

---

## Phase 3: Entity & Lifecycle Mapping

**Goal**: Map domain entities and their state machines, using chunk content as hints.

**Prompt for agent**:
```
For each business capability, identify the core domain entities.

ENTITY VS VALUE OBJECT:
Distinguish between:
- ENTITY: Has identity, tracked across states, has lifecycle
  Example: Chunk (has identity, tracked across FUTURE->IMPLEMENTING->ACTIVE)
- VALUE OBJECT: Compared by content, no lifecycle, immutable
  Example: SymbolicReference (compared by content, no lifecycle)

USE CHUNK CONTENT AS HINTS:
- Chunk GOAL.md files often describe entities implicitly
- Success criteria may reveal entity states
- Code references point to entity implementations

FOR EACH CAPABILITY:
1. What are the primary ENTITIES? (Things with identity that persist)
   - Look at chunk code_references for model definitions
   - Check for enums that suggest state machines
   - Look for classes with status/state fields

2. What are the VALUE OBJECTS? (Things compared by value)
   - Configuration objects, reference types, DTOs
   - These don't need lifecycle documentation

3. What states can each ENTITY be in?
   - Chunk success criteria often describe state transitions
   - Example: "Chunk can be PLANNED → IMPLEMENTING → ACTIVE"
   - Draw state machine for each entity with 3+ states

4. What relationships exist between entities?
   - Chunk references to multiple models suggest relationships
   - One-to-many, ownership hierarchies
   - Which entity OWNS which?

5. How do chunks document entity behavior?
   - Which chunks describe creation?
   - Which chunks describe state transitions?
   - Which chunks describe validation?

Output format:

## Entity Catalog

### Entities (with identity and lifecycle)

#### [Entity Name]
- Type: ENTITY
- Capability: [which capability owns this]
- Source chunks: [chunks that document this entity]
- States: [STATE_A → STATE_B → STATE_C]
- Key attributes: [important fields]
- Relationships: [owns X, belongs to Y]
- State machine:
  ```
  FUTURE ──create──> IMPLEMENTING ──complete──> ACTIVE
                           │
                           └──abandon──> ABANDONED
  ```

### Value Objects (no lifecycle)

#### [Value Object Name]
- Type: VALUE_OBJECT
- Capability: [which capability uses this]
- Purpose: [what it represents]
- Compared by: [which fields determine equality]

## Entity Relationship Diagram
```
[ASCII diagram showing entity relationships]

Example:
Narrative ──contains──> Chunk ──references──> SymbolicReference
    │                     │
    └──────────> Subsystem <───implements───┘
```

## Chunk-to-Entity Mapping
| Chunk | Entities Affected | Aspect Documented |
|-------|-------------------|-------------------|
| chunk_create | Chunk | Creation, initial state |
| chunk_validate | Chunk, SymbolicReference | Validation rules |
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
- "Only one IMPLEMENTING chunk allowed" → concurrency rule

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
   - Repository-level isolation

4. What consistency rules exist?
   - Cross-entity constraints
   - Calculation rules
   - Ordering requirements

CONFLICT DETECTION:
- Do any chunks document contradictory rules?
- Are there rules in code not documented in chunks?
- Are there chunk rules not enforced in code?

CONFLICT RESOLUTION STRATEGIES:
When conflicts are found:

1. Overlapping success criteria:
   - If semantically identical → dedupe to single invariant
   - If semantically different → keep both with attribution
     Example: "Reference format must be symbolic (from symbolic_code_refs)"

2. Contradictory statements:
   - Check HISTORICAL status - one chunk may supersede the other
   - Check created_after ordering - newer chunk wins
   - If both ACTIVE, flag for human decision with both statements

3. Example conflict resolution:
   - chunk_a (HISTORICAL): "Line numbers are acceptable"
   - chunk_b (ACTIVE): "Only symbolic references allowed"
   Resolution: Use chunk_b (chunk_a is HISTORICAL, superseded)

Output format:

## Business Rules by Capability

### [Capability Name]

#### State Rules
| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| Only valid transitions allowed | chunk_x success criteria | src/validation.py:45 |

#### Validation Rules
| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| References must be symbolic | chunk_y success criteria | src/models.py:123 |

#### Concurrency Rules
| Rule | Source | Enforcement Location |
|------|--------|---------------------|
| One IMPLEMENTING per repo | chunk_z success criteria | src/chunks.py:89 |

## Rule Conflicts
| Rule A | Rule B | Status | Resolution |
|--------|--------|--------|------------|
| "Line numbers OK" (chunk_a) | "Symbolic only" (chunk_b) | RESOLVED | chunk_b wins (chunk_a HISTORICAL) |
| "X required" | "X optional" | UNRESOLVED | Flag for human decision |

## Rules in Code Not in Chunks
| Rule | Code Location | Suggested Documentation |
|------|---------------|------------------------|
| Max 100 chunks per repo | src/limits.py:12 | Add to workflow_artifacts invariants |
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
   - See GRANULARITY EXAMPLES below

GRANULARITY DECISION CRITERIA:
- Merge if: always change together, shared vocabulary, same entity lifecycle
- Split if: distinct user workflows, different change cadence, different owners

GRANULARITY EXAMPLES:

MERGE these (same capability, shared entities):
- chunk_frontmatter_model + chunk_validate + chunk_list_command
  → All serve "chunk lifecycle" capability
  → Same entity (Chunk), same status model
  → Would always change together when Chunk model changes

KEEP together despite different touchpoints:
- orch_dashboard (operator-facing UI)
- orch_scheduling (internal algorithm)
  → Same capability ("parallel execution")
  → Different user types is OK within same subsystem
  → Would create artificial boundary if split

KEEP separate (different capabilities):
- workflow_artifacts vs. orchestrator
  → Different entities (Chunk vs WorkUnit)
  → Different change cadence (stable vs active development)
  → Different primary users (all users vs parallel-work users)
  → Clear ownership boundary

NAMING:
- Use business language from Phase 2
- Prefer nouns over verbs
- ✓ "artifact_ordering" (what it manages)
- ✗ "ordering_implementation" (too technical)
- ✓ "workflow_artifacts" (business domain)
- ✗ "chunk_management" (too generic)

CHUNK ASSIGNMENT:
- For each proposed subsystem, list contributing chunks
- Some chunks may contribute to multiple subsystems (split content)
- Some chunks may be deprecated (superseded by others)
- Note HISTORICAL chunks for provenance only

Output format:

## Proposed Subsystems

### [Subsystem Name]
- Business intent: [from Phase 2]
- Core entities: [from Phase 3]
- Key invariants: [from Phase 4, top 3-5]
- Contributing chunks:
  | Chunk | Status | Disposition | Notes |
  |-------|--------|-------------|-------|
  | chunk_a | ACTIVE | fully absorbed | All content relevant |
  | chunk_b | ACTIVE | partial | Validation rules only; schema → other subsystem |
  | chunk_c | HISTORICAL | provenance only | Superseded by chunk_d |
  | chunk_d | ACTIVE | fully absorbed | |
- Code locations: [consolidated code_references]
- Existing subsystem: [if reconciling with existing, note agreement/changes]

## Granularity Decisions Log
| Decision | Rationale |
|----------|-----------|
| Merged chunk_x + chunk_y into subsystem_a | Same entity lifecycle, always change together |
| Kept subsystem_a separate from subsystem_b | Different entities, different change cadence |

## Chunk Disposition Summary
| Chunk | Status | Disposition | Target Subsystem(s) |
|-------|--------|-------------|---------------------|
| chunk_a | ACTIVE | absorbed | subsystem_x |
| chunk_b | ACTIVE | split | subsystem_x (rules), subsystem_y (schema) |
| chunk_c | HISTORICAL | provenance | subsystem_x |
| chunk_d | ACTIVE | deprecated | n/a (superseded by chunk_e) |
```

**Intermediate output**: Save as `phase5_domain_boundaries.md`

---

## Phase 6: Infrastructure Annotation

**Goal**: Identify cross-cutting infrastructure patterns as supporting material.

**Prompt for agent**:
```
Identify cross-cutting infrastructure patterns.

INFRASTRUCTURE VS DOMAIN:
- Domain subsystems: owned by business capabilities, have entities
- Infrastructure: serves multiple domains equally, no domain-specific entities

COMMON INFRASTRUCTURE PATTERNS:
- Logging, tracing, metrics
- Authentication, authorization
- Caching, persistence patterns
- Error handling, validation frameworks
- CLI framework, argument parsing
- Template rendering

FOR EACH PATTERN:
1. Which subsystems use it?
2. Is it consistent or fragmented across subsystems?
3. Are there chunks that document infrastructure?
   - These chunks may not map to domain subsystems
   - They may become "Supporting Patterns" documentation

SUBSYSTEM OR SUPPORTING PATTERN?
Only promote infrastructure to full subsystem if ALL are true:
- Has complex business rules (not just technical patterns)
- Engineers frequently misunderstand it
- Has known deviations that need tracking
- Would benefit from DISCOVERING → STABLE lifecycle

Usually: infrastructure → "Supporting Patterns" section in repo docs

HANDLING INFRASTRUCTURE CHUNKS:
- Infrastructure chunks don't map to domain subsystems
- Options:
  a) Fold into "Supporting Patterns" documentation
  b) Create thin infrastructure subsystem if complex enough
  c) Archive with git history preservation

Output format:

## Infrastructure Patterns

### [Pattern Name]
- Used by subsystems: [list]
- Documented in chunks: [list or "none"]
- Consistency: CONSISTENT / FRAGMENTED / VARIES_BY_SUBSYSTEM
- Complexity: LOW / MEDIUM / HIGH
- Recommendation: SUPPORTING_PATTERN / SUBSYSTEM
- Rationale: [why this recommendation]

## Infrastructure Chunk Disposition
| Chunk | Pattern | Recommendation | Rationale |
|-------|---------|----------------|-----------|
| template_rendering | Template system | SUBSYSTEM | Complex, has deviations |
| error_handling | Error patterns | SUPPORTING_PATTERN | Simple, consistent |
| cli_framework | CLI patterns | SUPPORTING_PATTERN | Framework usage only |

## Supporting Patterns Summary
(For inclusion in repo documentation)

| Pattern | Purpose | Status | Notes |
|---------|---------|--------|-------|
| Error Handling | Standardized exceptions | Consistent | See src/errors.py |
| CLI Framework | Click-based commands | Consistent | Standard patterns |
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
4. Identify template-rendered files (need special handling)

TEMPLATE FILE HANDLING:
- If a file has AUTO-GENERATED header, it's rendered from a template
- Update the SOURCE template, not the rendered file
- Template backreferences may use different syntax:
  - Jinja2: {# Subsystem: name #}
  - Or standard comment in template output

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
   Review the code location. Usually one subsystem is primary.
   Use single reference to PRIMARY subsystem:
   `# Subsystem: primary_subsystem`
   (Secondary relationships captured in subsystem OVERVIEW.md code_references)

4. Chunk reference with no target subsystem:
   - Infrastructure chunk → remove backreference (infrastructure has no backref)
   - Deprecated chunk → remove backreference
   - Orphan code → add to appropriate subsystem or mark as infrastructure

GRANULARITY DECISIONS:
- MODULE level: entire file serves one subsystem → comment at top
- CLASS level: class within multi-concern file → comment above class
- FUNCTION level: only specific functions → comment above function

NEW BACKREFERENCES:
- Code areas discovered in Phase 2 that need subsystem refs
- Apply same granularity rules

Output format:

## Backreference Migration Plan

### Subsystem: [name]

#### Migrations
| File | Current Refs | Action | New Ref | Granularity |
|------|--------------|--------|---------|-------------|
| src/foo.py | # Chunk: a, b | consolidate | # Subsystem: name | MODULE |
| src/bar.py | (none) | add | # Subsystem: name | CLASS |
| src/baz.py | # Chunk: c | replace | # Subsystem: name | FUNCTION |

#### Template Files (special handling)
| Rendered File | Source Template | Action |
|---------------|-----------------|--------|
| CLAUDE.md | src/templates/CLAUDE.md.jinja2 | Update template |

### Removals
| File | Current Ref | Reason |
|------|-------------|--------|
| src/util.py | # Chunk: infra_x | Infrastructure, no backref needed |
| src/old.py | # Chunk: deprecated_y | Chunk deprecated |

## Migration Priority Order

Priority 1: HIGH IMPACT, LOW RISK
- Files with 10+ chunk refs (maximum consolidation benefit)
- Self-contained subsystems (orchestrator)

Priority 2: MEDIUM IMPACT, MEDIUM RISK
- Core model files (higher coupling)
- Files shared across 2-3 subsystems

Priority 3: HIGH COUPLING, MIGRATE LAST
- CLI entry points (highest touch)
- Cross-cutting utilities

| Priority | Files | Subsystem | Risk Level |
|----------|-------|-----------|------------|
| 1 | src/orchestrator.py, src/worktree.py | orchestrator | LOW |
| 2 | src/models.py, src/chunks.py | workflow_artifacts | MEDIUM |
| 3 | src/ve.py | multiple | HIGH |

## Validation Steps

After each priority group:
1. Run: `grep -r "# Chunk:" src/` - count should decrease
2. Verify: Each migrated file has at most one `# Subsystem:` comment
3. Verify: Subsystem OVERVIEW.md code_references match migrated files
4. Run: Full test suite passes

## Rollback Strategy
- Keep chunk directories until ALL validation passes
- Git history preserves all chunk content
- If issues found: revert backreference commits, investigate

## Migration Statistics
- Files with chunk refs: N
- Refs to consolidate: M
- Refs to remove: P
- New refs to add: Q
- Template files requiring update: R
```

**Intermediate output**: Save as `phase7_backreference_plan.md`

---

## Phase 8: Chunk Synthesis & Archive

**Goal**: Synthesize subsystem documentation from chunk content, producing partially-complete templates that show what's automated vs. what needs human refinement.

**Prompt for agent**:
```
Create subsystem OVERVIEW.md files by synthesizing chunk GOAL.md files.

IMPORTANT: Produce ACTUAL FILES, not just descriptions. Each subsystem gets
a real OVERVIEW.md file saved to the output directory.

FOR EACH SUBSYSTEM:

1. Gather contributing chunks (from Phase 5)
   - ACTIVE/IMPLEMENTING: full content synthesis
   - HISTORICAL: provenance list only

2. Extract from each ACTIVE chunk GOAL.md:
   - Problem statement → contributes to Intent
   - Success criteria → contributes to Invariants
   - Code references → validates code_references list
   - Rationale/context → contributes to Scope

3. Create OVERVIEW.md file with CONFIDENCE MARKERS:

   Use these markers to indicate synthesis confidence:
   - [SYNTHESIZED]: Content extracted directly from chunks, high confidence
   - [INFERRED]: Content derived from chunk patterns, medium confidence
   - [NEEDS_HUMAN]: Placeholder requiring human input, low/no confidence
   - [CONFLICT]: Multiple chunks disagree, human resolution needed

   File template:
   ```markdown
   ---
   status: DOCUMENTED
   # MIGRATION NOTE: This subsystem was synthesized from chunks.
   # Review all [NEEDS_HUMAN] and [CONFLICT] sections before finalizing.
   # Confidence: X% synthesized, Y% inferred, Z% needs human input
   chunks:
     - name: chunk_a
       relationship: implements
     - name: chunk_b
       relationship: implements
   ---

   ## Intent

   <!-- SYNTHESIS CONFIDENCE: HIGH/MEDIUM/LOW -->

   [SYNTHESIZED] Primary purpose extracted from chunk problem statements:
   [Direct quote or synthesis from chunks]

   [NEEDS_HUMAN] Business context and strategic importance:
   <!-- Why does this subsystem matter to the organization? -->
   <!-- What would break if this subsystem didn't exist? -->

   ## Scope

   ### In Scope
   <!-- SYNTHESIS CONFIDENCE: MEDIUM -->

   [INFERRED] Based on chunk code_references and success criteria:
   - [capability derived from chunks]
   - [capability derived from chunks]

   [NEEDS_HUMAN] Clarify boundaries:
   <!-- Are there edge cases not covered by chunks? -->

   ### Out of Scope
   <!-- SYNTHESIS CONFIDENCE: LOW -->

   [NEEDS_HUMAN] What explicitly does NOT belong here:
   <!-- This is rarely documented in chunks -->
   <!-- List capabilities that might seem related but belong elsewhere -->

   ## Invariants

   <!-- SYNTHESIS CONFIDENCE: HIGH -->

   [SYNTHESIZED] From chunk success criteria:
   1. [Exact success criterion from chunk_a]
      Source: chunk_a
   2. [Exact success criterion from chunk_b]
      Source: chunk_b

   [CONFLICT] Contradictory requirements found:
   - chunk_x says: "[statement]"
   - chunk_y says: "[contradictory statement]"
   <!-- Human decision required -->

   [NEEDS_HUMAN] Implicit invariants not in chunks:
   <!-- What rules exist in code but weren't documented? -->

   ## Code References

   <!-- SYNTHESIS CONFIDENCE: HIGH -->

   [SYNTHESIZED] Consolidated from chunk code_references:
   - `src/path/file.py#ClassName` - [description from chunk]
   - `src/path/other.py#function_name` - [description from chunk]

   [INFERRED] Additional references found in code but not in chunks:
   - `src/path/discovered.py` - [inferred purpose]

   [NEEDS_HUMAN] Validate these references are current:
   <!-- Some chunk references may be stale -->

   ## Deviations

   <!-- SYNTHESIS CONFIDENCE: LOW -->

   [NEEDS_HUMAN] Known deviations from ideal:
   <!-- Chunks rarely document what's wrong -->
   <!-- List known technical debt, inconsistencies -->

   ## Chunk Provenance

   This subsystem was synthesized from the following chunks:

   | Chunk | Status | Contribution | Confidence |
   |-------|--------|--------------|------------|
   | chunk_a | ACTIVE | Intent, Invariants 1-2 | HIGH |
   | chunk_b | ACTIVE | Invariants 3-4, Code refs | HIGH |
   | chunk_c | HISTORICAL | (superseded by chunk_b) | N/A |

   ## Synthesis Metrics

   | Section | Synthesized | Inferred | Needs Human | Conflicts |
   |---------|-------------|----------|-------------|-----------|
   | Intent | 1 | 0 | 1 | 0 |
   | Scope | 0 | 2 | 2 | 0 |
   | Invariants | 4 | 0 | 1 | 1 |
   | Code References | 8 | 2 | 1 | 0 |
   | Deviations | 0 | 0 | 1 | 0 |
   | **Total** | **13** | **4** | **6** | **1** |

   **Overall Confidence**: X% (synthesized / total non-conflict items)
   ```

4. SAVE ACTUAL FILES:
   - Create directory: [output_dir]/subsystems/[subsystem_name]/
   - Write OVERVIEW.md with above template
   - This produces real, editable files for human review

5. Handle content conflicts:

   CONFLICT RESOLUTION:

   Overlapping success criteria:
   - If semantically identical → dedupe to single invariant
   - If semantically different → keep both with attribution
     Example: "References must be symbolic (from symbolic_code_refs)"

   Contradictory statements:
   - Check chunk status: HISTORICAL loses to ACTIVE
   - Check created_after ordering: newer chunk wins
   - If both ACTIVE and unresolved → flag for human decision

   Example resolution:
   - chunk_a (HISTORICAL): "Line numbers are acceptable"
   - chunk_b (ACTIVE): "Only symbolic references allowed"
   → Use chunk_b statement, note chunk_a in provenance as superseded

5. Validate synthesized content:
   - Does Intent answer "what problem does this solve?"
   - Do Invariants match actual code behavior?
   - Are code_references accurate and current?

ARCHIVE STRATEGY:

Recommendation: DELETE chunks after successful migration
- Subsystem captures all documentation value
- Git history preserves archaeology (`git log --all -- docs/chunks/chunk_name/`)
- Provenance section in subsystem links to chunk history
- Cleanest repository state

Alternative (if nervous): ARCHIVE chunks temporarily
- Move to docs/archive/chunks/
- Delete after 30 days if no issues
- Clutters repository during transition

Output format:

## Subsystem Documentation Drafts

### docs/subsystems/[name]/OVERVIEW.md

```markdown
[Full draft of synthesized OVERVIEW.md]
```

**Synthesis Notes:**
- Intent sourced from: chunk_a problem statement, chunk_b rationale
- Invariants sourced from: chunk_a success criteria (3), chunk_b success criteria (2)
- Code references: consolidated from 5 chunks, validated against current code

**Conflicts Resolved:**
| Conflict | Resolution | Rationale |
|----------|------------|-----------|
| "X required" vs "X optional" | "X required" | chunk_b is newer |

**Conflicts Requiring Human Decision:**
| Conflict | Options | Chunks Involved |
|----------|---------|-----------------|
| [description] | A or B | chunk_x, chunk_y |

### [Next subsystem...]

## Archive Plan

| Chunk | Status | Disposition | Notes |
|-------|--------|-------------|-------|
| chunk_a | ACTIVE | delete after migration | Fully synthesized into subsystem_x |
| chunk_b | ACTIVE | delete after migration | Fully synthesized into subsystem_x |
| chunk_c | HISTORICAL | delete after migration | Provenance preserved in subsystem_x |
| chunk_d | ACTIVE | keep temporarily | Conflicts need resolution |

## Post-Migration Verification
- [ ] All subsystem OVERVIEW.md files created
- [ ] All code_references validated against actual files
- [ ] Chunk provenance sections complete
- [ ] No unresolved content conflicts
```

**Intermediate output**: Save as `phase8_synthesis_archive.md`

---

## Phase 9: Migration Execution Order

**Goal**: Define the order and validation for executing the migration.

**Prompt for agent**:
```
Create a prioritized execution plan for the migration.

PRIORITIZATION CRITERIA:
1. Risk level (self-contained = low risk, high coupling = high risk)
2. Validation ease (can we verify correctness easily?)
3. Dependencies (does subsystem A depend on B being migrated first?)

EXECUTION ORDER PRINCIPLES:

Priority 1: STABLE, SELF-CONTAINED subsystems
- Already well-bounded (existing subsystems with STABLE status)
- Low coupling to other subsystems
- Validates migration process with low risk
- Example: template_system

Priority 2: WELL-CLUSTERED capabilities
- Clear boundaries from chunk analysis
- Moderate coupling
- Self-contained tests possible
- Example: orchestrator

Priority 3: CORE DOMAIN subsystems
- Highest coupling
- Most chunks to synthesize
- Requires most validation
- Example: workflow_artifacts

FOR EACH SUBSYSTEM IN ORDER:

1. Pre-migration checklist:
   - [ ] Subsystem OVERVIEW.md draft reviewed
   - [ ] Code references validated
   - [ ] Conflicts resolved
   - [ ] Tests passing

2. Migration steps:
   a. Create subsystem directory (if new)
   b. Write OVERVIEW.md
   c. Update code backreferences
   d. Run validation checks
   e. Commit with clear message

3. Post-migration validation:
   - [ ] Subsystem OVERVIEW.md exists and is valid
   - [ ] Code backreferences updated
   - [ ] No orphan `# Chunk:` references for migrated chunks
   - [ ] Tests passing

4. Chunk cleanup:
   - Delete migrated chunk directories
   - Commit deletion separately (for clean git history)

Output format:

## Migration Execution Order

### Phase A: Validate Migration Process
Subsystems: [list stable, low-risk subsystems]
Goal: Prove the migration process works

| Step | Action | Validation |
|------|--------|------------|
| A.1 | Create template_system OVERVIEW.md | File exists, valid YAML |
| A.2 | Update template file backreferences | grep finds new refs |
| A.3 | Run tests | All pass |
| A.4 | Delete template_system chunks | Directories removed |
| A.5 | Run tests again | All pass |

### Phase B: Migrate Self-Contained Subsystems
Subsystems: [list well-clustered subsystems]
Goal: Migrate clear-boundary subsystems

[Same step structure]

### Phase C: Migrate Core Domain
Subsystems: [list high-coupling subsystems]
Goal: Complete migration

[Same step structure]

### Phase D: Cleanup
Goal: Remove migration artifacts, final validation

| Step | Action | Validation |
|------|--------|------------|
| D.1 | Remove any remaining chunk directories | docs/chunks/ empty or removed |
| D.2 | Update CLAUDE.md if needed | No chunk workflow references |
| D.3 | Full test suite | All pass |
| D.4 | Manual review | Subsystems readable, complete |

## Rollback Procedures

If issues at any phase:

| Phase | Rollback Action |
|-------|-----------------|
| A (any step fails) | `git reset --hard HEAD~N` to before Phase A |
| B (any step fails) | Keep Phase A, revert Phase B commits |
| C (any step fails) | Keep A+B, revert Phase C commits |
| D (cleanup fails) | Restore chunk directories from git |

## Success Criteria

Migration is complete when:
- [ ] All subsystem OVERVIEW.md files exist and are valid
- [ ] All code backreferences use `# Subsystem:` (no `# Chunk:`)
- [ ] docs/chunks/ directory is empty or removed
- [ ] All tests pass
- [ ] Documentation is coherent and navigable
```

**Intermediate output**: Save as `phase9_execution_order.md`

---

## Final Report Format

After all phases, produce a consolidated report:

```markdown
# Chunk Migration Report

## Executive Summary
- Chunks analyzed: N (M ACTIVE, P HISTORICAL)
- Subsystems created: Q (R new, S updated)
- Code files migrated: T
- Backreferences updated: U

## Migration Map

### Chunk → Subsystem Mapping
| Chunk | Status | Target Subsystem | Disposition |
|-------|--------|------------------|-------------|
| chunk_a | ACTIVE | subsystem_x | absorbed |
| chunk_b | ACTIVE | subsystem_x, subsystem_y | split |
| chunk_c | HISTORICAL | subsystem_x | provenance only |

### Subsystem Summary
| Subsystem | Status | Intent | Chunks Absorbed | Code Locations |
|-----------|--------|--------|-----------------|----------------|
| subsystem_x | NEW | [brief] | N | M files |
| subsystem_y | UPDATED | [brief] | P | Q files |

## Subsystem Documentation

[For each subsystem: final OVERVIEW.md content]

## Backreference Migration Summary

| Metric | Count |
|--------|-------|
| Files with `# Chunk:` before | N |
| Files with `# Subsystem:` after | M |
| Backreferences consolidated | P |
| Backreferences removed (infrastructure) | Q |
| New backreferences added | R |

## Execution Log

[Summary of what was done in each phase]

## Validation Results

| Check | Result |
|-------|--------|
| All subsystems created | PASS |
| All backreferences migrated | PASS |
| All tests passing | PASS |
| No orphan chunk references | PASS |

## Human Effort Required

Summary of what was automated vs. what needs human refinement:

### Synthesis Confidence by Subsystem

| Subsystem | Synthesized | Inferred | Needs Human | Conflicts | Confidence |
|-----------|-------------|----------|-------------|-----------|------------|
| subsystem_a | 15 | 3 | 4 | 0 | 82% |
| subsystem_b | 12 | 5 | 6 | 2 | 68% |
| subsystem_c | 8 | 2 | 8 | 1 | 53% |
| **Total** | **35** | **10** | **18** | **3** | **68%** |

### Human Tasks by Category

| Category | Count | Estimated Effort | Priority |
|----------|-------|------------------|----------|
| Conflict resolution | 3 | 15 min each | HIGH |
| Business context (Intent) | 4 | 10 min each | MEDIUM |
| Scope clarification | 6 | 5 min each | MEDIUM |
| Deviation documentation | 4 | 10 min each | LOW |
| Reference validation | 8 | 2 min each | LOW |

### Effort Estimate

- **Automated work**: ~X hours saved (chunk reading, consolidation, conflict detection)
- **Human review needed**: ~Y hours (conflict resolution, business context, validation)
- **Overall automation rate**: Z%

### Files Requiring Human Review

Priority order for human review:

1. **HIGH** (conflicts or low confidence):
   - `subsystems/subsystem_b/OVERVIEW.md` - 2 conflicts, 68% confidence
   - `subsystems/subsystem_c/OVERVIEW.md` - 1 conflict, 53% confidence

2. **MEDIUM** (needs business context):
   - `subsystems/subsystem_a/OVERVIEW.md` - Intent needs enrichment

3. **LOW** (validation only):
   - All subsystems: verify code_references are current

## Lessons Learned

[Any issues encountered, decisions made, recommendations for next migration]
```

---

## Intermediate Output Summary

| Phase | Output File | Purpose |
|-------|-------------|---------|
| 1 | `phase1_chunk_inventory.md` | Chunk map, all cluster types |
| 2 | `phase2_business_capabilities.md` | Chunk-informed capability discovery |
| 3 | `phase3_entity_lifecycle.md` | Entity/value object mapping |
| 4 | `phase4_business_rules.md` | Invariants with conflict resolution |
| 5 | `phase5_domain_boundaries.md` | Subsystem boundaries with granularity decisions |
| 6 | `phase6_infrastructure.md` | Infrastructure patterns |
| 7 | `phase7_backreference_plan.md` | Migration plan with priorities |
| 8 | `phase8_synthesis_archive.md` | Synthesized docs and archive plan |
| 9 | `phase9_execution_order.md` | Prioritized execution plan |
| Final | `chunk_migration_report.md` | Complete migration report |

---

## Cross-Repository Considerations

When working with task directories spanning multiple repositories:

1. **Subsystems can reference multiple repos**: Use repo prefixes in code_references
   ```markdown
   ## Code References
   - `platform:src/billing/` - Backend billing logic
   - `platform-web:src/features/billing/` - Billing UI
   ```

2. **Chunks may reference external code**: These cannot be migrated directly
   - Document external references in subsystem OVERVIEW.md
   - External code keeps its own backreference strategy

3. **Repository boundaries matter**: Subsystem scope should respect repo boundaries
   - A subsystem can DOCUMENT cross-repo concepts
   - But code_references should be scoped to the current repo
   - External references are informational, not governing

---

## Validation Checklist

Before executing migration:

- [ ] Every chunk is accounted for (absorbed, split, provenance, or deprecated)
- [ ] Every subsystem has clear business intent (not technical description)
- [ ] Chunk success criteria are preserved as subsystem invariants
- [ ] Backreference migration plan covers all `# Chunk:` comments
- [ ] Infrastructure is documented but not over-promoted to subsystems
- [ ] Template files identified and handled appropriately
- [ ] Conflict resolution complete (no UNRESOLVED conflicts)
- [ ] Execution order respects dependencies
- [ ] Rollback procedures documented
- [ ] Git history will preserve chunk archaeology after deletion
