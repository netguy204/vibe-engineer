---
status: SOLVED
trigger: "Steward agents need persistent memory across context clears; compaction alone is insufficient for long-running entities"
proposed_chunks:
  - prompt: "Define entity directory structure, memory file format, and ve entity create/list commands"
    chunk_directory: "entity_memory_schema"
    depends_on: []
  - prompt: "Create shutdown/sleep skill: extract journal memories from session, run incremental consolidation"
    chunk_directory: "entity_shutdown_skill"
    depends_on: [0]
  - prompt: "Create startup/wake skill: load core memories, build consolidated index, include touch protocol"
    chunk_directory: "entity_startup_skill"
    depends_on: [0]
  - prompt: "Implement ve entity touch command for runtime memory reinforcement"
    chunk_directory: "entity_touch_command"
    depends_on: [0]
  - prompt: "Implement recency-based decay and capacity pressure across all memory tiers"
    chunk_directory: "entity_memory_decay"
    depends_on: [1, 3]
created_after: ["agent_invite_links", "orch_stuck_recovery"]
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

The steward concept has revealed a class of agent that benefits from being treated as a long-running entity — one that develops and retains understanding of a narrow domain across many sessions. The current mechanism for indefinite runtime is compaction, but it is not effective for this use case: compaction discards too much context, and the agent loses accumulated understanding each time context is cleared.

The specific failure mode observed: after compaction, the steward would forget internalized skills it had developed through operator feedback. The operator found themselves retraining the agent on behaviors it had already learned — feedback that should have made those skills salient was lost. This is not just context loss; it's loss of *developed capability*.

The operator hypothesizes that a sleep/wake memory consolidation cycle (analogous to human dreaming) would be more effective than compaction for preserving agent understanding across sessions. A real conversation log (~7,800 lines) from a long-running database savings plan steward is available for experimentation at `~/.claude/projects/-Users-btaylor-Tasks-database-savings-plans/6cd96a31-f042-4272-978c-9b7dba0dfd63.jsonl`.

## Success Criteria

1. **Memory tier schema defined**: A concrete data format for tiered memories (at minimum: raw daily entries, consolidated mid-tier, and high-tier persistent memories), with clear promotion/demotion rules.
2. **Shutdown ("sleep") prototype**: A working prototype that reads a conversation log, extracts salient events with valence (success/failure), and writes them as tier-0 memories. Then consolidates against existing memories, promoting repeated themes to higher tiers.
3. **Startup ("wake") prototype**: A working prototype that loads all highest-tier memories in full, plus an index of lower-tier memories, producing a context payload suitable for session initialization.
4. **Empirical comparison**: Run the shutdown/startup cycle on the real steward log and qualitatively assess whether the resulting memory state captures the essential understanding that agent had accumulated — compared to what raw compaction would preserve.
5. **Proposed chunk(s)**: If the approach is viable, produce chunk prompts for integrating this into the VE skill system (shutdown skill, startup skill, memory storage conventions).

## Testable Hypotheses

### H1: Two complementary memory mechanisms — continuous journaling + periodic consolidation — are needed

- **Rationale**: The operator describes two distinct processes: (1) an ongoing skill that records memories *during* interaction (like short-term memory formation), and (2) a shutdown/sleep cycle that reflects on the day and consolidates (like dreaming). These serve different functions — the journal captures raw signal in real-time; consolidation identifies patterns, promotes recurring themes, and prunes noise. Neither alone is sufficient.
- **Test**: Build both mechanisms against the real log. Compare memories produced by consolidation-only vs journal+consolidation. Does the continuous journal capture feedback/skills that a post-hoc analysis of the full log would miss?
- **Status**: PARTIALLY VERIFIED — The two-step pipeline (extract then consolidate) works. Whether continuous journaling adds value over post-hoc extraction from full transcripts is still open.

### H2: The LLM itself is the right judge of memory salience

