---
status: ONGOING
trigger: Quality slippage and loss of visibility as orchestrator usage increased
proposed_chunks: []
created_after: ["selective_artifact_linking"]
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

As orchestrator usage has increased, I'm experiencing discomfort with the quality and completeness of work being produced. Specifically:

- Less visibility into how decisions are made during chunk implementation
- Quality slippage where chunks complete but don't fully realize the vision in their GOAL.md
- A familiar feeling from moving up management levels—being further from the work

This warrants investigation because the current workflow lacks quality gates that would catch incomplete implementations or design drift before work is marked complete.

## Success Criteria

1. **Define what "reviewer agent" means in this context** - What would it review, when would it trigger, what feedback would it provide?

2. **Determine whether goal-to-implementation verification is tractable** - Can we reliably detect when an implementation doesn't fully realize its GOAL.md?

3. **Explore how "taste" could be encoded** - Either define what taste means operationally, or conclude it's too subjective to encode

4. **Design a quality gate integration point** - Where in the orchestrator workflow would review happen, and how would feedback loop back?

5. **Prototype or specify at least one reviewer pattern** - Either a working prototype or a clear enough specification that implementation is straightforward

## Testable Hypotheses

### H1: Reviewer agents can restore the "trusted lieutenant" dynamic from management

- **Rationale**: The discomfort described is familiar from management—being far from the work. In management, trusted people close to the action provided quality assurance and surfaced issues. Reviewer agents could serve this role.
- **Test**: Define what a "trusted lieutenant" actually does (reviews what? catches what?) and determine if an agent can replicate those functions.
- **Status**: UNTESTED

### H2: Goal-to-implementation fidelity can be verified through test coverage analysis

- **Rationale**: "Goals are fully represented by the implementation (as proved by the tests)" implies tests are the evidence of goal realization.
- **Test**: For a sample of completed chunks, compare GOAL.md success criteria against test assertions. Determine if gaps are detectable programmatically.
- **Status**: UNTESTED

### H3: Subsystem invariants provide a tractable subset of "taste"

- **Rationale**: Taste is hard to define, but subsystem invariants are explicit. Checking conformity to subsystems might capture the "coherence" aspect of taste, even if not the full aesthetic dimension.
- **Test**: Review existing subsystem OVERVIEW.md files for invariants. Determine if violations could be detected by a reviewer agent.
- **Status**: UNTESTED

### H4: Taste can be decomposed into reviewable heuristics

- **Rationale**: Great engineers had "taste" that made reviewed work cohere better. This might decompose into: naming consistency, pattern adherence, appropriate abstraction level, etc.
- **Test**: Interview yourself: What specifically did those engineers catch that others missed? Can those catches be enumerated as rules?
- **Status**: UNTESTED

## Exploration Log

### 2026-01-13: Defining the "trusted lieutenant" role

Explored H1 by interviewing about what trusted tech leads actually do. Key findings:

**What they review:** Code alignment with big picture objectives—not just "does it work" but "does it serve the intent."

**What they catch:** Implementation details that don't cover difficulties implied by the objectives. Gaps between literal requirements and the spirit of the goal.

**How they escalate:** As discussions, not reports. "We need to either change objectives or find a new implementation perspective." Two-way bridge between implementation reality and intent.

**What makes them trusted:** They understood the intent deeply enough that delegation of attention was possible. When they were "on it," the operator didn't need to be.

**Key insight:** The three sources of trusted lieutenant knowledge map to existing documentation:

| Trust Source | Documentation Equivalent |
|--------------|-------------------------|
| Documented context | GOAL.md + linked narratives/investigations |
| Implicit understanding | Narrative OVERVIEW.md, Investigation trigger/findings |
| Pattern recognition | Subsystem invariants |

This suggests H1 is tractable: the information a reviewer agent needs is already documented. The question becomes whether an agent can be prompted to use it effectively.

### 2026-01-13: Defining reviewer agent output modes

Continued H1 exploration. The reviewer agent should operate in two modes:

**Mode 1: Confident feedback (PR review cycle)**
- Reviewer knows what needs to change based on documented intent
- Gives feedback directly to the implementation agent
- Implementation iterates until reviewer approves
- Operator attention not required

**Mode 2: Escalation (attention mechanism)**
- Reviewer recognizes a gap in understanding
- The issue can't be resolved within documented intent
- Uses orchestrator attention mechanism to escalate to operator
- Blocks until operator provides clarity

This mirrors how trusted tech leads work: handle what they can, escalate what they can't. The key design question: how does the reviewer distinguish between "I can give feedback" and "I need to escalate"?

### 2026-01-13: Trust graduation and decision logging

Key insight: Trust is earned, not declared. The system needs to support trust development over time.

**Decision log requirement:**
- Reviewer maintains a log of all decisions made
- Allows operator to "watch over the shoulder" during early usage
- Similar to how managers observe new hires' code reviews before trusting them
- Transparency mechanism that enables trust to develop

