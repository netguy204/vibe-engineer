---
status: ONGOING
trigger: "Team feedback revealed gap between document-oriented workflow and code-first discovery preferences"
proposed_chunks: []
created_after: ["semantic_bugfix_documentation"]
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

Team feedback revealed a gap between the current document-oriented workflow and how engineers actually work. Some team members prefer hands-on code-first discovery (e.g., vibing through UI problems), but the current system doesn't reconcile code changes back to documentation. The core insight: vibe engineering should guarantee that documentation and code remain consistent regardless of which is edited first—like a wiki that stays synchronized with its codebase.

## Success Criteria

1. **Mental model clarity**: A clear definition of what chunks *are*—wiki pages asserting truths about system atoms, not tickets or commits
2. **Code→Doc reconciliation design**: A concrete mechanism for how code-first changes propagate back to documentation
3. **Tool vs convention boundary**: Understanding which workflows need tool support vs. which are just team conventions
4. **Ticket backreference model**: Define what backreferences from the documentation "wiki" to external tickets (Linear) are valuable and how they should be represented
5. **Proposed chunks**: Concrete implementation work for bidirectional sync capabilities

## Testable Hypotheses

### H1: Chunks should be understood as wiki pages, not tickets

- **Rationale**: Tickets are temporal (created → worked → closed), while chunks assert ongoing truths about system atoms. The wiki model better captures that chunks relate to each other through links and persist as living documentation.
- **Test**: Do chunks (or clusters of chunks) cohere into consumable "pages" about some domain in the system that add useful semantic understanding to the code that references them? If yes, the wiki model holds.
- **Status**: VERIFIED WITH REFINEMENT

**Findings**:
- Chunks as they exist today are work-item-sized, not concept-sized (27 chunks reference src/chunks.py but cluster into ~3-5 concepts)
- Subsystems ARE wiki pages - they have the right structure (intent, scope, invariants, code_references)
- Chunks don't become wiki pages directly - they're aggregated/synthesized into wiki pages
- Further refinement: chunks may become OBSOLETE, replaced by wiki pages + tickets + git history

### H2: Code→Doc sync requires detecting semantic drift, not just file changes

- **Rationale**: A file change doesn't tell you *what* documentation is affected. The system needs to understand which chunks "govern" which code regions.
- **Test**: Analyze existing backreference patterns—can we infer chunk ownership from current `# Chunk:` comments?
- **Status**: VERIFIED

**Findings**:
- Forward reconstruction experiment showed we CAN synthesize doc updates from diffs when wiki pages have semantic anchors (success criteria)
- The routing decision (vertical vs horizontal change) is solvable
- Code backreferences should point to wiki pages (subsystems), not chunks
- Wiki page code_references establish which code belongs to which concept

### H3: Linear tickets serve a different purpose than chunks and should be linked, not unified

- **Rationale**: Tickets capture *requests* (from stakeholders) and *workflow state* (assigned, in review). Chunks capture *truths about the system*. These are complementary, not overlapping.
- **Test**: Identify what information flows from Linear that isn't captured in chunks (requester, priority, sprint, acceptance criteria from PM).
- **Status**: VERIFIED AND EXTENDED

**Findings**:
- Original hypothesis was "tickets complement chunks"
- Evolved to: "tickets + git history REPLACE chunks"
- Two-layer model emerged:
  - Tickets + Git = request/result flow (what was asked, what was done)
  - Wiki pages = concept documentation (current truth)
- Chunks as a separate artifact become unnecessary
- Tickets reference wiki pages during triage; PRs update wiki pages; archaeology is in git history of wiki + ticket links

### H4: Engineers who "vibe" on code can trigger documentation reconciliation post-hoc

- **Rationale**: Rather than forcing doc-first workflow, provide tooling that asks "what did you just change, and which chunks does it affect?"
- **Test**: Prototype a post-commit hook or CLI command that prompts for chunk reconciliation.
- **Status**: VERIFIED

**Findings**:
- Forward reconstruction experiment (prototypes/forward_reconstruction_prompt.md) showed synthesis is feasible
- Given a diff and affected wiki pages, we can determine:
  1. Whether to update existing page or create new one
  2. What the documentation delta should say
  3. What code_references to add/update