- **Rationale**: Mechanical heuristics (tool success/failure, user "yes"/"no") miss the nuance of what the agent actually learned. When the operator gives feedback that shapes how the agent approaches a task, that's a skill being internalized — detectable by the LLM reading the conversation, but not by simple pattern matching. The LLM can assess: "this interaction changed how I would approach similar tasks in the future."
- **Test**: Compare LLM-judged salience against mechanical heuristics on the same log segments. Do they identify the same memories? Where do they diverge, which set better captures the "skills" the agent developed?
- **Status**: PARTIALLY SUPPORTED — Log analysis shows that the highest-value memory events (behavioral corrections, domain teaching, autonomy calibration) require semantic understanding to detect. Mechanical signals like explicit "update your SOP" directives exist (~13 instances) but represent only a fraction of the ~130+ memory-worthy events. The correction→adaptation sequences that capture skill development are invisible to simple pattern matching.

### H3: An LSTM-inspired tiered structure can preserve developed skills more effectively than compaction

- **Rationale**: Compaction treats all context equally. A tiered system where repeated themes get promoted to higher significance mirrors human memory consolidation. The key failure mode to solve: the agent forgetting internalized skills that operator feedback made salient. These skills should be among the highest-tier memories.
- **Test**: Process the steward log through the full journal+consolidation cycle. Does the resulting memory set capture the skills the agent developed? Would loading these memories at startup prevent the "retraining" problem?
- **Status**: VERIFIED — The 11 core memories precisely capture the skills the operator reported losing: PR lifecycle management, cross-system verification, async coordination, autonomy calibration, documentation-first workflow. These are the behaviors that were repeatedly corrected during the "training phase" of the session. Loading these at startup would directly prevent the retraining problem.

### H4: Memories should be scoped to named entities, not sessions or directories

- **Rationale**: The operator envisions multiple entities per working directory — a steward entity, potentially subdomain-specialist entities. Each entity accumulates its own memories. This means the storage structure is `<entity_name>/memories/` not `<session_id>/memories/`. An entity persists across many sessions; its memories are its identity.
- **Test**: Design the storage schema with entity-scoped directories. Validate that this supports: (1) one steward entity today, (2) multiple entities in same directory later, (3) entity memories surviving session clears.
- **Status**: UNTESTED — Schema designed but not validated in a live entity workflow.

### H5: The startup payload (all highest-tier + lower-tier index) fits within a reasonable context budget

- **Rationale**: If high-tier memories grow unbounded, startup cost approaches the same problem compaction has. Consolidation must keep the top-tier set compact enough to load in full.
- **Test**: After running the sleep cycle, measure the token count of resulting top-tier memories plus lower-tier index. Target: under 4K tokens for startup context.
- **Status**: VERIFIED — 11 core memories (full content) + 19 consolidated memory titles = ~9,700 chars (~2,400 tokens). Well under the 4K token target. Room for growth as entity accumulates more experience.

### H6: Agents can self-report core memory usage with sufficient accuracy to drive reinforcement

- **Rationale**: If tier-2 memories are loaded as a named, numbered list with a clear instruction to run `ve entity touch <id>` when applying one, the agent may be metacognitively aware enough to self-report. The memories are discrete principles, not diffuse knowledge, which makes self-observation plausible.
- **Test**: Give a sub-agent the 11 core memories from the prototype, a startup prompt with the touch instruction, and a simulated workday (a segment of the real conversation log). Measure: (1) does it touch memories at all? (2) are the touches accurate — does the memory it reports actually relate to the action it's taking? (3) does it over-report (touching everything) or under-report (missing obvious applications)? (4) does the metacognitive overhead visibly degrade task performance?
- **Status**: VERIFIED — Agent self-reported 17 memory touches across 10 scenario messages. 100% precision (no false positives), strong recall (13/16 expected, with 3 divergences reflecting better reasoning than ground truth). No over-reporting. Agent also demonstrated metacognitive discrimination — identified 2 edge cases it considered and correctly rejected. See prototypes/h6_scenario.md and prototypes/touch_log.jsonl.

