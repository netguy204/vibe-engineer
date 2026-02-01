---
status: ONGOING
trigger: "CLAUDE.md consuming significant tokens; need to reduce weight to add more valuable context"
proposed_chunks:
  - prompt: "Refactor CLAUDE.md template with progressive disclosure: extract orchestrator docs to ORCHESTRATOR.md, extract artifact docs (narratives, investigations, subsystems) to ARTIFACTS.md, update CLAUDE.md.jinja2 with signpost structure. Use prototypes in this investigation as starting point."
    chunk_directory: progressive_disclosure_refactor
    depends_on: []
  - prompt: "Extract external artifacts documentation to docs/trunk/EXTERNAL.md and add signpost to CLAUDE.md"
    chunk_directory: progressive_disclosure_external
    depends_on: [0]
  - prompt: "Validate agent behavior with extracted documentation during normal development"
    chunk_directory: progressive_disclosure_validate
    depends_on: [0]
  - prompt: "Rename ve chunk list --latest to --current and add --recent flag showing 10 most recent ACTIVE chunks. Update CLAUDE.md template and any other docs referencing --latest."
    chunk_directory: chunk_list_flags
    depends_on: []
  - prompt: "Add Jinja2 templates for progressive disclosure documents (ORCHESTRATOR.md, ARTIFACTS.md, EXTERNAL.md) so they get installed during ve init"
    chunk_directory: disclosure_trunk_templates
    depends_on: [0]