**Trust graduation cycle:**
1. **Observation phase**: Decision log captures all decisions; operator reviews regularly
2. **Calibration phase**: Operator provides feedback ("should have escalated" / "didn't need to escalate")
3. **Delegation phase**: Operator declares categories reviewer can handle autonomously
4. **Full trust**: Operator only sees escalations, trusts the rest

**Escalation heuristic:**
- Primary signal: **Ambiguity** in documented intent
- Modifier: **Severity** (architectural > functional > style)
- Override: **Trust level** (trusted reviewers auto-decide on delegated categories)

Example trust evolution: "I don't care about style issues—just decide or ignore. But always escalate architectural concerns."

### 2026-01-13: Reviewer prompt prototype

Created initial prototype: `prototypes/chunk-review.md`

Key design decisions in the prototype:
- **Four-phase workflow**: Context gathering → Alignment review → Decision making → Decision logging
- **Three decision types**: APPROVE, FEEDBACK, ESCALATE
- **Trust levels**: observation → calibration → delegation → full (mirrors human trust graduation)
- **Escalation heuristic**: Ambiguity as primary signal, severity as modifier, delegated categories as override
- **Decision log**: Per-chunk REVIEW_LOG.md for transparency during trust development
- **Integration point**: After chunk-implement, before chunk-complete

Open questions identified:
- Per-chunk vs global decision log?
- Trust level persistence across sessions?
- Reviewer personalities (strict vs lenient)?
- Handling reviewer/implementer disagreements?
- Incremental vs end-of-chunk review?

### 2026-01-13: Reviewer personality model refined

Key refinement from discussion: reviewers are **persistent entities with emergent personality**, not anonymous instances.

**Decision log as training data:**
- Per-reviewer, global (not per-chunk)
- Captures decisions + operator feedback (good/bad/feedback)
- Becomes few-shot context for future reviews
- Dual purpose: transparency for trust AND shaping judgment

**Trust is domain-scoped:**
- A reviewer might be fully trusted for API work but only calibration-trusted for UI work
- Domain expertise emerges from accumulated examples in that domain

**Personality forking:**
- Start with baseline reviewer
- Accumulate examples through observation/calibration
- When examples start conflicting across domains, fork a new reviewer
- New reviewer starts from baseline + domain-specific example subset
- Avoids "confusion" from contradictory examples

**Lifecycle:**
1. Baseline reviewer prompt (the prototype)
2. Observation mode: decisions logged, operator flags good/bad
3. Examples accumulate, incorporated as few-shot context
4. Trust increases where examples are coherent
5. Domain divergence detected → fork new domain-specific reviewer
6. Each reviewer has own decision log, own trust level, own domain scope

This implies infrastructure:
- Reviewer registry (named reviewers with metadata)
- Decision log storage (per-reviewer)
- Example selection for few-shot context
- Domain assignment (which reviewer handles which chunks)
- Fork mechanism (create new reviewer from baseline + example subset)

### 2026-01-13: Reviewer prototype v2 and directory structure

Updated prototype with:
- **Loop detection**: Max 3 iterations before automatic escalation; same-issue detection
- **Two review modes**: Incremental (on-demand, advisory) and final (mandatory gate)
- **Implementer interface**: `/request-review` for mid-implementation feedback

Created prototype reviewers directory structure:

```
prototypes/reviewers/
├── baseline/
│   ├── METADATA.yaml    # Trust level, domain scope, stats
│   ├── PROMPT.md        # Core reviewer instructions
│   └── DECISION_LOG.md  # Empty, ready for first review
└── api_v1/
    ├── METADATA.yaml    # Delegation trust, API domain scope
    ├── PROMPT.md        # Domain-specific learned preferences
    └── DECISION_LOG.md  # Example decisions with operator feedback
```

