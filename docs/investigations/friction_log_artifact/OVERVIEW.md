---
status: ONGOING
trigger: "Friction points accumulate during project use but have no artifact type to capture them"
proposed_chunks:
  - prompt: "Create friction log template and `ve friction` CLI"
    chunk_directory: null
  - prompt: "Add friction_entries to chunk GOAL.md template"
    chunk_directory: null
  - prompt: "Integrate friction into /chunk-create and /chunk-complete"
    chunk_directory: null
  - prompt: "Document friction log artifact in CLAUDE.md"
    chunk_directory: null
created_after: ["template_drift"]
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

Friction points accumulate during project use but have no home in the current artifact system:

- **Not a chunk**: When friction is discovered, we don't immediately know the solution
- **Not an investigation**: Friction logs extend over long periods; investigations are bounded explorations
- **Not a narrative**: Narratives plan work upfront; friction emerges organically over time

Without a dedicated artifact type, friction gets lost in chat logs, mental notes, or scattered TODOs. Over time, patterns emerge that could inform systematic improvements—but only if friction is captured and accumulated somewhere.

## Success Criteria

1. **Clear boundaries**: Define what distinguishes a friction log from chunk, investigation, narrative, and subsystem—with concrete examples of each
2. **Lifecycle design**: Determine status values, state transitions, and what "resolution" means for friction logs (if anything)
3. **Entry structure**: Design what a friction entry contains (timestamp, context, severity, tags, etc.)
4. **Friction-to-chunk workflow**: Design how accumulated friction spawns actionable chunks, including bidirectional linking
5. **Grounded in reality**: Validate design against real friction examples from chat logs

## Testable Hypotheses

### H1: Friction logs should be project-level singletons

- **Rationale**: Friction cuts across the codebase; a single log allows pattern detection across features
- **Test**: Review real friction examples—do they cluster by feature, or cut across?
- **Status**: VERIFIED
- **Evidence**: Reviewed 7 friction categories from chat logs. They span: CLI design, frontmatter conventions, code references, template system, documentation. No single domain dominates. Tags enable categorization within a single log.

### H2: Friction entries should evolve into proposed_chunks when patterns emerge

- **Rationale**: Similar to how investigations spawn proposed_chunks, friction patterns spawn work
- **Test**: Design the data model to support this flow; validate against real examples
- **Status**: VERIFIED
- **Evidence**: Designed workflow where friction entries link directly to chunks via `addressed_by` field. Unlike investigations which have `proposed_chunks` array, friction logs have entries that individually track their resolution. The "pattern → action" flow works better as: accumulated entries → human decision → chunk creation (with bidirectional links).

### H3: Friction logs need a fundamentally different lifecycle than investigations

- **Rationale**: Investigations are bounded questions; friction logs are ongoing accumulators
- **Test**: Determine if traditional status values (ONGOING/SOLVED) apply, or if friction logs are always "active"
- **Status**: VERIFIED
- **Evidence**: Friction logs don't have artifact-level status—they're ledgers, not documents. You don't "complete" a journal. The log is always implicitly active. Only individual entries have lifecycle (OPEN → ADDRESSED → RESOLVED).

### H4: Individual friction entries need their own lifecycle

- **Rationale**: A friction point might be: observed → addressed by chunk → resolved
- **Test**: Design entry-level status distinct from log-level status
- **Status**: VERIFIED
- **Evidence**: Designed entry lifecycle: OPEN → ADDRESSED (when chunk created) → RESOLVED (when chunk complete). Also WONTFIX for acknowledged-but-not-addressed. This captures the journey from pain to resolution.

### H5: Chunks need backlinks to the friction entries they address

- **Rationale**: Traceability from "why did we do this work?" back to accumulated pain
- **Test**: Design frontmatter schema for friction references in chunks
- **Status**: VERIFIED
- **Evidence**: Designed `friction_entries` array in chunk GOAL.md frontmatter with `entry_id` and `scope` (full/partial). This enables both "why did we do this work?" queries and multi-chunk resolution of complex friction.

## Exploration Log

### 2026-01-12: Chat log analysis for real friction examples

Analyzed 10 Claude chat log sessions from `~/.claude/projects/-Users-btaylor-Projects-vibe-engineer/`. Identified 7 concrete friction categories:

1. **Code Reference Ambiguity**: Symbolic references like `src/ve.py#create` became ambiguous when multiple commands have `create` functions. Resolved by renaming to `create_narrative`, `create_investigation`.