created_after: ["orch_task_context"]
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
  - depends_on: Optional array of integer indices referencing other prompts in the same array.
    This expresses implementation dependencies between proposed chunks.
    - Indices are zero-based (e.g., `depends_on: [0, 2]` means "this prompt depends on
      prompts at indices 0 and 2 in this array")
    - Use when chunks have ordering constraints (e.g., chunk B needs chunk A's interfaces)
    - At chunk-create time, index references are translated to chunk directory names
    - Omit or set to [] for prompts with no dependencies
- Unlike narrative chunks (which are planned upfront), these emerge from investigation findings
-->

## Trigger

CLAUDE.md is consuming significant tokens in every VE project, and there's more detail that should be available to agents. The current monolithic structure creates a ceiling: adding valuable context requires first reducing what's already there.

Specific sections identified as candidates for extraction:
- Orchestrator documentation (detailed commands, workflows, batch operations)
- Narratives and Investigations guidance
- Possibly: Subsystems, External Artifacts, Friction Log details

The goal is "reducing weight and increasing potential" - making room for growth while ensuring agents can still discover and access the full documentation when needed.

## Success Criteria

1. **Identify extractable sections**: Determine which CLAUDE.md sections can be moved to linked documents without breaking agent discovery
2. **Define "clue" patterns**: Establish what minimal information must remain in CLAUDE.md for agents to know when to follow links
3. **Measure token impact**: Quantify current CLAUDE.md token usage and projected savings from extraction
4. **Validate agent behavior**: Confirm (via existing patterns or testing) that agents successfully follow documentation links
5. **Produce a recommended structure**: A concrete proposal for the new CLAUDE.md organization with linked documents

## Testable Hypotheses

### H1: Agents can successfully discover and follow links to extended documentation when given sufficient contextual clues

- **Rationale**: Agents already follow links to GOAL.md, subsystem docs, and other artifacts when the context suggests they should
- **Test**: Analyze existing link-following patterns in VE workflows; identify what triggers successful discovery
- **Status**: VERIFIED
- **Evidence**:
  - Existing patterns show agents successfully follow links when given behavioral triggers
  - Subagent test confirmed: given slim CLAUDE.md and prompt "How do I manage conflicts in the orchestrator?", agent correctly identified `docs/trunk/ORCHESTRATOR.md` as the file to read

### H2: There is a natural hierarchy where some concepts are core and others are extensions

- **Rationale**: Chunks and basic workflow are needed immediately; orchestrator, investigations, and narratives are needed only in specific scenarios
- **Test**: Categorize CLAUDE.md sections by "always needed" vs "situationally needed" based on agent workflows
- **Status**: VERIFIED
- **Evidence**: Token analysis shows clear split:
  - Core (23%): Header, Project Docs, Chunks, Commands, Getting Started, Learning Philosophy
  - Situational (77%): Narratives, Subsystems, Investigations, Friction Log, External, Orchestrator, Backreferences

### H3: A "signpost" pattern (brief description + link) is sufficient for agent discovery

- **Rationale**: Agents can pattern-match on keywords and context to know when to read more
- **Test**: Examine how agents currently discover subsystems and investigations from brief mentions
- **Status**: VERIFIED (prototype created)
- **Evidence**: Prototype signpost pattern reduces orchestrator section from 1001 words to ~70 words while preserving:
  - What it is (brief description)
  - When to use it (trigger keywords/scenarios)
  - Where to learn more (link to docs)
  - Related commands (skill references)

### H4: Extracted documents can live in docs/trunk/ alongside other reference docs

- **Rationale**: docs/trunk/ is already established as the location for stable project documentation
- **Test**: Verify no tooling or conventions assume CLAUDE.md is the only entry point
- **Status**: VERIFIED
- **Evidence**: docs/trunk/ already contains GOAL.md, SPEC.md, DECISIONS.md, TESTING_PHILOSOPHY.md, FRICTION.md. Adding ORCHESTRATOR.md, ARTIFACTS.md, EXTERNAL.md follows established pattern. No tooling assumes CLAUDE.md is comprehensive.

### H5: Token savings of 30-50% are achievable while maintaining agent effectiveness

- **Rationale**: Orchestrator section alone is substantial; combined with narratives/investigations, extraction could be significant
- **Test**: Measure current token counts per section; model extraction scenarios
- **Status**: EXCEEDED
- **Evidence**: Prototype achieves 77% reduction (2749 words → 642 words; ~3573 tokens → ~834 tokens). Far exceeds 30-50% target.

## Exploration Log

### 2026-01-31: Token measurement and section categorization

Analyzed CLAUDE.md.jinja2 template (2749 words, ~3568 tokens estimated).

**Token breakdown by section:**

| Section | Words | ~Tokens | % of Total |
|---------|-------|---------|------------|
| Header | 27 | 35 | 1% |
| Project Documentation | 79 | 102 | 3% |
| Chunks | 234 | 304 | 9% |
| Narratives | 70 | 91 | 3% |
| Subsystems | 150 | 195 | 5% |
| Investigations | 151 | 196 | 5% |
| Friction Log | 252 | 327 | 9% |
| Proposed Chunks | 79 | 102 | 3% |
| External Artifacts | 225 | 292 | 8% |
| Available Commands | 115 | 149 | 4% |
| Getting Started | 25 | 32 | 1% |
| Learning Philosophy | 146 | 189 | 5% |
| **Working with the Orchestrator** | **1001** | **1301** | **36%** |
| Code Backreferences | 195 | 253 | 7% |

**Key finding**: The Orchestrator section alone is 36% of the template.

**Categorization attempt (H2):**

*Core (always needed):*
- Header: 35 tokens
- Project Documentation: 102 tokens
- Chunks: 304 tokens
- Available Commands: 149 tokens
- Getting Started: 32 tokens
- Learning Philosophy: 189 tokens
- **Core subtotal: ~811 tokens (23%)**

*Situational (needed only in specific scenarios):*
- Narratives: 91 tokens (multi-chunk initiatives)
- Subsystems: 195 tokens (implementing patterns)
- Investigations: 196 tokens (exploring/diagnosing)
- Friction Log: 327 tokens (capturing friction)
- Proposed Chunks: 102 tokens (managing proposed work)
- External Artifacts: 292 tokens (multi-repo workflows)
- Working with the Orchestrator: 1301 tokens (parallel execution)
- Code Backreferences: 253 tokens (adding backreferences)
- **Situational subtotal: ~2757 tokens (77%)**

**Implication**: If situational content is extracted and replaced with signposts (~25-50 tokens each), potential reduction from ~3568 to ~1200-1400 tokens (60-65% savings). This exceeds H5's 30-50% target.

### 2026-01-31: Analyzing existing discovery patterns (H1, H3)

Examined how agents currently discover and follow links:

**Pattern 1: Behavioral triggers with directory references**
```markdown
**When to check subsystems**: Before implementing patterns that might already exist
in the codebase, check `docs/subsystems/` for existing documentation.
```

**Pattern 2: Artifact type → directory mapping**
The current structure establishes `## Narratives (docs/narratives/)` section headers that teach the location alongside the concept.

**Pattern 3: Skills as progressive disclosure**
Skills already implement progressive disclosure - `/orchestrator-submit-future` contains detailed orchestrator instructions loaded on-demand. Current skill token usage:
- orchestrator-investigate: ~914 words (~1188 tokens)
- orchestrator-submit-future: ~371 words (~482 tokens)

**Key insight**: There's redundancy between inline CLAUDE.md documentation and skill content. The CLAUDE.md orchestrator section (1001 words) overlaps with skill content.

**Proposed signpost pattern** (testing H3):

```markdown
## Orchestrator (`ve orch`)

The orchestrator manages parallel chunk execution across multiple worktrees. Use when:
- Managing multiple concurrent workstreams
- Running chunks "in the background"
- Coordinating FUTURE chunks for later execution

Key phrases: "background", "parallel", "orchestrator", "inject", "FUTURE chunk"

For details: See `docs/trunk/ORCHESTRATOR.md`
Commands: `/orchestrator-submit-future`, `/orchestrator-investigate`
```

This signpost is ~70 words (~91 tokens) vs current 1001 words (~1301 tokens).

**Question to resolve**: Where should extracted content live?
- Option A: `docs/trunk/` (stable reference docs, part of template)
- Option B: Skill-only (no new files, rely entirely on skills)
- Option C: Hybrid (brief docs in trunk for context, detailed procedures in skills)

### 2026-01-31: Architecture analysis - where extracted content lives

**Token economics insight:**

The goal is reducing *always-loaded* tokens (CLAUDE.md) while ensuring agents can access full documentation *when needed*. Three potential homes for extracted content:

| Location | Load behavior | Token impact |
|----------|---------------|--------------|
| CLAUDE.md | Always loaded | Current cost |
| Skills | On-demand (invoked) | Zero until needed |
| docs/trunk/*.md | On-demand (Read tool) | Zero until needed |

**Skills vs docs/trunk/ tradeoff:**

- **Skills**: Already exist; contain procedural instructions; invoked by name
- **docs/trunk/**: Better for conceptual/reference content; agents must know to read them

**Observation from session context:**

Skills are exposed via system prompt with brief descriptions:
```
- orchestrator-submit-future: Batch-submit all FUTURE chunks to the orchestrator.
- orchestrator-investigate: Investigate and resolve a stuck orchestrator work unit.
```

Agents can pattern-match on these descriptions. But for *conceptual understanding* (when is orchestrator appropriate? what are FUTURE chunks?), skills may not be sufficient - they're task-oriented, not education-oriented.

**Proposed architecture:**

```
CLAUDE.md (always loaded, ~1200 tokens)
├── Core: Project docs, Chunks, Commands, Getting Started
├── Signposts: Brief section + trigger keywords + link for each:
│   ├── Orchestrator → docs/trunk/ORCHESTRATOR.md
│   ├── Artifacts → docs/trunk/ARTIFACTS.md (narratives, investigations, subsystems)
│   ├── Friction Log → docs/trunk/FRICTION.md (already exists)
│   └── External/Multi-repo → docs/trunk/EXTERNAL.md

Skills (on-demand, loaded when invoked)
├── Procedural: /chunk-create, /orchestrator-submit-future, etc.
└── Already contain step-by-step instructions

docs/trunk/*.md (on-demand, read when triggered)
├── ORCHESTRATOR.md - conceptual + reference (not procedural)
├── ARTIFACTS.md - narratives, investigations, subsystems overview
└── EXTERNAL.md - multi-repo workflows
```

**Key distinction:**
- CLAUDE.md signposts tell agents *when* to look
- docs/trunk/*.md explains *concepts and context*
- Skills explain *how* to perform specific tasks

### 2026-01-31: Prototypes created

Created three prototypes in `prototypes/`:

1. **CLAUDE-slim.md** (642 words, ~834 tokens)
   - Core sections preserved: Project Docs, Chunks, Commands, Getting Started, Learning Philosophy
   - Situational sections replaced with signposts using "Read when:" pattern
   - 77% reduction from original

2. **ORCHESTRATOR.md** (~800 words)
   - Full orchestrator reference extracted from CLAUDE.md
   - Organized by: Key Commands, FUTURE Chunks, Batch Creation, Re-injection, Attention, Background Keyword
   - Suitable for docs/trunk/

3. **ARTIFACTS.md** (~550 words)
   - Combines narratives, investigations, subsystems documentation
   - Includes "When to use" guidance and frontmatter patterns
   - Covers code backreferences and proposed_chunks pattern

**Next steps**: These prototypes validate the approach. Implementation would involve:
1. Converting prototypes to Jinja2 templates
2. Adding them to the template rendering pipeline
3. Updating CLAUDE.md.jinja2 to use slim structure
4. Testing with real agent workflows

### 2026-01-31: Subagent verification of signpost discovery

Tested slim CLAUDE.md with a research prompt: "How do I manage conflicts in the orchestrator?"

**Agent behavior**: Given only the slim CLAUDE.md, the agent correctly:
1. Matched the "orchestrator" keyword to the Orchestrator section
2. Identified `docs/trunk/ORCHESTRATOR.md` as the primary file to read
3. Noted `/orchestrator-investigate` as a relevant command
4. Recognized the pattern: "tell me where to look, not everything I need to know"

**Agent's assessment**: "The slim CLAUDE.md provides sufficient discovery cues for this question."

**Conclusion**: H1 and H3 are validated - agents can successfully discover linked documentation from signpost patterns. The "Read when" triggers and explicit file references provide adequate discovery cues.

### 2026-01-31: Friction discovered - --latest misnomer

While reviewing the slim CLAUDE.md prototype, noticed this line:
> "To understand recent work, use `ve chunk list --latest` to find the most recently created chunk."

This is misleading. `--latest` actually shows the currently IMPLEMENTING chunk, not recent work. Two issues:
1. **Misnomer**: "latest" implies recency, but it means "current"
2. **Missing capability**: No way to see what work was done recently (useful for context)

Added proposed chunk to rename `--latest` → `--current` and add `--recent` for actual recency.

## Findings

### Verified Findings

1. **Massive token reduction is achievable**: 77% reduction from ~3573 to ~834 tokens by moving situational content to linked docs. (Evidence: prototype CLAUDE-slim.md)

2. **Clear core/situational split exists**: 23% of content is core (chunks, getting started, commands), 77% is situational (orchestrator, artifacts, external). (Evidence: section-by-section token analysis)

3. **Orchestrator is the largest target**: At 1301 tokens (36% of total), the orchestrator section provides the biggest single extraction opportunity.

4. **Signpost pattern is viable**: Brief section with "what/when/where" structure (70 words) can replace detailed inline documentation (1001 words) while preserving discovery triggers.

5. **docs/trunk/ is appropriate home**: Existing pattern of reference docs (GOAL, SPEC, DECISIONS, FRICTION) establishes precedent.

### Hypotheses/Opinions

1. **Agent effectiveness will be maintained**: Subagent test with "orchestrator conflicts" query showed correct discovery behavior. More diverse testing in production would further validate.

2. **Skills complement but don't replace extracted docs**: Skills are procedural ("how to do X"), while extracted docs are educational ("what is X, when to use it"). Both are needed.

3. **Extraction order should prioritize orchestrator**: Biggest token savings with clearest extraction boundary.

## Proposed Chunks

1. **Refactor CLAUDE.md template with progressive disclosure**: Combined chunk that extracts orchestrator docs to ORCHESTRATOR.md, extracts artifact docs (narratives, investigations, subsystems) to ARTIFACTS.md, and updates CLAUDE.md.jinja2 with signpost structure.
   - Priority: High
   - Dependencies: None
   - Notes: Use prototypes at `prototypes/CLAUDE-slim.md`, `prototypes/ORCHESTRATOR.md`, `prototypes/ARTIFACTS.md`. Combines what were originally chunks 0, 1, and 4 to avoid file-level conflicts on CLAUDE.md.jinja2.

2. **Create docs/trunk/EXTERNAL.md for multi-repo workflows**: Extract external artifacts documentation to standalone reference doc.
   - Priority: Medium
   - Dependencies: Chunk 1
   - Notes: Only needed in multi-repo contexts; low frequency but high cognitive load.

3. **Validate agent behavior with extracted docs**: Test that agents successfully discover and read extracted documentation when triggered by signposts.
   - Priority: Medium
   - Dependencies: Chunk 1
   - Notes: Could be done informally during normal development rather than as dedicated test.

4. **Rename --latest to --current and add --recent**: The `ve chunk list --latest` flag is a misnomer - it shows the currently implementing chunk, not recent work. Rename to `--current` and add `--recent` to show 10 most recent ACTIVE chunks.
   - Priority: Medium
   - Dependencies: None (independent - touches CLI code and different part of CLAUDE.md)
   - Notes: Discovered during investigation when reviewing slim CLAUDE.md prototype. No backwards compatibility needed but requires doc updates.

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