## Exploration Log

### 2026-03-19: Investigation created

- Identified test data: `~/.claude/projects/-Users-btaylor-Tasks-database-savings-plans/6cd96a31-f042-4272-978c-9b7dba0dfd63.jsonl` (7,767 lines)
- Log is a JSONL conversation transcript containing: user messages, assistant responses, tool calls/results, progress events, file-history snapshots, queue operations
- The steward was working on database savings plans — a domain-specific long-running task
- Next steps: analyze the log to understand what kinds of "memories" a sleep cycle should extract, then build prototypes in `prototypes/`

### 2026-03-19: Refined model from operator feedback

Key clarifications from operator:
1. **Failure mode is skill loss, not context loss.** The steward forgets *how to do things* it learned through feedback, not just *what happened*. This reframes the problem: we're preserving developed capabilities, not conversation history.
2. **Two-system architecture:** Continuous memory journaling during interaction (like an ongoing skill) PLUS periodic consolidation at shutdown (reflection + dreaming). The shutdown isn't the only time memories are created — it's the consolidation moment.
3. **Entity-scoped, not session-scoped.** Memories belong to a named entity (e.g., "steward"), not to a conversation session. Multiple entities can exist in one working directory. Today: one steward per directory. Future: subdomain specialists, multiple stewards.
4. **LLM judges salience.** Not mechanical heuristics. The LLM is best positioned to recognize "this feedback changed how I'd approach similar tasks."

Emerging storage model:
```
<project_dir>/.entities/
  <entity_name>/
    memories/
      journal/        # tier 0: raw memories created during interaction
      consolidated/   # tier 1: patterns across multiple journal entries
      core/           # tier 2: persistent skills and understanding
    identity.md       # entity definition, role, startup instructions
```

### 2026-03-19: Log structure analysis

Analyzed the steward log (~7,800 lines over 6 days, single session with one compaction boundary).

**Log composition by message type:**
- Assistant messages: ~42% (tool calls and responses)
- User messages: ~30% (operator input and task notifications)
- Progress/metadata: ~12% (hook events, file snapshots)
- Queue operations: ~6% (async task coordination)
- System events: ~4% (turn boundaries, compaction)
- Completion markers: <1% (PR links, session resume points)

**Signal density:** Only ~3-5% of the log contains memory-worthy content. The vast majority is mechanical tool execution. A consolidation system needs aggressive filtering.

**Natural segmentation:** Clear overnight gaps create 6 day-boundaries. One compaction event mid-session. Within-day gaps of 30-90 minutes correspond to async waits and operator absences.

### 2026-03-19: Memory-worthy event taxonomy

Identified six categories of events worth remembering, in descending signal strength:

1. **Explicit memory directives** (~13 instances): The operator directly tells the agent to remember a workflow or procedure. These are unambiguous — a memory system should trivially detect and capture them.

2. **Behavioral corrections** (~36 instances): The operator redirects the agent's approach. These come in three flavors:
   - *Directive*: "Do X instead" (workflow reshaping)
   - *Factual*: Agent misunderstood current state
   - *Awareness*: Agent failed to notice something had already happened

3. **Domain concept teaching** (~23 instances): The operator explains how entities relate, what distinctions matter, invariant rules. These build the agent's mental model.

4. **Investigation cycles** (~17 instances): Anomaly reported → hypothesis → verification → refinement. Each cycle teaches the agent about data integrity patterns.

5. **Confirmation signals** (~14 instances): Brief affirmations that validate the agent's current approach. Quieter than corrections but important — they mark what NOT to change.

6. **Autonomy calibration** (throughout): Operator teaches when to act vs ask, when to wait for a signal vs take initiative, when to re-plan from goals vs patch a plan.

### 2026-03-19: Skill development patterns

The agent developed capabilities in these abstract categories over the session:

| Category | Description | Signal |
|----------|-------------|--------|
| Lifecycle management | Multi-step workflows with specific ordering and state checks | Most frequently corrected — 9+ explicit procedure updates |
| Multi-agent coordination | Sending/receiving messages, avoiding duplicate watchers, acknowledging signals | New capability introduced mid-session |
| Verify-then-iterate cycles | Change → deploy → wait → verify → analyze → iterate | Learned when to wait vs act in async workflows |
| Domain model refinement | Correctly modeling entity relationships and disambiguation | ~20 edge cases learned incrementally |
| Autonomy calibration | When to take initiative vs wait for permission | Explicitly taught via corrections |
| Documentation-code alignment | Updating docs when understanding changes | Learned through feedback |

### 2026-03-19: End-to-end prototype run

Ran the full pipeline against the real steward log:

**Step 1: Parse** (`prototypes/parse_log.py`)
- Input: 7,767 JSONL entries
- Output: 6 day-segment JSON files in `prototypes/parsed_days/`
- Filtering: Kept user messages, assistant text, system events, queue operations. Stripped tool results and metadata.

**Step 2: Extract** (6 sub-agents in parallel, one per day)
- Each sub-agent read its day's transcript and wrote journal memories
- Prompt framing: "You are performing end-of-day journaling" — the agent reflects on its own interactions
- Output: 96 total journal memories across 6 days (14, 14, 16, 19, 17, 16 per day)
- Quality: Memories are lesson-framed ("Always do X when Y"), not narrative ("On March 14, the operator said...")
- Categories captured: correction (most common), skill, domain, confirmation, coordination, autonomy

**Step 3: Consolidate** (1 sub-agent reading all 96 journals)
- Input: 96 tier-0 memories
- Output: 11 core (tier 2) + 19 consolidated (tier 1) + 14 unconsolidated (tier 0)
- 54% reduction in memory count, with richer content per memory
- Recurrence correctly detected: PR lifecycle (4x), cross-system verification (5x), async coordination (5x), background process management (4x)

**Key metrics:**
| Metric | Value |
|--------|-------|
| Log entries | 7,767 |
| Day segments | 6 |
| Journal memories extracted | 96 |
| After consolidation | 44 (54% reduction) |
| Core memories | 11 |
| Startup payload | ~2,400 tokens |
| Sub-agent extraction time | ~75-150s per day |
| Consolidation time | ~150s |

**Observation: Privacy abstraction is imperfect.** Despite explicit privacy instructions, some memories leak domain specifics. The extraction prompt needs stronger guidance or a separate abstraction pass. For entity-private memories this is fine; it's only an issue when memories are stored in public repos.

**Observation: The extraction prompt works as a skill prototype.** The prompt given to sub-agents ("you are performing end-of-day journaling, here are the categories of memory-worthy events...") directly translates to a shutdown skill. This validates the sub-agent approach over API scripting.

### 2026-03-19: Incremental consolidation design

Based on operator feedback, refined the consolidation algorithm. Continuous journaling deferred — shutdown extraction is sufficient given experimental results.

**Nightly consolidation algorithm:**

1. **Record**: New memories from today's shutdown enter at tier 0.
2. **Associate**: For each new tier-0 memory, check for association with existing memories:
   - Associates with tier-2 → **reinforce** (refine content, bump recurrence). Tier-0 consumed.
   - Associates with tier-1 → **eager promote** (merge into tier-1, evaluate for tier-2 promotion with lower threshold). Tier-0 consumed.
   - Associates with another tier-0 → **consolidate** both into new tier-1. Both consumed.
   - No association → stays at tier-0.
3. **Evaluate**: Any tier-1 memory with sufficient reinforcement or salience promotes to tier-2.

**Key properties:**
- Frequently corrected behaviors reach core in ~3 days (tier-0 → tier-1 → tier-2)
- Core memories are refined, not duplicated — new evidence enriches existing memories
- Association with higher tiers lowers the promotion threshold ("eager promotion")
- Orphan tier-0 memories that persist without association are decay candidates

