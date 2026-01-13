---
status: ONGOING
trigger: "Bug chunks provide little semantic value for code understanding but may reveal friction patterns"
proposed_chunks:
  - prompt: "Suggest subsystem when cluster expands beyond threshold"
    chunk_directory: cluster_subsystem_prompt
  - prompt: "Add bug_type field to guide agent behavior at completion"
    chunk_directory: bug_type_field
  - prompt: "Document bug→friction→subsystem pipeline in CLAUDE.md"
    chunk_directory: null
created_after: ["orchestrator_quality_assurance"]
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
- Format: list of {prompt, chunk_directory} where:
  - prompt: The proposed chunk prompt text
  - chunk_directory: Populated when/if the chunk is actually created via /chunk-create
- Unlike narrative chunks (which are planned upfront), these emerge from investigation findings
-->

## Trigger

Observed that bug-fix chunks provide little semantic value when agents explore the codebase via backreferences. Following a chunk reference to "fixed null pointer in X" doesn't illuminate the code's purpose. However, bug patterns over time might reveal friction points that warrant subsystem documentation. Questioning whether the primary value of bug chunks is workflow improvement (friction discovery) rather than code understanding.

## Success Criteria

1. A clear recommendation for whether/how bug chunks should be tracked differently from feature chunks
2. A defined pipeline (or rejection of one) from bug patterns → friction → subsystems
3. Guidelines for when a bug warrants a chunk vs. just a commit

## Testable Hypotheses

### H1: Bug chunks' primary value is friction pattern detection, not code semantics

- **Rationale**: Bug chunk backreferences don't help understand code purpose—"fixed null pointer" tells you nothing about why the code exists
- **Test**: Review existing bug chunks and evaluate: (a) do any backreferences actually help understanding? (b) do any reveal repeated friction in an area?
- **Status**: PARTIALLY VERIFIED - See exploration log 2026-01-13

### H2: Repeated bugs in the same area signal missing subsystem documentation

- **Rationale**: Inconsistency or unclear boundaries cause repeated issues; if agents keep tripping over the same patterns, a subsystem definition would prevent future bugs
- **Test**: Look for bug clusters in the codebase and check if they share a common architectural confusion
- **Status**: VERIFIED - orch_* cluster shows 55% bug rate with no subsystem

### H3: A "friction_entries" linkage from bugs would make patterns discoverable

- **Rationale**: Bugs could feed the friction log rather than (or in addition to) code backreferences, making workflow improvement the primary output
- **Test**: Evaluate whether linking bugs to friction entries rather than code would improve workflow learning
- **Status**: SUPPORTED - orch_unblock_transition already uses friction_entries pattern

### H4: An eager detection workflow could flag subsystem candidates before bug accumulation

- **Rationale**: If we can detect "this bug is in the same area as previous bugs" at creation time, we can prompt for subsystem consideration earlier
- **Test**: Identify what signals at bug creation time could trigger subsystem review
- **Status**: UNTESTED

## Exploration Log

### 2026-01-13: Investigation created

Framed initial hypotheses around bug chunks serving friction detection rather than code semantics. Next steps: review existing bug-related chunks in the codebase to test H1.

### 2026-01-13: Hypothesis testing - Bug chunk analysis

**Methodology:** Searched all chunk GOAL.md files for bug/fix/error/broken keywords, then examined representative samples.

**H1 findings - Semantic value varies by bug type:**

Examined 4 representative bug chunks:

| Chunk | Type | Semantic Value | Friction Signal |
|-------|------|----------------|-----------------|
| `fix_ticket_frontmatter_null` | Pure code bug | LOW | YES - Python→YAML translation |
| `orch_blocked_lifecycle` | Workflow bug | MEDIUM - explains expected workflow | YES - state machine complexity |
| `orch_unblock_transition` | State bug | LOW | HIGH - has friction_entries already |
| `ordering_field_clarity` | Documentation bug | HIGH - explains concepts | HIGH - clarity fix |

**Key insight:** Bug chunks split into categories:
- **Pure code bugs** → LOW semantic value for backreferences
- **Workflow/lifecycle bugs** → MEDIUM (they document expected behavior)
- **Documentation/clarity bugs** → HIGH (they explain concepts)