- Key requirement: wiki pages need semantic anchors (success criteria, invariants) for routing to work
- Target is wiki pages, not chunks

## Exploration Log

### 2025-01-14: Experimental methodology for H4/H1

Proposed two approaches to test whether code→doc reconciliation is feasible:

**Approach A: Blind synthesis**
- Take N recent diffs, strip `# Chunk:` backreferences
- Prompt: "What documentation would describe this change?"
- Compare synthesized output to actual chunks

**Approach B: Forward reconstruction** (preferred)
- Find a commit where a chunk was created
- Accumulate subsequent diffs touching files that chunk references
- Prompt: "Given this chunk and these subsequent changes, what updates should the chunk receive?"
- Compare to actual chunk evolution (if any)

Approach B tests both H4 (can we reconcile post-hoc?) and H1 (do chunks accumulate into coherent wiki-like pages?).

**Next step**: Select a chunk with known subsequent modifications to its referenced code, then run the forward reconstruction experiment.

### 2025-01-14: Experiment setup - forward reconstruction

**Selected chunk**: `symbolic_code_refs` (created 2026-01-08)
- Establishes: symbolic reference format (`{file_path}#{symbol_path}`), overlap detection, validation at completion
- References: `src/models.py#SymbolicReference`, `src/chunks.py#Chunks::validate_chunk_complete`, etc.

**Selected diff**: commit `f53bb07` (2026-01-13)
- Adds `parse_chunk_frontmatter_with_errors()` for detailed validation feedback
- Enhances `SymbolicReference.validate_ref()` with contextual error messages for org/repo format
- Adds `task_context` and `projects` parameters to `create_chunk()`

**Experiment question**: Given the chunk GOAL.md and this diff, can we synthesize:
1. Whether the chunk should be updated (or a new chunk created)
2. What the documentation delta should say
3. What new code_references should be added

**Prototype prompt**: See `prototypes/forward_reconstruction_prompt.md`

### 2025-01-14: Experiment results - forward reconstruction

Ran the forward reconstruction prompt. Key findings:

**The synthesis worked** - given the chunk and diff, we could determine:
1. This should update the existing chunk (not create a new one)
2. The documentation delta: add note about contextual error messages to "Validation at Completion"
3. New code reference: `src/chunks.py#Chunks::parse_chunk_frontmatter_with_errors`

**Why it worked**:
- The chunk had clear success criteria that served as semantic anchors
- The diff was additive (extending existing behavior), not contradictory
- The domain boundaries were well-defined (validation of symbolic references)

**Conditions for success** (hypothesis emerging):
- Chunks need strong semantic anchors (success criteria, not just descriptions)
- Changes should be mappable to existing criteria or trigger explicit new criteria
- This supports H4 when chunks are well-structured

**Open question**: What happens when a diff spans multiple chunks' domains? Or when a diff contradicts existing documentation?

### 2025-01-14: Multi-chunk diff experiment (initial framing)

**Case study**: Commit `488cdff` - "selective project linking"

This commit added `--projects` option to 4 commands, touching code with multiple existing chunk backreferences.

**Initial (wrong) analysis**: I framed this as a "routing decision" where someone chose to create a new chunk rather than update existing ones.

**Correction**: In the current workflow, there was no decision. Everything becomes a chunk because chunks are conflated with tickets. The `selective_project_linking` chunk exists not because of horizontal/vertical analysis but because that's what the workflow does for all work.

### 2025-01-14: Reframing - what would wiki-model decisions look like?

**The real question**: If we adopted a wiki model where chunks are enduring pages about system aspects, what decision-making would be needed?

**Scenario A: Code change, existing wiki pages**
- Developer makes a change
- System identifies which wiki pages govern the changed code
- Decision needed: Does this change UPDATE an existing page, or CREATE a new one?

**Scenario B: Code change, no governing pages (orphan code)**
- Developer makes a change to code with no backreferences
- Decision needed: Should we create a page for this? Or is it minor/mechanical?

**The vertical/horizontal distinction**:
- **Vertical**: Change deepens understanding of ONE concept the wiki already documents
- **Horizontal**: Change introduces a NEW concept that crosses existing concepts

**Key insight**: This decision doesn't exist in the current workflow. Every piece of work creates a chunk. If we want a wiki model, we need to design when to UPDATE vs CREATE.