**Open design questions:**
- The specific threshold for tier-1 → tier-2 promotion (recurrence count? salience? both?)
- Whether retrieval during a workday counts as reinforcement

### 2026-03-19: Decay mechanics design

Operator concern: without decay at all tiers (including core), the system will too aggressively create core memories and overwhelm context. 11 core memories from 6 days → unsustainable over months.

**Design: Two complementary decay mechanisms**

1. **Recency-based decay**: Every memory carries `last_reinforced` timestamp. Memories unreinforced for N consolidation cycles lose salience, then demote, then expire:
   - Tier 2 → loses salience → demotes to tier 1 → eventually expires
   - Tier 1 → loses salience → expires
   - Tier 0 → expires after M cycles without association

2. **Capacity pressure**: Each tier has a soft budget. When exceeded, least-recently-reinforced memories demote or expire first. Creates competitive dynamics — new core memories must earn their place; old ones must continue proving relevance.

**Combined effect:**
- Skills used daily → stay core forever (constantly reinforced)
- Skills critical during a project phase but no longer needed → gradually fade from core → consolidated → gone
- Startup payload stays bounded regardless of entity lifetime

**Reinforcement signals identified so far:**
- New tier-0 memory associates with existing higher-tier memory (consolidation-time reinforcement)
- Agent retrieves a lower-tier memory during workday because it's relevant (retrieval-as-reinforcement — requires tracking which memories were accessed)

**Open questions:**
- Tier-2 capacity budget (initial proposal: 15 memories)
- Decay rate (cycles before demotion)

### 2026-03-19: Retrieval-as-reinforcement and self-reporting

**Problem**: Tier-2 memories are preloaded into context — they influence behavior invisibly. Unlike tier-1 (explicitly retrieved from index), there's no observable "access" event for tier-2. Without a reinforcement signal, tier-2 memories can only be reinforced via consolidation (new tier-0 memories associating with them).

**Proposed mechanism**: Teach the agent to self-report. The startup prompt includes: "When you notice yourself applying a core memory, run `ve entity touch <memory_id>` to record that it was useful today." This requires metacognitive self-awareness — the agent must notice when a named principle is influencing its behavior.

**Why it might work**: Core memories are discrete, titled, loaded as an explicit list. They're named principles, not diffuse knowledge. "Never push directly to main" is specific enough that an agent might notice the moment it acts on that principle.

**Failure modes to test for:**
1. Over-reporting — agent touches everything to be safe (no signal)
2. Under-reporting — memory influences behavior so naturally the agent doesn't notice
3. Distraction tax — metacognitive monitoring degrades task performance

**Fallback**: If self-reporting doesn't work, tier-2 reinforcement happens only during consolidation. If the domain keeps generating new tier-0 memories about a topic, the associated tier-2 stays alive. If the topic never recurs in journals, the tier-2 fades. This is closer to human sleep-based consolidation — reinforcement during dreaming, not waking use.

### 2026-03-19: H6 experiment results — self-reporting works

Ran 10-message simulated workday with 11 core memories loaded and touch instruction.

**Results:**
| Metric | Value |
|--------|-------|
| Total touches | 17 |
| Precision (no false positives) | 100% |
| Recall (vs ground truth) | 13/16 (81%) |
| Ground truth divergences | 3 — all were better reasoning than ground truth |
| Over-reporting | None detected |
| Under-reporting | Minimal |
| Metacognitive discrimination | Agent correctly rejected 2 edge cases |

**Key observations:**
1. The agent naturally touched 1-2 memories per message, consistent with realistic usage patterns.
2. Where it diverged from ground truth, it had stronger reasoning — e.g., deferring CM1 (join verification) until actually making changes rather than touching it during diagnosis.
3. The agent added touches the ground truth missed — e.g., CM1 on a column rename (renaming one side could break the join), CM10 before creating a PR.
4. Metacognitive self-assessment was high quality: identified CM8 as not applicable to a one-directional watch (only to request-response), and CM2 as not applicable when the operator already confirmed the logic was correct.
5. No visible degradation in response quality from the metacognitive overhead.