The api_v1 example shows:
- How trust level progresses (observation → delegation)
- How domain scope narrows (api/*, *_endpoint, *_validation)
- How delegated categories emerge ("style", "error_messages")
- How decision log entries capture operator feedback (good/bad marking)
- How PROMPT.md evolves to include learned DO/DON'T preferences

## Findings

### Verified Findings

**F1: Trusted lieutenant role is tractable for agents**

The information a trusted tech lead uses to review code is already documented in
the vibe-engineer artifact structure:
- GOAL.md captures focused intent
- Linked narratives/investigations provide implicit understanding
- Subsystem invariants encode pattern recognition

An agent can be prompted to use these sources the way a human reviewer would.

**F2: Two-mode review structure matches workflow needs**

- **Incremental review** (on-demand): Implementer requests feedback mid-work via `/request-review`. Advisory only, doesn't block.
- **Final review** (mandatory): Gate between chunk-implement and chunk-complete. Must approve before completion.

**F3: Trust is earned through observable decision history**

Reviewers start untrusted (observation mode) and graduate through calibration → delegation → full trust based on accumulated good decisions. This mirrors how human managers develop trust in reports.

**F4: Reviewer personality emerges from examples**

Rather than predefined "strict" vs "lenient" personalities, reviewer character emerges from:
- Accumulated decision log entries
- Operator feedback (good/bad marking)
- Domain-specific examples that get incorporated as few-shot context

**F5: Loop detection requires three distinct mechanisms**

| Mechanism | Purpose |
|-----------|---------|
| `max_iterations` | Hard limit preventing infinite review cycles |
| `escalation_threshold` | Early warning when convergence is at risk |
| `same_issue_threshold` | Immediate escalation when same issue recurs (misunderstanding signal) |

These are per-reviewer configurable as part of personality tuning.

### Hypotheses/Opinions

- Domain-specific reviewers will naturally emerge as examples accumulate and conflict
- The "taste" question (H3/H4) may be partially answered by subsystem invariants, but full taste encoding remains unverified
- Forking threshold (when to create a new domain reviewer) needs operational experience to calibrate

### 2026-01-13: Prototype test on selective_artifact_friction chunk

Tested the reviewer prototype on a real orchestrator-completed chunk: `selective_artifact_friction`.

**Context gathered:**
- GOAL.md: 7 success criteria for task-aware friction logging with --projects flag
- Investigation: `selective_artifact_linking` - provided design rationale (Option D)
- Subsystem: `workflow_artifacts` (STABLE) - established patterns to follow
- PLAN.md: 8 implementation steps

**Review process:**
- Checked each success criterion against implementation evidence
- Found code_references in GOAL.md matched actual code locations
- Verified subsystem documentation was updated (Hard Invariant #11)
- Tests exist but weren't executed (would need `uv run pytest`)

**Simulated decision: APPROVE**
- All criteria had implementation evidence
- Pattern consistency with other task-aware commands
- Minor observation: test filename slightly different from PLAN.md (acceptable)

**Observations about the prototype:**
1. The context gathering phase worked well - backreferences to investigation and subsystem provided crucial design rationale
2. Code_references in GOAL.md made verification straightforward
3. A real reviewer would want to actually run tests, not just verify they exist
4. The "spirit vs letter" check is hard to mechanize - relied on pattern matching against similar commands

**Potential improvements:**
- Add a "verify tests pass" step that actually executes tests
- Consider adding code diff analysis to the review (what changed, not just what exists)
- The investigation backreference was valuable - consider making this mandatory for reviewer context

### 2026-01-13: Sub-agent test on orch_broadcast_invariant chunk

Spawned a sub-agent with the baseline reviewer prompt to review `orch_broadcast_invariant` chunk.

**Methodology change:** Instead of manually simulating the review, spawned a general-purpose agent with the reviewer prompt. This is a better test of whether the prompt actually works.

**Agent behavior observed:**
1. Agent read GOAL.md and extracted 4 success criteria
2. Agent read PLAN.md to understand intended approach
3. Agent checked for linked artifacts (none in this case - no narrative/investigation/subsystem)
4. Agent examined code_references by reading scheduler.py and test file
5. Agent mapped each criterion to implementation evidence
6. Agent produced structured YAML decision

**Result: APPROVE**

```yaml
decision: APPROVE
summary: "Implementation correctly fixes missing WebSocket broadcasts and documents the invariant with comprehensive test coverage."
criteria_assessment:
  - criterion: "RUNNING broadcast"
    status: "satisfied"
    evidence: "Lines 431-437 in scheduler.py, verified by test"
  - criterion: "Phase advance broadcast"
    status: "satisfied"
    evidence: "Lines 731-737 in scheduler.py, verified by test"
  - criterion: "Invariant documented"
    status: "satisfied"
    evidence: "Lines 203-228 class docstring with pattern example"
  - criterion: "All tests pass"
    status: "satisfied"
    evidence: "All 75 tests pass including 4 new broadcast tests"
```

**Agent went beyond minimum requirements:**
- Noted that DONE broadcast was added (beyond explicit criteria, but aligned with invariant)
- Verified code backreferences were added correctly
- Acknowledged investigation item (race condition) was appropriately deferred

**Key observation:** The agent actually ran the tests (`All 75 tests pass`) rather than just checking tests exist. The prompt didn't explicitly require this, but the agent inferred it from criterion 4.

**Implications for prototype:**
1. The prompt is functional - agent followed the review phases correctly
2. Agents will run tests if the criterion mentions "tests pass"
3. No linked artifacts (investigation/subsystem) meant less context - agent still produced good review
4. The structured output format worked - agent produced valid YAML decision

<!--
GUIDANCE:

Summarize what was learned, distinguishing between what you KNOW and what you BELIEVE.

### Verified Findings

Facts established through evidence (measurements, code analysis, reproduction steps).
Each finding should reference the evidence that supports it.

Example:
- **Root cause identified**: The ImageCache singleton holds references indefinitely,
  preventing garbage collection. (Evidence: heap dump analysis, see Exploration Log 2024-01-16)

### Hypotheses/Opinions

Beliefs that haven't been fully verified, or interpretations that reasonable people
might disagree with. Be honest about uncertainty.

Example:
- Adding LRU eviction is likely the simplest fix, but we haven't verified it won't
  cause cache thrashing under our workload.
- The 100MB cache limit is a guess; actual optimal size needs load testing.

This distinction matters for decision-making. Verified findings can be acted on
with confidence. Hypotheses may need more investigation or carry accepted risk.
-->

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