**Open design question**: Can we automate this? Or is it inherently a human judgment? What signals could tooling use?

### 2025-01-14: Exploring the update-vs-create decision

**The bootstrapping problem**: In a mature wiki, structure guides decisions. But we're starting from a codebase where chunks = tickets, not pages. How do we discover the right wiki structure?

**Thought experiment**: Take `selective_project_linking` as an example.

In the current model, it's a chunk documenting "the work to add --projects option."

In a wiki model, where would this content live?
- Option A: Its own page - "Project Filtering" as a cross-cutting concept
- Option B: Sections on each command's page - "chunk create" page has a "Project Filtering" section
- Option C: A "CLI Common Options" page that documents all shared options

**What determines the right choice?**

1. **Reuse potential**: Will other code/docs need to reference this concept?
   - If yes → its own page (so others can link to it)
   - If no → section on existing page

2. **Conceptual independence**: Does this stand alone as a coherent idea?
   - "Symbolic references" → yes, it's a whole format with rules
   - "Added --projects option" → maybe not, it's a feature of commands

3. **Change cohesion**: When this concept changes, what else changes with it?
   - If it changes independently → its own page
   - If it always changes with something else → part of that page

**Hypothesis**: The existing chunk clusters might reveal natural wiki pages. Chunks that keep referencing each other, or that govern overlapping code, might want to be merged into a single wiki page.

**Test**: Look at which chunks share code_references. High overlap might indicate they're aspects of the same concept.

### 2025-01-14: Chunk overlap as wiki structure signal

**Data**: Examined which files are referenced by multiple chunks.

| File | Chunk Count |
|------|-------------|
| src/ve.py | 41 |
| src/models.py | 21 |
| src/chunks.py | 27 |

**Observation**: 27 chunks reference `src/chunks.py`. Grouped by naming pattern:

| Concept | Chunks | Example |
|---------|--------|---------|
| Schema/refs | 12 | symbolic_code_refs, chunk_frontmatter_model |
| Validation | 4 | chunk_validate, valid_transitions |
| Ordering | ~10 | artifact_ordering_index, populate_created_after |

**Key insight**: Current chunk granularity is **work-item-sized**, not **concept-sized**. In a wiki model:
- 12 schema chunks → 1 "Chunk Schema" page
- 4 validation chunks → 1 "Validation" page
- 10 ordering chunks → 1 "Artifact Ordering" page

**The transformation**: Chunks → Wiki Pages requires aggregation. Work items that touched the same concept get merged into a single page describing that concept's current truth.

**What this means for bidirectional sync**:
1. When code changes, identify which **concept** it affects (not which ticket created it)
2. Update the wiki page for that concept
3. The page accumulates understanding over time (vs chunks which accumulate as separate items)

## Findings

### Verified Findings

1. **Forward reconstruction works** when chunks have semantic anchors (success criteria). Given a chunk GOAL.md and a subsequent diff, we can synthesize documentation updates. (Evidence: forward_reconstruction_prompt.md experiment)

2. **Chunks are work-item-sized, not concept-sized.** 27 chunks reference `src/chunks.py`, but they cluster into ~3-5 concepts (schema, validation, ordering). (Evidence: code_paths analysis in exploration log)

3. **Chunk → Wiki transformation requires aggregation.** Multiple work-item chunks that touched the same concept would merge into a single wiki page describing that concept's current state.

4. **The update-vs-create decision maps to: "Does this affect an existing concept?"** Not "which chunk created this code" but "what concept does this code belong to."

### Hypotheses/Opinions

1. **Three-layer model may be emerging**:
   - **Tickets** (Linear): Work requests and workflow status - external, transient
   - **Chunks**: Work documentation - what was done - historical record
   - **Wiki Pages**: Concept documentation - what IS true now - evergreen

   Chunks and wiki pages are not the same thing. Chunks are the archaeology; wiki pages are the current truth.

2. **Subsystems might already be wiki pages.** Looking at how subsystems work (documenting patterns, invariants, code references), they're closer to the wiki page concept than chunks are.

3. **The horizontal/vertical decision is about concept boundaries.**
   - Vertical change: deepens one concept → update that page
   - Horizontal change: introduces new concept → create new page
   - The decision requires knowing the concept structure, which doesn't exist explicitly yet.