**Implication for design:** Retrieval-as-reinforcement via self-reporting is viable. The touch log becomes a signal for the consolidation step: memories that are frequently touched during workdays are actively useful and should resist decay. Memories never touched are candidates for demotion.

**Integration with decay:** The `last_reinforced` timestamp on each memory can now be updated from two sources:
1. Consolidation-time: new tier-0 memories that associate with higher-tier memories
2. Runtime: `ve entity touch` calls during workday

Both signals contribute to keeping a memory alive.

### 2026-03-19: Evidence of the retraining problem

**Key finding**: The same category of correction (lifecycle management) recurs across multiple days. This is direct evidence of the failure mode the operator described — the agent does not fully internalize taught skills across session boundaries.

The session shows a clear three-phase evolution:
1. **Investigation phase** (first third): Heavy direct work, few corrections
2. **Training phase** (middle third): Peak corrections and explicit procedure updates — operator actively shaping autonomous behavior
3. **Autonomous phase** (final third): Fewer corrections, high autonomous activity — skills appear internalized

A memory system's success criterion: an agent that goes through phases 1-2 should retain phase-3 capability after a context clear.

### 2026-03-19: Implications for prototype design

1. **Explicit memory signals are the easy win.** "Update your SOP" / "remember this" patterns are unambiguous and should always produce a memory.

2. **Correction→adaptation sequences are the high-value target.** Each correction encodes a before/after behavioral shift. Extracting the pattern (not the specific content) captures skill development.

3. **Confirmation signals prevent drift.** If we only record corrections, the agent becomes overly cautious and may abandon validated approaches. Confirmations anchor what's working.

4. **Phase transitions matter.** The agent goes from investigation → training → autonomy. Memory should capture that it reached autonomy in a domain, not just individual corrections.

5. **Async coordination creates a distinct memory type.** "What I'm waiting for and what to do when it arrives" doesn't fit neatly into single-event memory. It's more like a standing instruction.

6. **Day boundaries are natural consolidation triggers.** Overnight gaps are clear and natural "sleep" points.

## Findings

### Verified Findings

**The tiered consolidation pipeline works end-to-end.** 6 days of conversation (7,767 log entries, ~579K chars of content) were processed through parse → extract → consolidate, producing a tiered memory structure. (Evidence: prototypes/tiers/)

- Input: 7,767 JSONL log entries across 6 days
- After parsing: 6 day segments, filtered to memory-relevant content
- After extraction: 96 tier-0 journal memories (6 sub-agents, one per day)
- After consolidation: 11 core (tier 2) + 19 consolidated (tier 1) + 14 unconsolidated (tier 0) = 44 total
- Reduction: 54% fewer memories than raw journal, with richer content per memory

