---
status: SOLVED
trigger: "Bidirectional links between artifacts rely on developer caution; no mechanical guarantee of referential integrity"
proposed_chunks:
  - prompt: "Add `ve validate` command that runs referential integrity validation across all artifacts and code backreferences"
    chunk_directory: docs/chunks/integrity_validate
    depends_on: []
  - prompt: "Validate code backreferences point to existing artifacts (# Chunk: and # Subsystem: comments)"
    chunk_directory: docs/chunks/integrity_code_backrefs
    depends_on: [0]
  - prompt: "Validate proposed_chunks references in narratives, investigations, and friction log"
    chunk_directory: docs/chunks/integrity_proposed_chunks
    depends_on: [0]
  - prompt: "Add bidirectional consistency warnings (chunk→parent without parent→chunk)"
    chunk_directory: docs/chunks/integrity_bidirectional
    depends_on: [0, 1, 2]
  - prompt: "Fix existing 18 integrity violations in current codebase"
    chunk_directory: docs/chunks/integrity_fix_existing
    depends_on: [0]
  - prompt: "Add /validate-fix slash command that iteratively runs validation and fixes errors until all checks pass"
    chunk_directory: docs/chunks/integrity_validate_fix_command
    depends_on: [0, 1, 2, 3]
created_after: ["claudemd_progressive_disclosure"]
---

<!--
DO NOT DELETE THIS COMMENT until the investigation reaches a terminal status.
This documents the frontmatter schema and guides investigation workflow.

STATUS VALUES:
- ONGOING: Investigation is active; exploration and analysis in progress
- SOLVED: The investigation question has been answered. If proposed_chunks exist,
  implementation work remains—SOLVED indicates the investigation is complete, not
  that all resulting work is done.
- NOTED: Findings documented but no action required; kept for future reference
- DEFERRED: Investigation paused; may be revisited later when conditions change

TRIGGER:
- Brief description of what prompted this investigation
- Examples:
  - "Test failures in CI after dependency upgrade"
  - "User reported slow response times on dashboard"
  - "Exploring whether GraphQL would simplify our API"
- The trigger naturally captures whether this is an issue (problem to solve)
  or a concept (opportunity to explore)

PROPOSED_CHUNKS:
- Starts empty; entries are added if investigation reveals actionable work
- Each entry records a chunk prompt for work that should be done
- Format: list of {prompt, chunk_directory, depends_on} where:
  - prompt: The proposed chunk prompt text
  - chunk_directory: Populated when/if the chunk is actually created via /chunk-create
  - depends_on: Optional array of integer indices expressing implementation dependencies.

    SEMANTICS (null vs empty distinction):
    | Value           | Meaning                                 | Oracle behavior |
    |-----------------|----------------------------------------|-----------------|
    | omitted/null    | "I don't know dependencies for this"  | Consult oracle  |
    | []              | "Explicitly has no dependencies"       | Bypass oracle   |
    | [0, 2]          | "Depends on prompts at indices 0 & 2"  | Bypass oracle   |

    - Indices are zero-based and reference other prompts in this same array
    - At chunk-create time, index references are translated to chunk directory names
    - Use `[]` when you've analyzed the chunks and determined they're independent
    - Omit the field when you don't have enough context to determine dependencies
- Unlike narrative chunks (which are planned upfront), these emerge from investigation findings
-->

## Trigger

The vibe-engineer workflow creates bidirectional links between artifacts (chunks, code, narratives, investigations, subsystems) but the only thing ensuring their integrity is developer caution. As the reference graph grows, the risk of broken or inconsistent links increases.

Examples of current link types:
- Chunk ↔ Code backreferences (code comments pointing to chunks, chunk GOAL.md referencing code locations)
- Chunk → Narrative/Investigation (frontmatter references)
- Narrative → Chunks (proposed_chunks with chunk_directory references)
- Investigation → Chunks (proposed_chunks)
- Subsystem ↔ Code backreferences

Without mechanical validation, links can become stale (referenced artifact deleted/moved), asymmetric (A→B exists but B→A missing), or orphaned (pointing to non-existent targets).

## Success Criteria

1. **Complete map of all link types**: Document every edge type in the reference graph (chunk↔code, chunk→narrative, etc.) with their directionality and current validation status
2. **Evaluate enforcement mechanisms**: Compare approaches (database with FK constraints, file-based validation, git hooks, CI checks) with their trade-offs
3. **Recommendation**: Propose whether and how to implement mechanical validation, with enough detail to create implementation chunks

## Testable Hypotheses

### H1: A lightweight SQLite database can track all link types without disrupting the current file-based workflow