4. **Backreferences could evolve.** Instead of `# Chunk: ...` (linking to work history), code could have `# Concept: ...` (linking to wiki page). Chunks become metadata *on* the wiki page, not the primary reference.

5. **Subsystems ARE wiki pages.** Examined `docs/subsystems/template_system/OVERVIEW.md`:
   - Intent, Scope, Invariants = concept documentation
   - Code references = what implements this concept
   - Chunk relationships = work history (which chunks contributed)

   The subsystem aggregates chunks. Multiple chunks "implement" the subsystem. The subsystem is the evergreen truth; chunks are archaeology.

6. **The transformation isn't "chunks → wiki pages."** It's: "use more subsystems (or subsystem-like artifacts) as wiki pages, keep chunks as work history that feed into them."

7. **Subsystem is the right name.** After exploring whether "page" should be distinct from "subsystem", concluded they are the same. Subsystem captures "atomic parts of a software project that hang together and change together." The aspirational/deviation-tracking property is a feature.

8. **Chunks conflate two purposes.** They mix concept documentation (→ subsystems) with work unit scratchpad (→ new user-global artifact). Separating these clarifies both.

9. **Scratchpad is user-global, outside git.** Lives in `~/.vibe/scratchpad/`, organized by project. Supports cross-project "what am I working on" queries. Personal process artifact, not shared documentation. Will develop tooling for this.

10. **Task context must be preserved.** Subsystems can be cross-repo, potentially living in a global artifacts repo and linked from individual repos. Implementation must support task context (multi-repo workflows) - this has been forgotten in past implementations.

### 2025-01-14: Reconsidering the three-layer model

**Operator pushback**: Do we actually need chunks as archaeology? Could tickets + git history satisfy that need, leaving only:
- **Tickets + Git**: Request/result flow (what was asked, what was done)
- **Wiki pages**: Concept documentation (current truth)

**Analysis: What chunks provide vs. replacements**

| Chunk provides | Could be replaced by |
|----------------|----------------------|
| Why we made a change | Ticket description + wiki page git history |
| Grouping of related work | PR (groups commits), ticket links to PR |
| Success criteria | Ticket acceptance criteria |
| Code references | Wiki page code_references (current state) |
| Decision rationale | DECISIONS.md or wiki page sections |

**What we might lose:**
1. Narrative coherence at moment of decision - but DECISIONS.md + wiki git history partially addresses this
2. In-repo work grouping - but wiki code_references provide concept-based grouping which may be more useful

**What we'd gain:**
1. Less clutter (no accumulating chunk directories)
2. Simpler model (two layers instead of three)
3. Cleaner backreferences (`# Subsystem:` not `# Chunk:`)
4. Natural aggregation (wiki pages are concept-sized)

**The remaining question**: Is there archaeology value in chunks that git history + tickets + wiki evolution can't provide?

Tentative answer: Probably not, IF:
- Wiki pages are well-structured with intent/scope/invariants
- DECISIONS.md captures significant architectural choices
- Tickets are linked to PRs and wiki pages
- Wiki git history is navigable ("what changed in our understanding of X?")

**Key insight**: The wiki page's git history IS the archaeology. If someone wants to understand how a concept evolved, they can `git log docs/subsystems/foo/OVERVIEW.md`.

### 2025-01-14: Two paths to wiki-based vibe engineering

**Path A: New project bootstrap (cold start)**
1. Analyze codebase (structure, patterns, dependencies)
2. Identify cohesive concepts (clustering by file relationships, naming, imports)
3. Create wiki pages (intent, scope, invariants, code_references)
4. Write backreferences throughout code (`# Concept: ...`)

**Path B: Migrate existing vibe-engineering project**
1. Analyze existing chunks (cluster by code_references overlap)
2. Synthesize wiki pages from chunk clusters (12 schema chunks → 1 "Chunk Schema" page)
3. Update backreferences (`# Chunk:` → `# Concept:`)
4. Archive/delete chunk directories

**Observation**: Path B's synthesis step is what we prototyped earlier, but for aggregation (many chunks → one page) rather than forward reconstruction (diff → doc update).