But ALL have friction detection value—every bug reveals something unclear in the system.

**H2 findings - The orchestrator cluster:**

| Metric | Value |
|--------|-------|
| Total `orch_*` chunks | 20 |
| Bug-related chunks | 11 (55%) |
| Orchestrator subsystem | Does not exist |

Bug-related chunks: `orch_activate_on_inject`, `orch_blocked_lifecycle`, `orch_broadcast_invariant`, `orch_conflict_oracle`, `orch_conflict_template_fix`, `orch_foundation`, `orch_inject_path_compat`, `orch_mechanical_commit`, `orch_sandbox_enforcement`, `orch_unblock_transition`, `orch_verify_active`

**Key insight:** 55% bug rate with no subsystem documentation suggests the orchestrator is architecturally complex but undocumented. A subsystem definition could establish invariants (state transitions, broadcast requirements, sandbox boundaries) that prevent future bugs.

**H3 findings - friction_entries pattern already emerging:**

`orch_unblock_transition` already has:
```yaml
friction_entries:
  - entry_id: "Over-eager conflict oracle causes unnecessary blocking"
    scope: full
```

The pattern of linking bugs to friction is already being used organically. This validates the idea that bugs should flow into friction tracking.

## Findings

### Verified Findings

1. **Bug chunks vary in semantic value by type.** Pure code bugs (typo fixes, null handling) provide little semantic value via backreferences. Workflow bugs provide medium value because they document expected behavior. Documentation/clarity bugs provide high value because they explain concepts. (Evidence: analysis of 4 representative chunks)

2. **Bug clusters correlate with missing subsystem documentation.** The orchestrator has 20 chunks, 55% of which are bug-related, and no subsystem documentation exists. This suggests architectural complexity without documented invariants leads to repeated issues. (Evidence: `orch_*` chunk analysis)

3. **The friction_entries pattern already exists.** At least one bug chunk (`orch_unblock_transition`) already links to friction entries, validating the hypothesis that bugs should flow into friction tracking. (Evidence: existing frontmatter)

### Hypotheses/Opinions

1. **Bug chunks should still be created** but their primary purpose is friction detection, not code understanding. The act of documenting a bug creates a searchable record that reveals patterns over time.

2. **Bug clusters (3+ bugs in same area) should trigger subsystem review.** When bugs accumulate in an area, it's a signal that invariants need documenting—not just that code needs fixing.

3. **Code backreferences may be optional for pure bug fixes.** If a bug fix doesn't add semantic understanding ("fixed null pointer"), the backreference adds noise. The friction_entries linkage may be more valuable.

## Proposed Chunks

1. **Suggest subsystem when cluster expands beyond threshold**: When `ve chunk create` would expand a cluster (chunks sharing a naming prefix) beyond a configurable size (e.g., 5), prompt the operator to consider defining a subsystem for that cluster. This surfaces missing subsystem documentation proactively rather than waiting for bug accumulation to reveal it.
   - Priority: High
   - Dependencies: None
   - Notes: Could use `ve chunk list --prefix <prefix>` internally to detect cluster size; threshold could be configurable in `.ve-config.yaml`

2. **Add "bug_type" field to guide agent behavior at completion**: When a chunk is a bug fix, the agent should classify it as either *semantic* (revealed new understanding of intended behavior) or *implementation* (corrected known-wrong code). The chunk template should include conditional guidance: semantic bugs require code backreferences and searching for impacted chunks; implementation bugs may skip backreferences since they don't add to code understanding.
   - Priority: Medium
   - Dependencies: None
   - Notes: Field values: `semantic` | `implementation`. Field guides agent behavior, not retrospective analysis.

3. **Document bug→friction→subsystem pipeline in CLAUDE.md**: Add guidance for when bugs should create friction entries and when bug clusters warrant subsystem documentation.
   - Priority: Medium
   - Dependencies: None
   - Notes: Codifies the learnings from this investigation into workflow guidance

## Resolution Rationale

*To be completed when investigation reaches terminal status.*