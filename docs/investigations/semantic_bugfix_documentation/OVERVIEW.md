---
status: ONGOING
trigger: "Semantic bug fix revealed incomplete backreference story"
proposed_chunks: []
created_after: ["bug_chunk_semantic_value"]
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

While completing the `orch_agent_question_tool` chunk (a semantic bug fix against
`orch_scheduling`), we realized that agents following backreferences from code to
the original chunk would arrive at an incomplete understanding.

**The scenario**: `orch_scheduling` introduced `_is_error_result()`, a text-parsing
heuristic for detecting errors in agent output. `orch_agent_question_tool` removed
this function because it caused false positives - the SDK's `is_error` flag is
authoritative. This is a semantic bug: the original understanding of "how to detect
errors" was wrong.

**The problem**: An agent following the `# Chunk: docs/chunks/orch_scheduling`
backreference in `src/orchestrator/agent.py` would read about the scheduling layer's
design but wouldn't learn that the error detection approach was later corrected.
They'd see the original intent without the refined understanding.

**What's at stake**: The backreference system is meant to help future agents
understand code intent. If semantic bug fixes don't propagate to the chunks they
correct, agents will inherit outdated understanding and potentially reintroduce
the same bugs.

## Success Criteria

1. **Define the information gap**: Clearly articulate what an agent misses when
   they only read the original chunk without awareness of semantic corrections.

2. **Identify documentation patterns**: Determine how semantic bug fixes should
   reference or update the chunks they correct, so agents arrive at complete
   understanding.

3. **Evaluate trade-offs**: Consider whether the solution should:
   - Update original chunks (risks breaking their historical accuracy)
   - Add forward-references from original to correcting chunk
   - Add backward-references from correcting chunk to original (already exists via `parent_chunk`?)
   - Use a different mechanism entirely

4. **Propose concrete changes**: If changes to the chunk system are warranted,
   document them as proposed chunks with clear specifications.

## Testable Hypotheses

<!--
GUIDANCE:

Frame your beliefs as hypotheses that can be verified or falsified. This encourages
objective investigation rather than confirmation bias.

For each hypothesis, consider:
1. **Statement**: What do you believe might be true?
2. **Test**: How could this hypothesis be verified or disproven?
3. **Status**: UNTESTED | VERIFIED | FALSIFIED | INCONCLUSIVE

Example format:

### H1: The memory leak is in the image processing pipeline

- **Rationale**: Memory issues correlate with image-heavy requests
- **Test**: Profile memory allocation during image processing vs other operations
- **Status**: UNTESTED

### H2: Switching to streaming would reduce memory pressure

- **Rationale**: Current implementation loads entire files into memory
- **Test**: Prototype streaming approach and compare peak memory usage
- **Status**: UNTESTED

Update status as you explore. A falsified hypothesis is still valuable - it
eliminates possibilities and focuses the investigation.
-->

## Exploration Log

### 2026-01-13: Triggering scenario documented

While completing `orch_agent_question_tool`, we identified the semantic bug pattern:

**Original chunk**: `orch_scheduling` (ACTIVE)
- Introduced `_is_error_result()` function for text-based error detection
- Code had backreference: `# Chunk: docs/chunks/orch_scheduling`

**Correcting chunk**: `orch_agent_question_tool` (now ACTIVE, `bug_type: semantic`)
- Removed `_is_error_result()` - SDK's `is_error` flag is authoritative
- Added new backreferences at the modified locations

**Current state of backreferences in code**:
```python
# src/orchestrator/agent.py, lines 472, 581, 677:
# Chunk: docs/chunks/orch_agent_question_tool - Remove text-parsing error heuristics
```

**The gap**: The module-level backreference still points to `orch_scheduling` (line 1),
but nothing in `orch_scheduling`'s GOAL.md warns readers that its error detection
approach was later corrected. An agent reading `orch_scheduling` for context would
not know to also read `orch_agent_question_tool`.

**Existing mechanisms considered**:
- `parent_chunk` field: Currently "null for new work, chunk directory for corrections"
  - We didn't use this for `orch_agent_question_tool` because it's not a correction
    to a specific chunk - it's a bug fix that happened to touch code introduced by
    multiple chunks
- `created_after` field: Tracks causal ordering, not semantic relationships
- Backreferences in code: Point forward in time (new code → its chunk), not backward

## Findings

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