- **Rationale**: SQLite is embedded, requires no server, and supports FK constraints natively
- **Test**: Prototype a schema that models the reference graph; evaluate if all link types fit
- **Status**: VERIFIED (schema fits, but sync complexity is significant)
- **Evidence**: See `prototypes/schema.sql` - all 12 link types modeled with FK constraints. However, keeping DB in sync with files requires either file watching, git hooks, or on-demand sync. Files remain authoritative, making DB a derived/redundant data store.

### H2: File-based validation (parsing YAML frontmatter + scanning code comments) is sufficient and avoids database sync complexity

- **Rationale**: Links already exist in files; a validator could traverse and check without duplicating state
- **Test**: Prototype a validator that detects broken/asymmetric links in the current codebase
- **Status**: VERIFIED (working prototype found 18 real issues)
- **Evidence**: See `prototypes/file_validator.py` - builds in-memory graph on each run, validates all link types. Found 18 referential integrity issues in current codebase (mostly bidirectional consistency violations).

### H3: Git hooks (pre-commit or pre-push) are the right enforcement point

- **Rationale**: Catches violations before the repo; familiar developer workflow
- **Test**: Evaluate whether validation can run fast enough for pre-commit (<2-3 seconds)
- **Status**: VERIFIED (296ms for full validation)
- **Evidence**: Timed the file-based validator on this codebase (171 chunks, 23 source files with backrefs): 282ms for artifacts, 14ms for code, <1ms for validation. Total ~300ms, well under pre-commit threshold.

## Exploration Log

### 2026-01-31: Complete Reference Graph Mapping

Audited the codebase to identify all link types. Found 12 distinct edge types:

**Chunk Outbound Links (all validated):**
| Link | Frontmatter Field | Validation Function |
|------|-------------------|---------------------|
| Chunk → Narrative | `narrative: str` | `validate_narrative_ref()` |
| Chunk → Investigation | `investigation: str` | `validate_investigation_ref()` |
| Chunk → Friction Entries | `friction_entries: list` | `validate_friction_entries_ref()` |
| Chunk → Subsystems | `subsystems: list` | `validate_subsystem_refs()` |
| Chunk → Code | `code_references: list` | `_validate_symbol_exists()` |

**Code Backreferences (parsing only, NO validation):**
| Link | Pattern | Location |
|------|---------|----------|
| Code → Chunk | `# Chunk: docs/chunks/...` | `CHUNK_BACKREF_PATTERN` in chunks.py:1473 |
| Code → Subsystem | `# Subsystem: docs/subsystems/...` | `SUBSYSTEM_BACKREF_PATTERN` in chunks.py:1475 |

**Parent Artifact → Chunk Links (NO validation):**
| Link | Field | Location |
|------|-------|----------|
| Narrative → Chunks | `proposed_chunks[].chunk_directory` | narratives.py |
| Investigation → Chunks | `proposed_chunks[].chunk_directory` | investigations.py |
| Friction → Chunks | `proposed_chunks[].chunk_directory` | friction.py |

**Other Links:**
| Link | Field | Validated? |
|------|-------|------------|
| Subsystem → Chunks | `chunks: list` | YES - `validate_chunk_refs()` |
| Any Artifact → Artifacts | `created_after: list` | NO |