**The bootstrap process might generalize**: Both paths require:
1. Identifying concepts in code
2. Creating wiki pages for concepts
3. Establishing bidirectional references (code ↔ wiki)

The difference is the input:
- Path A: Raw code
- Path B: Code + existing chunks (which provide hints about concept boundaries)

**Tooling implication**: A `ve wiki bootstrap` command that:
- Analyzes code structure and naming patterns
- Proposes wiki page boundaries
- Generates initial wiki pages with code_references
- Writes backreferences in code

For migration, it would also:
- Read existing chunks to inform concept clustering
- Synthesize chunk content into wiki pages
- Handle the `# Chunk:` → `# Concept:` rewrite

### 2025-01-14: Ticket-wiki integration

**The flow**:
1. **Triage**: Ticket references wiki pages ("affects Template System, Artifact Ordering")
2. **Work**: Developer changes code AND updates wiki pages
3. **Completion**: PR includes code diff + wiki diff together
4. **Archaeology**: PR shows what changed in code and understanding simultaneously

**What this requires**:
- Wiki pages exist for major concepts (currently: 2 subsystems, need: 20-30?)
- Tickets reference affected concepts (manual or tooling-assisted)
- PRs include wiki updates as standard practice
- Code backreferences wiki pages

**The bootstrapping chicken-and-egg**:
- Need wiki pages for ticket-wiki flow to work
- Need ticket-wiki flow to motivate creating wiki pages

**Resolution**: Bootstrap the wiki first. Create the 20-30 concept pages from existing chunks + code analysis. Then the ticket-wiki flow becomes natural.

**Implication for vibe-engineering workflow**:
Instead of "create chunk → do work → complete chunk", it becomes:
1. Ticket created (references affected wiki pages)
2. Do work (change code, update wiki pages)
3. PR reviewed (code + wiki changes together)
4. Ticket closed (links to PR showing what changed)

No in-repo chunk artifact needed. The wiki page git history + ticket + PR provide full traceability.

### 2025-01-14: Artifact types in the wiki model

**Subsystems → Wiki hub pages**
- Already the right structure (intent, scope, invariants, code_references)
- Aspirational property: describe how the world SHOULD be
- Track deviations: how the world DIFFERS from ideal
- Reconciliation decisions → Linear tickets → work → documentation + code
- The subsystem evolves toward its aspirational state over time

**Narratives → Possibly obsolete**
- Purpose was: help operator think through a group of work units
- In wiki model: that planning happens in Linear or outside the repo
- The wiki itself might serve the coordination purpose narratives served
- If we need to document "why these 5 tickets are related", that's a Linear epic or project, not an in-repo artifact

**Investigations → Stand apart, remain valuable**
- Not about work management; about THINKING and REASONING
- Product-oriented thinking: happens outside (designers, users, Linear)
- Tech-oriented thinking: happens in-repo, in context of codebase
  - System architecture reasoning
  - Technical opportunity/problem analysis
  - Decision exploration with code evidence
- Output: often Linear tickets that then update wiki pages
- Value: helps future engineers understand WHY decisions were made
- Investigations are exploratory; wiki pages are declarative

**Chunks → Obsolete (replaced by tickets + PRs + wiki updates)**

**The simplified artifact set:**
1. **Wiki pages (subsystems)** - Concepts, current truth, aspirational patterns
2. **Investigations** - Exploratory thinking, tech-owned reasoning, decision archaeology
3. **DECISIONS.md** - Major architectural choices (or fold into wiki page sections?)

**Flow artifacts (chunks, narratives)** become unnecessary because:
- Chunks → ticket describes request, PR shows work, wiki update shows understanding change
- Narratives → Linear epics/projects coordinate related work externally

### 2025-01-14: Wiki bootstrap experiment design

**Goal**: Test whether we can bootstrap a wiki from code analysis on a legacy codebase.

**Workflow created**: `prototypes/wiki_bootstrap_workflow.md`

**Phases**:
1. Structural Analysis - directory structure, entry points, file inventory
2. Dependency Mapping - imports, hub files, clusters
3. Concept Discovery - identify cohesive concepts that could become pages
4. Page Boundary Refinement - finalize pages, resolve overlaps
5. Backreference Planning - map files to pages