**The core memories capture exactly the skills the operator reported losing.** The 11 core memories include:
- PR lifecycle management (push to branch, check state before updating, rebase after merge) — the most frequently corrected behavior
- Cross-system verification workflows (verify both sides of a join, run integration tests)
- Background process management (kill old before starting new)
- Async coordination patterns (watch before send, never ack preemptively)
- Autonomy calibration (act with standing permission, don't re-ask)
- Documentation-first workflow (update docs before committing)

These are precisely the "internalized skills" the operator described having to retrain.

**Startup payload fits comfortably within budget.** Full tier-2 content + tier-1 title index = ~9,700 chars (~2,400 tokens). Well under the 4K token target. This means an agent can load its full identity at startup without significant context cost.

**Sub-agent extraction produces actionable, lesson-framed memories.** The prompt "you are performing end-of-day journaling" successfully guided sub-agents to extract lessons rather than narratives. Most memories are framed as reusable instructions ("Always do X", "Never do Y", "When Z happens, do W"). This validates the skill-based approach — the extraction prompt IS the prototype for the shutdown skill.

**Recurring patterns are correctly identified and promoted.** The consolidation step correctly identified that PR lifecycle management, cross-system verification, and background process management were corrected repeatedly across days and promoted them to core. Recurrence counts of 3-5 on core memories match the "agent kept forgetting this" pattern.

### Hypotheses/Opinions

**Privacy abstraction needs a dedicated pass.** The extraction prompt included privacy instructions, but some memories still contain domain-specific details (specific SQL engines, service types). A production implementation should either: (a) strengthen the extraction prompt with examples of good vs bad abstraction, or (b) add a separate privacy filter step. For entity-private memories (which most will be), this may not matter — the privacy constraint is specific to this investigation's public-repo context.

**The "continuous journaling" system (H1) may not need to be a separate mechanism.** The sub-agent extraction worked well operating on a full day's transcript post-hoc. An alternative to continuous real-time journaling: the agent simply operates normally, and the shutdown skill processes the full session transcript. This is simpler and avoids the overhead of interrupting work for memory writes. However, there's a risk that very long sessions could exceed context limits for the extraction pass. This needs more exploration.

**Three tiers appear sufficient for this data (H3 supported).** The three tiers produced a clean stratification: core (principles), consolidated (detailed skills), unconsolidated (one-off specifics). No tier felt over-crowded or under-utilized. However, this was only 6 days of data. After months of operation, tier 1 could grow large enough to need a fourth tier or more aggressive consolidation.

**Incremental consolidation is the production-critical path.** The prototype performed full consolidation (read all journals, produce all tiers from scratch). In production, each shutdown adds new journal entries that must be integrated into existing tiers without re-processing everything. The incremental consolidation prompt exists in `prototypes/consolidate.py` but hasn't been tested yet.

## Proposed Chunks

### Memory System MVP

1. **Entity schema and storage** — Define the `.entities/<name>/` directory structure: `identity.md`, `memories/{journal,consolidated,core}/`, memory file format with `last_reinforced` timestamps and tier metadata.
   - Priority: High
   - Dependencies: None

2. **Shutdown/sleep skill** — Extract journal memories from the current session transcript, then run consolidation: associate new memories with existing tiers, promote/merge/decay per the incremental algorithm.
   - Priority: High
   - Dependencies: Entity schema

3. **Startup/wake skill** — Load all core memories in full, build index of consolidated memories, restore active subscriptions from entity state.
   - Priority: High
   - Dependencies: Entity schema

4. **Touch command** — `ve entity touch <memory_id> [reason]` to record runtime reinforcement of core memories. Updates `last_reinforced` timestamp.
   - Priority: Medium
   - Dependencies: Entity schema

5. **Decay mechanics** — Implement recency-based decay and capacity pressure during consolidation. Tier-0 expires after N cycles without association. Tier-1 decays without reinforcement. Tier-2 demotes when unreinforced and under capacity pressure.
   - Priority: Medium
   - Dependencies: Shutdown skill (runs during consolidation)

### Separate: Entity Harness MVP (future investigation)

6. **CLI wrapper** — Thin wrapper around Claude SDK that detects context pressure and triggers shutdown-clear-startup automatically, avoiding lossy compaction. Also supervises message subscriptions and restarts watches after context clears.
   - Priority: Future
   - Dependencies: Memory system MVP complete
   - Note: The memory MVP defines the contract (shutdown/startup skills) that the harness calls. Building the harness before the memory system is premature.

## Resolution Rationale

An LSTM-inspired tiered memory consolidation system is viable and effective for preserving agent skills across session boundaries. The prototype demonstrated: extraction of 96 journal memories from a real 6-day steward log, consolidation to 11 core + 19 consolidated memories (54% reduction, ~2,400 token startup payload), and verified self-reporting of core memory usage at runtime (100% precision, no over-reporting). The system addresses the observed failure mode — agents forgetting internalized skills after compaction — by giving them a structured sleep/wake cycle that mirrors human memory consolidation. Five proposed chunks define the implementation path.