2. **Inconsistent Frontmatter Naming**: Narratives use `chunks`, investigations use `proposed_chunks`, subsystems use both `chunks` (relationships) and prose sections for consolidation work. No unified way to query pending work.

3. **Missing Bidirectional Code-to-Doc References**: Code can reference chunks, but documentation doesn't point back to code. Agents can't discover the chunk that created code without manual search.

4. **Lack of Friction Accumulation Artifact**: (This investigation itself) - friction gets lost in chat logs.

5. **Template Maintenance Burden**: Rendered files (CLAUDE.md) shouldn't be edited directly, but it's easy to make mistakes.

6. **Code Reference Validation Gap**: No built-in validation that symbolic references still point to valid code after refactoring.

7. **Design Ambiguity in Semantic Boundaries**: Recurring questions about what belongs in which artifact type, naming conventions, subcommand reference formats.

**Key insight**: These frictions have different lifecycles:
- Some were resolved in-session (Code Reference Ambiguity)
- Some spawned chunks or investigations (Frontmatter Naming)
- Some remain open/accumulating (Template Burden, Validation Gap)

### 2026-01-12: Artifact type boundary analysis

Reviewed all artifact templates to understand their distinguishing characteristics:

| Artifact | Purpose | Temporal Scope | Work Relation | Discovery |
|----------|---------|----------------|---------------|-----------|
| **Chunk** | Execute bounded work | Short (session to days) | IS the work | N/A |
| **Investigation** | Answer bounded question | Medium (days to weeks) | SPAWNS proposed_chunks | Hypotheses → findings |
| **Narrative** | Realize multi-step ambition | Medium (weeks to months) | PLANS proposed_chunks upfront | Decomposition → chunks |
| **Subsystem** | Document emergent pattern | Long (indefinite) | TRACKS chunks + consolidation | Observation → documentation |
| **Friction Log** (proposed) | Accumulate pain points | Long (indefinite) | ACCUMULATES → eventually SPAWNS chunks | Experience → patterns |

**Distinguishing characteristics of friction logs:**

1. **Accumulation without resolution pressure**: Unlike investigations (bounded question) or chunks (bounded work), friction logs grow indefinitely. There's no "done" state for the log itself—only for individual entries.

2. **Multiple entries, single artifact**: Chunks are one entry per artifact. Investigations have one trigger per artifact. Friction logs have MANY entries per artifact—they're ledgers, not documents.

3. **Pattern emergence**: Individual friction entries are small. Value emerges when patterns become visible across entries. This is different from investigations where hypotheses drive exploration.