**Experiment**: Apply this workflow to a legacy repository (no chunks, only code) and report:
- What wiki pages were identified
- What concepts they cover
- How much of the codebase is covered

### 2025-01-14: Wiki bootstrap experiment - pybusiness

**Target**: ../pybusiness (134 Python source files, no existing chunks)

**Result**: 12 wiki pages identified covering ~95% of source files

**Layered structure discovered**:
```
Application (4):  Savings Analysis, Explain Engine, Cost Mapping, Billing Recon
Domain (3):       Commitment Engine, Risk Pool Analysis, Signal Processing
Integration (1):  Platform Abstraction
Foundation (4):   LLM Framework, Artifact Storage, Evidence Framework, Core Utils
```

**Key findings**:
1. **Two hub modules** (`utils` 64%, `platform` 42%) create natural foundation layer
2. **Domain concepts cluster clearly** - cengine, risk, signals are cohesive
3. **Cross-cutting concerns identified** - LLM tracing, async patterns, query templating
4. **Coverage is high** - only a few files (forecast.py, datagen/) weren't cleanly mapped

**Full report**: `prototypes/pybusiness_wiki_bootstrap_report.md`

**Validation of H4**: The bootstrap process successfully identified concepts from code structure and dependencies. This supports the claim that wiki pages can be synthesized from code analysis.

### 2025-01-16: Subsystems ARE the wiki

**Question explored**: What distinguishes a "wiki page" from a "subsystem"?

**Analysis**:

| Aspect | Current Subsystem | Hypothetical "Page" |
|--------|-------------------|---------------------|
| Structure | Intent, Scope, Invariants, Code refs | Intent, Scope, Code refs |
| Describes | How things SHOULD be | How things ARE |
| Tracks | Deviations from ideal | Just current state |
| Status | DISCOVERING → STABLE lifecycle | No lifecycle? |

**Finding**: When trying to identify something that's a "page" but NOT a subsystem... nothing emerged. All 12 pybusiness wiki pages fit the subsystem structure perfectly.

**Conclusion**: Subsystems ARE wiki pages. The structure is already right. We just need:
1. More of them (2 → 20-30 for a typical project)
2. To use them as the canonical documentation (not just "patterns we're consolidating")
3. Code backreferences point to subsystems

**Why "subsystem" is the right name**: It captures the idea of atomic parts of a software project that hang together and change together. The aspirational property (tracks deviations, drives improvement) is a feature, not a limitation.

### 2025-01-16: The scratchpad concept

**Insight**: Chunks have been conflating two purposes:
1. **Concept documentation** (wiki) → belongs in subsystems
2. **Work unit scratchpad** (notebook) → personal, ephemeral, process-oriented

**Scratchpad characteristics**:
- Lives outside git (not version controlled with project)
- User-global (cross-project view)
- Personal process, not shared artifact
- Helps with: remembering context, planning approach, drafting tickets, cross-session continuity

**Proposed location**: `~/.vibe/scratchpad/` organized by project

**Key use case**: "What am I working on?" query every morning to get brain straight - requires cross-project view.

**Tooling decision**: Will develop tooling for scratchpad, especially cross-project queries.

### 2025-01-16: Final model

**Three locations for work artifacts**:

```
USER-GLOBAL (outside git) - ~/.vibe/scratchpad/
├── Personal work notes
├── Draft tickets before Linear
├── Cross-project "what am I working on" view
└── Ephemeral, archived when done

IN-REPO (version controlled) - docs/
├── subsystems/     → Wiki pages (concepts, current truth, aspirational)
├── investigations/ → Exploratory thinking, tech-owned reasoning
└── DECISIONS.md    → Major architectural choices

EXTERNAL (Linear + GitHub)
├── Tickets         → Official work requests, workflow state
└── PRs             → Work results, subsystem updates
```

**Artifact lifecycle changes**:
- **Chunks** → Obsolete (replaced by scratchpad + subsystems + tickets)
- **Narratives** → Obsolete (planning happens in Linear epics)
- **Subsystems** → Expanded role as wiki pages
- **Investigations** → Remain valuable for tech-owned reasoning
- **Scratchpad** → New user-global concept for work-in-progress