**Key Finding:** Significant validation asymmetry exists:
- Chunk outbound links: ALL validated
- Code backreferences: NOT validated (chunk/subsystem may not exist)
- Parent→chunk links: NOT validated (chunk_directory may be stale)
- Bidirectional consistency: NOT checked (A→B doesn't verify B→A)

### 2026-01-31: SQLite Schema Prototype

Created `prototypes/schema.sql` modeling the complete reference graph. Key observations:
- All 12 link types fit naturally into relational schema
- FK constraints provide automatic validation
- Views can detect asymmetric links efficiently

**Complexity concern:** Sync between files and database. Files are authoritative, so DB is derived state. Options:
1. On-demand sync via `ve validate` (simplest)
2. Git hook sync (pre-commit rebuilds DB)
3. File watcher (complex, needs daemon)

Decided sync complexity outweighs FK constraint benefits for this use case.

### 2026-01-31: File-Based Validator Prototype

Created `prototypes/file_validator.py` implementing stateless validation. Tested on current codebase:

```
Scanning artifacts...
  Chunks: 171, Narratives: 8, Investigations: 15, Subsystems: 6
Scanning code backreferences...
  Files with chunk backrefs: 23 (114 total refs)
  Files with subsystem backrefs: 32 (53 total refs)
Validating referential integrity...
  Errors found: 18
```

**Actual issues found:**
1. Malformed investigation ref: `docs/investigations/task_agent_experience` (should be just `task_agent_experience`)
2. 17 bidirectional consistency violations: chunks claim parent artifacts that don't list them

### 2026-01-31: Performance Benchmarking

Timed the file-based validator:
```
scan_artifacts:     282ms
scan_code_backrefs:  14ms
validate_graph:      <1ms
---
Total:              296ms
```

**Conclusion:** File-based validation is fast enough for pre-commit hooks. Even with 10x growth, would stay under 3 seconds.

## Findings

### Verified Findings

1. **12 distinct link types exist** in the reference graph (see Exploration Log for complete mapping)

2. **Significant validation asymmetry exists:**
   - Chunk outbound links: ALL validated (in `validate_chunk_complete()`)
   - Code backreferences: NOT validated
   - Parent artifact → chunk links: NOT validated
   - Bidirectional consistency: NOT checked

3. **18 referential integrity violations exist** in the current codebase:
   - 1 malformed investigation reference (includes `docs/investigations/` prefix)
   - 17 bidirectional consistency violations (chunks claim parents that don't list them)

4. **File-based validation is fast enough** for pre-commit hooks (~300ms for 171 chunks)

5. **SQLite adds sync complexity without proportional benefit** for this use case:
   - Files are authoritative; DB would be derived state
   - All validation can be done with single traversal
   - FK constraints don't help if sync is incomplete

### Hypotheses/Opinions

1. **File-based validation is the right approach** - No database needed. Build in-memory graph on each run, validate, discard. Stateless is simpler.

2. **Pre-commit hook is the right enforcement point** - Fast enough, catches violations before they enter the repo, familiar workflow.

3. **Bidirectional consistency should be a warning, not error** - The parent→child direction is often set at creation, child→parent direction added later. Strict enforcement would break existing workflows.

4. **`ve validate` command is the right interface** - Can be invoked manually, by hooks, or by CI. Single entry point for all validation.

## Proposed Chunks

1. **Add `ve validate` command**: Implement a CLI command that runs referential integrity validation across all artifacts and code backreferences. Returns non-zero exit code on errors.
   - Priority: High
   - Dependencies: None
   - Notes: Use file-based approach from `prototypes/file_validator.py`. Start with errors only; add `--strict` flag for warnings.

2. **Validate code backreferences point to existing artifacts**: Extend existing backreference scanning to verify that `# Chunk:` and `# Subsystem:` comments reference existing artifacts.
   - Priority: High
   - Dependencies: ve validate command
   - Notes: Currently `count_backreferences()` only counts; should also validate.

3. **Validate proposed_chunks references**: Check that `proposed_chunks[].chunk_directory` in narratives, investigations, and friction log point to existing chunks.
   - Priority: Medium
   - Dependencies: ve validate command
   - Notes: NULL/missing chunk_directory is valid (chunk not yet created); only validate non-null references.

4. **Add bidirectional consistency warnings**: Warn when chunk→parent link exists but parent doesn't list chunk, or vice versa.
   - Priority: Low
   - Dependencies: Chunks 1-3
   - Notes: Should be warnings, not errors. May require workflow changes to make strict enforcement practical.

5. **Fix existing integrity violations**: Clean up the 18 violations found in current codebase.
   - Priority: Medium
   - Dependencies: ve validate command (to verify fixes)
   - Notes: 1 malformed ref, 17 bidirectional inconsistencies. Some may require updating parent artifacts.

6. **Add /validate-fix slash command**: Create a slash command that iteratively runs validation and fixes errors until all checks pass. The agent loops: run validate, analyze errors, apply fixes, repeat until clean.
   - Priority: Medium
   - Dependencies: Chunks 1-4 (needs full validation and all error types defined)
   - Notes: Should handle fixable errors automatically (e.g., add missing backrefs, normalize paths) and report unfixable issues for human review.

## Resolution Rationale

All three success criteria have been met:

1. **Complete map of link types**: Documented 12 distinct edge types with their validation status (see Exploration Log)

2. **Evaluated enforcement mechanisms**: Compared SQLite (FK constraints) vs file-based validation. File-based is simpler and sufficient—no database sync complexity, ~300ms validation time.

3. **Recommendation**: Implement `ve validate` command using file-based approach. Run via pre-commit hook. Five implementation chunks proposed.

**Key insight:** The reference graph doesn't need a persistent database. It can be computed on-demand by traversing files. This avoids the complexity of keeping two data stores in sync while still providing mechanical validation guarantees.

**Prototypes produced:**
- `prototypes/schema.sql` - SQLite schema (evaluated, not recommended)
- `prototypes/file_validator.py` - Working file-based validator (recommended approach)