4. **Entry-level vs artifact-level lifecycle**: Subsystems have artifact-level status (DISCOVERING → STABLE). Friction logs may need BOTH:
   - Artifact-level: Always "active" (it's a ledger, not a question)
   - Entry-level: observed → addressed → resolved

5. **Bidirectional linking**: When friction spawns a chunk, both should reference each other:
   - Chunk frontmatter: `friction_entries: [{log: "...", entry_id: "..."}]`
   - Friction entry: updated with `addressed_by: {chunk_directory: "..."}`

### 2026-01-12: Lifecycle design

**Key insight**: Friction logs need TWO distinct lifecycles.

#### Artifact-Level Lifecycle

Unlike other artifacts, friction logs don't "complete." They're ledgers, not documents. Two options:

**Option A: No artifact-level status**
- Friction logs are always active
- Simpler model; the log just exists
- Archival happens by moving the file, not by status change

**Option B: Minimal artifact-level status**
- `ACTIVE` - Default; friction being accumulated
- `ARCHIVED` - Project moved on; log retained for history

Leaning toward **Option A** for simplicity. A friction log is like a journal—you don't "complete" it.

#### Entry-Level Lifecycle

Individual friction entries have their own lifecycle:

```
OPEN → ADDRESSED → RESOLVED
       └→ WONTFIX
```

- **OPEN**: Friction observed but nothing done
- **ADDRESSED**: Chunk created to address (link to chunk)
- **RESOLVED**: Chunk complete, friction eliminated
- **WONTFIX**: Acknowledged but decided not to address (with rationale)

#### Proposed Entry Structure

```yaml
entries:
  - id: F001  # For stable references
    date: 2026-01-12
    title: "Symbolic code references become ambiguous"
    description: |
      When multiple CLI commands have functions named `create`, the
      symbolic reference `src/ve.py#create` becomes ambiguous.
    context: "Discovered while adding investigation CLI commands"
    impact: high  # low | medium | high | blocking
    frequency: recurring  # one-time | recurring
    tags: [code-references, naming, cli]
    status: RESOLVED
    addressed_by:
      - chunk_directory: "symbolic_code_refs"
    resolution_notes: "Renamed functions to be unambiguous"
```

#### Questions to resolve

1. **Should entries live in frontmatter or document body?**
   - Frontmatter: Machine-readable, enables `ve friction list --open`
   - Body: Better for prose descriptions, easier manual editing
   - Hybrid: IDs and status in frontmatter, prose in body sections

2. **Single friction log per project, or multiple logs by domain?**
   - Single: Simpler, enables cross-cutting pattern discovery
   - Multiple: Could organize by area (DX, API, testing)
   - Leaning single for now; tags handle categorization

3. **How to surface patterns?**
   - Tags enable grouping
   - Could add `ve friction analyze --tags cli` to find clusters
   - When a cluster has 3+ entries, suggest creating a chunk or investigation

### 2026-01-12: Friction-to-chunk workflow design

#### Workflow Overview

```
┌─────────────────┐
│ Experience      │   User/agent encounters friction during work
│ Friction        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ /friction-log   │   Capture with: title, description, context, impact
│ (new command)   │   Entry status: OPEN
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Pattern         │   Over time, entries accumulate
│ Accumulation    │   Tags reveal clusters
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Pattern         │   `ve friction analyze` or manual review
│ Recognition     │   Identify clusters worth addressing
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ /chunk-create   │   Create chunk referencing friction entries
│ (with friction) │   Entry status: OPEN → ADDRESSED
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ /chunk-complete │   When chunk completes, update entries
│                 │   Entry status: ADDRESSED → RESOLVED
└─────────────────┘
```

#### Bidirectional Links

**Friction → Chunk (in friction log):**
```yaml
entries:
  - id: F003
    # ... other fields ...
    status: ADDRESSED
    addressed_by:
      - chunk_directory: "cli_naming_conventions"
        scope: partial  # full | partial
```

**Chunk → Friction (in chunk GOAL.md frontmatter):**
```yaml
friction_entries:
  - entry_id: F003
    scope: partial  # This chunk partially addresses F003
  - entry_id: F007
    scope: full     # This chunk fully addresses F007
```

The `scope` field matters because:
- A single chunk might partially address friction (leaving residual friction)
- Multiple chunks might collaboratively address one friction entry
- Full/partial helps track whether friction is truly resolved

#### Commands and Integrations

**New commands:**

1. `ve friction log` / `/friction-log`
   - Quick-capture friction with minimal ceremony
   - Prompts for: title, description (optional), impact, tags
   - Auto-generates ID, timestamps entry

2. `ve friction list [--open] [--tags TAG]`
   - Show friction entries, filterable by status and tags
   - Default shows OPEN entries

3. `ve friction analyze [--tags TAG]`
   - Group entries by tag
   - Highlight clusters with 3+ entries
   - Suggest: "Consider creating a chunk or investigation"

**Modified commands:**

1. `/chunk-create` additions:
   - Option to specify friction entries being addressed
   - Updates those entries to ADDRESSED status
   - Adds `friction_entries` to chunk frontmatter

2. `/chunk-complete` additions:
   - Checks if chunk has `friction_entries`
   - Prompts: "Mark these friction entries as RESOLVED?"
   - Updates friction log accordingly

#### Alternative: Investigation as Intermediary

For complex friction patterns, the workflow might be:

```
Friction cluster → Investigation (to understand root cause) → Chunks (to fix)
```

In this case:
- Friction entries link to investigation: `investigated_by: "friction_pattern_analysis"`
- Investigation has `friction_entries` in frontmatter
- Investigation's `proposed_chunks` address the root cause

This is similar to how bugs sometimes need investigation before fixing.

#### Location Decision

Where should the friction log live?

**Option A: `docs/trunk/FRICTION.md`**
- Alongside GOAL.md, SPEC.md, DECISIONS.md
- Signals project-level importance
- Single canonical location

**Option B: `docs/friction/LOG.md`**
- Separate directory like chunks/, investigations/
- Room for future expansion (multiple logs?)
- Consistent with other artifact locations

**Recommendation: Option A** for now. Friction is project-level context, like decisions. If we later need multiple logs, we can migrate.

## Findings

### Verified Findings

1. **Friction logs are a distinct artifact type**: They differ from existing artifacts on multiple dimensions:
   - Purpose: Accumulate pain points (vs. execute work, answer questions, plan work, document patterns)
   - Temporal scope: Indefinite (vs. bounded)
   - Content granularity: Many entries per artifact (vs. one topic per artifact)
   - Work relationship: ACCUMULATE → eventually SPAWN chunks

2. **Friction logs need entry-level lifecycle, not artifact-level**: The log itself doesn't "complete"—only individual entries transition through OPEN → ADDRESSED → RESOLVED.

3. **Bidirectional linking is essential**: Chunks need `friction_entries` frontmatter to trace "why this work?" and friction entries need `addressed_by` to track resolution.

4. **Real friction cuts across domains**: Analysis of 7 friction categories from chat logs showed no single domain dominates. Tags within a single log handle categorization.

5. **Pattern emergence drives value**: Individual friction entries are small observations. Value comes from seeing patterns across entries—this informs what chunks or investigations to create.

### Hypotheses/Opinions

1. **Location at `docs/trunk/FRICTION.md`**: Recommending trunk because friction is project-level context like DECISIONS.md. Could also be `docs/friction/LOG.md`. User preference needed.

2. **Entry storage in frontmatter vs body**: Leaning toward frontmatter for machine-readability (enables `ve friction list --open`), but large entry counts might strain YAML. Could use hybrid: IDs/status in frontmatter, prose in body. Needs validation in practice.

3. **Single log per project**: Recommending single log with tags vs multiple logs by domain. Simpler and enables cross-cutting pattern discovery. Tags handle categorization.

4. **Investigation as intermediary for complex patterns**: For friction clusters that need root-cause analysis, the workflow might be: friction cluster → investigation → chunks. This is a design opinion, not tested.

5. **Command naming**: Proposed `/friction-log` for capture, `ve friction list/analyze` for queries. Naming is subjective.

## Proposed Chunks

1. **Create friction log template and `ve friction` CLI**: Implement the FRICTION.md template at `docs/trunk/FRICTION.md` and the `ve friction log/list/analyze` CLI commands. This is the foundation—entries can be captured and queried.
   - Priority: High
   - Dependencies: None
   - Notes: See Exploration Log for entry structure and lifecycle design. Start with entries in frontmatter; migrate to hybrid if YAML becomes unwieldy.

2. **Add friction_entries to chunk GOAL.md template**: Extend the chunk template to support `friction_entries` frontmatter linking chunks to the friction they address.
   - Priority: Medium
   - Dependencies: Chunk 1 (template must exist first)
   - Notes: See "Chunk → Friction" link design in Exploration Log.

3. **Integrate friction into /chunk-create and /chunk-complete**: Modify chunk lifecycle commands to prompt for friction entries being addressed and update entry status accordingly.
   - Priority: Medium
   - Dependencies: Chunks 1 and 2
   - Notes: This completes the bidirectional workflow. /chunk-create sets entries to ADDRESSED, /chunk-complete sets to RESOLVED.

4. **Document friction log artifact in CLAUDE.md**: Update the CLAUDE.md template to explain friction logs alongside other artifact types.
   - Priority: Low
   - Dependencies: Chunk 1
   - Notes: Part of making the workflow discoverable.

## Resolution Rationale

<!--
GUIDANCE:

When marking this investigation as SOLVED, NOTED, or DEFERRED, explain why.
This captures the decision-making for future reference.

Questions to answer:
- What evidence supports this resolution?
- If SOLVED: What was the answer or solution?
- If NOTED: Why is no action warranted? What would change this assessment?
- If DEFERRED: What conditions would trigger revisiting? What's the cost of delay?

Example (SOLVED):
Root cause was identified (unbounded ImageCache) and fix is straightforward (LRU eviction).
Chunk created to implement the fix. Investigation complete.

Example (NOTED):
GraphQL migration would require significant investment (estimated 3-4 weeks) with
marginal benefits for our use case. Our REST API adequately serves current needs.
Would revisit if: (1) we add mobile clients needing flexible queries, or
(2) API versioning becomes unmanageable.

Example (DEFERRED):
Investigation blocked pending vendor response on their API rate limits. Cannot
determine feasibility of proposed integration without this information.
Expected response by 2024-02-01; will revisit then.
-->