**The workflow**:
1. Scratchpad note (personal thinking)
2. → Linear ticket (official request)
3. → Work (code changes + subsystem updates)
4. → PR (code + wiki diff together)
5. → Ticket closed, scratchpad archived

**Next step needed**: Implementation order for migrating vibe-engineer repository to this new view.

### 2026-01-16: Domain-oriented bootstrap (lesson learned)

**Context**: Applied wiki bootstrap workflow to platform codebase. Initial analysis produced 12 subsystems heavily weighted toward infrastructure patterns.

**The mistake**: Over-indexed on technical patterns:
- "Middleware Pipeline"
- "Instrumentation"
- "Error Handling"
- "Data Access Layer"
- "API Routing"

These are real patterns, but they're not the most valuable documentation. They answer "how is this built?" not "what does this system DO?"

**The correction**: Re-analyzed with business-first lens:
- What business problems does each service solve?
- What are the core entities users care about?
- What state machines govern entity lifecycles?
- What business rules must never be violated?

**Result**: 8 domain-oriented subsystems that map to business capabilities:
1. `commitment_fulfillment` - RI/Savings Plan lifecycle
2. `cost_integration` - Cloud account connections
3. `financial_billing` - Bills, invoices, payment strategies
4. `cost_hierarchy` - Cost layers, resource mapping
5. `cost_forecasting` - Projections, initiatives
6. `cost_analytics` - Queries, filtering, insights
7. `organizations` - Multi-tenancy, membership
8. `notifications` - Alerts, Knock integration

Infrastructure patterns became a "Supporting Infrastructure" section, not primary subsystems.

**New workflow created**: `prototypes/domain_oriented_bootstrap_workflow.md`

Key guidance:
1. Start with business capabilities, not technical layers
2. Map entities and their lifecycles (state machines)
3. Extract business rules (invariants)
4. Name subsystems using business language
5. Add infrastructure as supporting material LAST

**Validation**: If infrastructure subsystems outnumber domain subsystems, start over.

### 2026-01-16: Enhanced domain-oriented workflow

**Work done**: Enhanced `prototypes/domain_oriented_bootstrap_workflow.md` based on lessons from platform bootstrap:

**Added Phase 6: Backreference Planning**
- Explicit guidance on WHERE to add backreferences (entry points, core logic, not utilities)
- Granularity guidance (module vs class vs function level)
- Shared code handling (3+ subsystems = infrastructure, no backreference)
- Coverage validation (each subsystem 3+ refs, no file with 3+ subsystem refs)

**Added System Boundary Identification section**
- Signs of well-bounded subsystems (single owner, cohesive vocabulary, independent lifecycle)
- Signs boundaries are wrong (symptom → likely problem → solution table)
- The "Could You Explain It?" test (can you explain to a new engineer in 2 minutes?)
- Cross-repository boundaries (task context support with repo prefixes)

**Added Intermediate Output Summary**
- Each of 6 phases now saves an intermediate artifact
- Explicit table: phase → output file → purpose
- Rationale for why intermediates matter (review checkpoints, debugging, iteration, learning)

**Updated Overview**
- Explicit 6-phase list in overview
- Clear output specification (6 intermediates + final report)

**Result**: Complete workflow from business capability discovery through actionable backreference plan, with operator review points at each phase.

## Proposed Chunks

<!--
GUIDANCE:

If investigation reveals work that should be done, list chunk prompts here.
These are candidates for `/chunk-create` - the investigation equivalent of a
narrative's chunks section.

Not every investigation produces chunks:
- SOLVED investigations may produce implementation chunks
- NOTED investigations typically don't produce chunks (that's why they're noted, not acted on)
- DEFERRED investigations may produce chunks later when revisited

Format:
1. **[Chunk title]**: Brief description of the work
   - Priority: High/Medium/Low
   - Dependencies: What must happen first (if any)
   - Notes: Context that would help when creating the chunk

Example:
1. **Add LRU eviction to ImageCache**: Implement configurable cache eviction to prevent
   memory leaks during batch processing.
   - Priority: High
   - Dependencies: None
   - Notes: See Exploration Log 2024-01-16 for implementation approach

Update the frontmatter `proposed_chunks` array as prompts are defined here.
When a chunk is created via `/chunk-create`, update the array entry with the
chunk_directory.
-->

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