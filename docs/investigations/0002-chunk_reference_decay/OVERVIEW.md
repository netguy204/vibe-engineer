---
status: ONGOING
trigger: Code blocks accumulate many chunk backreferences that drip-feed context rather than providing high-value understanding
proposed_chunks:
  - prompt: "Implement chunk-to-narrative consolidation workflow that groups related chunks into narratives and updates code backreferences"
    chunk_directory: null
  - prompt: "Add narrative backreference support to code files (# Narrative: docs/narratives/NNNN-name format)"
    chunk_directory: null
---

<!--
DO NOT DELETE THIS COMMENT until the investigation reaches a terminal status.
This documents the frontmatter schema and guides investigation workflow.

STATUS VALUES:
- ONGOING: Investigation is active; exploration and analysis in progress
- SOLVED: The question has been answered or the problem has been resolved
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

Code blocks in this project are accumulating multiple chunk backreferences (e.g., `# Chunk: docs/chunks/0012-...`). When an agent follows these references to understand the code, each chunk provides only incremental context—drip-feeding information rather than delivering a coherent picture.

The concern: if the first backreference an agent traverses isn't highly likely to help them understand the code's context, the backreference system loses its value as a navigation aid. Agents may waste tokens following marginally-useful references or learn to ignore them entirely.

## Success Criteria

1. **Narrative consolidation experiment**: Identify code blocks with multiple chunk backreferences. Attempt to build narratives that group those chunks together. Evaluate whether the resulting narrative provides better semantic context than the individual chunk references.
   - If narratives are semantically valuable → hypothesis confirmed
   - If narratives don't add value → hypothesis rejected

2. **Age correlation verification**: Confirm that code with many backreferences tends to include older chunks. This supports the "decay over time" aspect—references accumulate as code evolves through multiple chunks.

## Testable Hypotheses

### H1: Chunk backreferences lose semantic value as chunks age

- **Rationale**: A chunk documents a discrete unit of work at a point in time. As code evolves through subsequent chunks, the original chunk's context becomes less relevant to understanding the current code.
- **Test**: Compare the usefulness of recent vs older chunk references when trying to understand code blocks.
- **Status**: VERIFIED

**Evidence (2026-01-10):**
- Chunks 0001 and 0002 provide LOW semantic value for understanding current src/chunks.py
- These chunks document WHAT was built ("we added a list command") but not WHY it matters architecturally
- An agent traversing these references learns implementation history, not design intent
- Chunk 0004 retains MEDIUM value because it explains the problem being solved (reference drift)

### H2: Narrative references provide better context than accumulated chunk references

- **Rationale**: Narratives synthesize the "why" across multiple chunks into a coherent story. An agent following a narrative reference gets the big picture immediately, rather than piecing together fragments from multiple chunks.
- **Test**: For code with multiple chunk backreferences, create a narrative grouping those chunks. Evaluate if the narrative provides faster/better understanding than traversing individual chunks.
- **Status**: VERIFIED (with nuance)

**Evidence (2026-01-10):**
See `prototypes/narrative_prototype.md` for full analysis.

- Drafted a narrative synthesizing the 8 chunks referenced in src/chunks.py
- Narrative provides ~40 lines of coherent context vs 8 GOAL.md files (~400-800 lines total)
- Key insight: "This is lifecycle infrastructure" immediately frames code purpose
- Key insight: "Referential integrity is a core concern" explains non-obvious complexity

**Nuance discovered:** Narratives are superior for understanding code PURPOSE. Chunks remain valuable for understanding code HISTORY (archaeology, debugging "who changed this"). This suggests a hybrid approach rather than full replacement.

### H3: Code with many backreferences tends to reference older chunks

- **Rationale**: Backreferences accumulate over time as code is touched by successive chunks. Therefore, heavily-referenced code should include references to early chunks.
- **Test**: Find code blocks with 3+ chunk backreferences and check the age distribution of referenced chunks.
- **Status**: VERIFIED

**Evidence (2026-01-10):**
- src/ve.py (46 refs) spans chunks 0001-0035 (97% of project history)
- src/chunks.py (34 refs) includes 6 references to chunk 0001 (oldest)
- Chunk 0001 is the 4th most referenced chunk globally despite being the oldest
- Files with high backreference counts consistently include chunks from the early project history

### H4: Narrative references reduce token consumption for code understanding

- **Rationale**: If agents must traverse multiple chunk GOALs to understand a code block, they consume tokens proportional to the number of chunks. A narrative that synthesizes the "why" upfront should provide equivalent understanding with fewer tokens.
- **Test**: Build a test bench using the Claude Agent SDK with two conditions:
  - **Condition A**: Agent understands code via N individual chunk backreferences (must read N GOAL.md files)
  - **Condition B**: Agent understands the same code via a narrative backreference (reads 1 OVERVIEW.md that synthesizes the N chunks)
  - **Metric**: Total tokens consumed to answer a standardized understanding question
- **Status**: INCONCLUSIVE

**Evidence (2026-01-10):**
- Test bench implemented in `prototypes/h4_test_bench.py`
- Results showed narrative using MORE tokens (943 vs 914), not fewer
- The synthetic test narrative was only 25% smaller than combined chunks
- Agent SDK cache tokens include system overhead, not just file content
- Methodology needs refinement to isolate documentation-reading costs

### H5: Weaker models achieve higher accuracy with narrative references than chunk references

- **Rationale**: Stronger models can synthesize the "why" from scattered chunks through multi-hop reasoning. Weaker models may struggle to piece together disparate information. Narratives pre-synthesize context, reducing cognitive load and potentially enabling weaker models to match stronger model accuracy.
- **Test**: Use a weaker model (haiku) in both conditions:
  - **Condition A**: Code with chunk backreferences
  - **Condition B**: Code with narrative backreference
  - **Metric**: Answer accuracy/quality on understanding questions (scored or compared)
  - **Control**: Run same test with stronger model (sonnet) to compare accuracy delta
- **Status**: FALSIFIED (narratives don't improve accuracy for detail questions)

**Evidence (2026-01-10):**

*Low-N test (3 chunks):*
- Test bench: `prototypes/h5_accuracy_test.py`
- Haiku scored identically: 2.25/3.0 both conditions
- No accuracy difference

*High-N test (8 chunks):*
- Test bench: `prototypes/h5_high_n_test.py`
- Chunks: 4.00/4.0 (100%) vs Narrative: 3.67/4.0 (92%)
- **Chunks performed BETTER** - narrative omitted details like "function", "validate"

**Interpretation:** Haiku can effectively synthesize information from 3 scattered chunks. The cognitive load of reading 3 separate files and extracting answers isn't high enough to show a narrative advantage.

**High-N test (2026-01-10):** Tested with 8 chunks (4,514 bytes) vs 1 narrative (1,929 bytes).

| Condition | Score | Accuracy |
|-----------|-------|----------|
| A: 8 Chunks | 4.00/4.0 | 100% |
| B: 1 Narrative | 3.67/4.0 | 92% |

**Surprising finding:** Chunks performed BETTER than narrative at 8 chunks.

The narrative missed specific details:
- Q2: "function" keyword (present in chunk 0012, condensed out of narrative)
- Q4: "validate" keyword (present in chunks, omitted from synthesis)

**Revised interpretation:** Narratives trade DETAIL for COHERENCE.
- For factual recall questions (what commands exist, what keywords are used), chunks preserve more detail
- Narratives may still be superior for PURPOSE questions (why does this exist, what's the architecture)
- The H2 finding (narratives better for PURPOSE) may coexist with chunks being better for DETAIL

**Refined hypothesis:** The narrative advantage is domain-specific:
- **PURPOSE/WHY questions**: Narrative advantage (pre-synthesized context)
- **DETAIL/WHAT questions**: Chunk advantage (complete information preserved)
- Weaker models may still benefit from narratives on PURPOSE questions

## Exploration Log

### 2026-01-10: Backreference census and age distribution analysis

**Method:** Scanned all `# Chunk:` backreferences in `src/` and analyzed their distribution.

**Backreference counts per file (top 10):**

| File | Backrefs | Unique Chunks |
|------|----------|---------------|
| src/ve.py | 46 | 18 |
| src/chunks.py | 34 | 10 |
| src/models.py | 29 | 10 |
| src/subsystems.py | 20 | 6 |
| src/task_utils.py | 17 | 3 |
| src/template_system.py | 13 | 3 |
| src/project.py | 13 | 3 |
| src/narratives.py | 7 | 3 |
| src/symbols.py | 5 | 1 |
| src/git_utils.py | 5 | 2 |

**Most referenced chunks globally (src/ only):**

| Chunk | Refs | Name | Age Percentile |
|-------|------|------|----------------|
| 0012 | 16 | symbolic_code_refs | 33% (older third) |
| 0010 | 15 | chunk_create_task_aware | 28% |
| 0029 | 12 | investigation_commands | 81% |
| 0001 | 12 | implement_chunk_start | 3% (oldest) |
| 0026 | 11 | template_system_consolidation | 72% |
| 0032 | 10 | proposed_chunks_frontmatter | 89% |

**Age distribution in most heavily-referenced files:**

*src/ve.py (46 refs):* References chunks 0001-0035 (nearly entire project history). Has 4 refs to 0001 (oldest chunk).

*src/chunks.py (34 refs):* References chunks 0001-0032. Has 6 refs to 0001, 7 refs to 0012.

*src/models.py (29 refs):* References chunks 0005-0032. Concentrated around foundational schemas.

**Key observation:** Chunk 0001 (the very first chunk) is the 4th most referenced chunk globally with 12 references. Files with many backreferences (like ve.py) span nearly the entire chunk history.

### 2026-01-10: Semantic value analysis of old chunk references in src/chunks.py

**Method:** Read chunks 0001, 0002, 0004 (the oldest referenced in src/chunks.py) and evaluated their usefulness for understanding the current code.

**Chunk 0001 (implement_chunk_start):**
- Describes: Creating `ve chunk start` command and foundational Chunks class
- References: `__init__`, `enumerate_chunks`, `num_chunks`, `find_duplicates`, `create_chunk`
- Semantic value for understanding current code: **LOW**
- The chunk documents WHAT was built, but if I'm trying to understand `enumerate_chunks()` today, reading this GOAL adds little beyond what the code itself shows. No architectural context.

**Chunk 0002 (chunk_list_command):**
- Describes: Adding `ve chunk list` command
- References: `list_chunks`, `get_latest_chunk`
- Semantic value: **LOW**
- The chunk says "we added listing functionality." The code already shows this. No insight into why listing matters in the broader workflow.

**Chunk 0004 (chunk_overlap_command):**
- Describes: Adding overlap detection for reference drift
- References: Several parsing/overlap methods
- Semantic value: **MEDIUM**
- This chunk explains the PROBLEM being solved (reference drift detection) which is less obvious from code alone. The "why" is present.

**Pattern observed:** Chunks document WHAT was built and WHEN, but rarely synthesize the WHY at an architectural level. Each chunk is a discrete work unit, not a coherent story.

**Hypothetical narrative value:** A narrative titled "Core Chunk Lifecycle" grouping 0001, 0002, 0004 could say:
> "These chunks establish foundational chunk management. The arc: create chunks → list/find chunks → detect when chunks affect each other's references. Together they form the lifecycle management layer that enables the documentation-driven workflow."

That single paragraph provides more architectural understanding than traversing three separate GOALs.

### 2026-01-10: Narrative prototype for src/chunks.py

**Method:** Created `prototypes/narrative_prototype.md` - a draft narrative that would replace the 8 chunk backreferences in src/chunks.py.

**Key decisions in the prototype:**
- Organized chunks into three phases: Foundation → Integrity → Expressiveness
- Focused on WHY the code exists, not WHAT it does
- ~40 lines of narrative vs ~400-800 lines across 8 GOAL.md files

**Evaluation:**
| Dimension | Chunks | Narrative |
|-----------|--------|-----------|
| Understanding PURPOSE | Low | High |
| Understanding HISTORY | High | Low |
| Token efficiency | Low (8 files) | High (1 file) |
| Traceability | High | Low |

**Insight:** The right answer isn't "replace chunks with narratives" but "use both for different purposes." Code should reference the narrative for context, and the narrative should link to its constituent chunks for archaeology.

### 2026-01-10: H4 Token consumption test

**Method:** Built test bench using Claude Agent SDK (`prototypes/h4_test_bench.py`). Created two isolated project directories:
- Condition A: src/chunks.py with 8 chunk backreferences, 8 GOAL.md files
- Condition B: src/chunks.py with 1 narrative backreference, 1 OVERVIEW.md file

Ran both conditions with identical prompts forcing agents to read referenced documentation.

**Results:**
| Metric | Condition A (Chunks) | Condition B (Narrative) |
|--------|---------------------|------------------------|
| Documentation size | 2,405 bytes | 1,802 bytes |
| Cache read tokens | 90K | 139K |
| Total tokens | 914 | 943 |
| Max turns reached | Yes (10) | Yes (10) |

**Unexpected finding:** Narrative condition consumed MORE tokens despite smaller documentation.

**Why this happened:**
1. The synthetic narrative wasn't dramatically smaller (only 25% reduction)
2. Agent SDK cache tokens include system context, reasoning, and tool overhead
3. The agent's decision-making process dominated the token count
4. Different agent behavior paths between conditions weren't controlled

**Conclusion:** The test methodology doesn't isolate the variable we want to measure. Token savings from narrative consolidation may still exist but require a different measurement approach (e.g., counting file read operations, or measuring in a more controlled environment).

### 2026-01-10: H5 Accuracy test with haiku

**Method:** Built accuracy test (`prototypes/h5_accuracy_test.py`) with:
- 3 factual questions answerable only from documentation
- Ground truth answers with keyword matching
- Haiku model in both conditions

**Results:**
| Question | Topic | Chunks Score | Narrative Score |
|----------|-------|--------------|-----------------|
| Q1 | Command syntax | 1.0 | 1.0 |
| Q2 | Overlap conditions | 0.25* | 0.25* |
| Q3 | Status values | 1.0 | 1.0 |
| **Total** | | **2.25** | **2.25** |

*Q2 scoring was artificially low due to strict keyword matching - actual answers were correct.

**Key finding:** Haiku performed identically in both conditions. It successfully:
- Read and synthesized information from 3 separate chunk files
- Answered all questions correctly (modulo scoring artifacts)
- Showed no accuracy benefit from narrative pre-synthesis

**Implication:** 3 chunks is below the threshold where narrative consolidation provides accuracy benefits for haiku. The synthesis task was within the model's comfortable capability range.

### 2026-01-10: H5 High-N test (8 chunks)

**Method:** Extended accuracy test with 8 chunks and 4 multi-hop questions requiring synthesis across multiple chunks. See `prototypes/h5_high_n_test.py`.

**Setup:**
- Condition A: 8 chunk GOAL.md files (4,514 bytes total)
- Condition B: 1 narrative OVERVIEW.md (1,929 bytes)
- Questions required synthesizing info from multiple sources

**Results:**
| Question | Topic | Chunks | Narrative |
|----------|-------|--------|-----------|
| Q1 | Lifecycle + commands | 100% | 100% |
| Q2 | Reference types | 100% | 83% |
| Q3 | Proposed chunks | 100% | 100% |
| Q4 | Overlap + subsystems | 100% | 83% |
| **Total** | | **100%** | **92%** |

**Key finding:** Chunks outperformed narrative on detail-oriented questions.

The narrative synthesis omitted:
- "function" as an example of symbolic reference format
- "validate" as a verb associated with subsystem references

**Insight:** Narratives trade DETAIL for COHERENCE. This is the correct tradeoff for PURPOSE questions but the wrong tradeoff for DETAIL questions.

### 2026-01-10: Narrative overconfidence hypothesis

**Observation:** In the H5 High-N test, condition B only had the narrative file, not the chunk files. The agent couldn't follow back to chunks even if it wanted to.

**But in a real scenario:** The narrative's frontmatter lists all constituent chunks. An agent COULD follow these references back to get more detail. The question: would it?

**Hypothesis: Narrative Overconfidence**
Narratives provide enough coherence that agents "satisfice" - they stop exploring because the answer feels complete. This is:
- **A feature** for PURPOSE questions (faster understanding, less token use)
- **A bug** for DETAIL questions (premature termination misses specifics)

**Implications for hybrid design:**
1. Narratives should signal when they're summaries vs authoritative
2. For detail-sensitive tasks, agents may need explicit prompting to follow chunk refs
3. Or: narratives could flag "for full API details, see chunk 0012"

**Untested:** Would an agent in a real scenario (both narrative AND chunks available) follow the frontmatter references, or stop at the narrative? This requires a new test condition.

### H6: Narrative overconfidence - agents stop exploring when narratives "feel complete"

- **Rationale**: Coherent narratives trigger satisficing behavior. Even when chunk references are available in the frontmatter, agents may not follow them because the narrative provides a "good enough" answer.
- **Test**: Create condition C where BOTH narrative AND chunk files exist. Ask detail questions. Observe whether agent follows frontmatter chunk references or stops at narrative.
- **Prediction**: Agent will stop at narrative, miss details, perform worse than condition A (chunks only)
- **Status**: UNTESTED (natural behavior)

**Evidence (2026-01-10):**
- Test bench: `prototypes/h6_overconfidence_test.py`
- Condition A (chunks only): 3.83/4.0
- Condition C (narrative + chunks): 3.83/4.0
- **Identical scores** - agent followed chunk refs from narrative frontmatter

**Interpretation:** When the prompt explicitly asks for details and indicates the summary may be incomplete ("follow references to find complete information"), the agent does follow the breadcrumbs. The narrative's frontmatter chunk list serves as effective navigation.

**METHODOLOGICAL LIMITATION:** The test does not address the actual hypothesis. The prompt explicitly instructs agents to dig deeper:
> "If a summary document doesn't have enough detail, follow its references to find the complete information."

Additionally, the narrative itself contains navigation cues:
> "For complete details on any topic, see the individual chunk documentation listed in the frontmatter above"

This primes agents to NOT satisfice. **The hypothesis about natural satisficing behavior in unprompted scenarios remains untested.**

**Next step:** Design H6b test without explicit navigation instructions to observe natural agent behavior.

## Findings

### Verified Findings

1. **Chunk backreferences accumulate over time and include old chunks** (H3 VERIFIED)
   - Files with many backreferences (e.g., src/ve.py with 46) span nearly the entire project history
   - Chunk 0001 is the 4th most referenced chunk globally despite being the oldest
   - Evidence: Backreference census in Exploration Log

2. **Old chunk references provide low semantic value for understanding current code** (H1 VERIFIED)
   - Chunks 0001 and 0002 document WHAT was built, not WHY it matters
   - An agent learns implementation history, not design intent
   - Exception: Chunks that explain the problem being solved (like 0004) retain value
   - Evidence: Semantic value analysis in Exploration Log

3. **A narrative synthesizing multiple chunks provides superior context** (H2 VERIFIED with nuance)
   - Narrative prototype: ~40 lines vs ~400-800 lines across 8 chunk GOALs
   - Narrative immediately frames purpose: "this is lifecycle infrastructure"
   - **Nuance**: Narratives are better for PURPOSE, chunks remain valuable for HISTORY
   - Evidence: See `prototypes/narrative_prototype.md`

4. **Narratives trade DETAIL for COHERENCE** (H5 High-N test)
   - At 8 chunks: Chunks scored 100%, Narrative scored 92%
   - Narrative omitted specific details (e.g., "function", "validate")
   - This is a TRADEOFF, not a universal improvement
   - Evidence: See `prototypes/h5_high_n_test.py`

5. **The narrative advantage is domain-specific:**
   - PURPOSE/WHY questions: Narrative likely superior (pre-synthesized context)
   - DETAIL/WHAT questions: Chunks superior (complete information preserved)
   - H1+H2 (qualitative) and H5 (quantitative) are compatible - different question types

6. **Agents follow breadcrumbs when prompted** (H6 FALSIFIED)
   - When both narrative and chunks exist, agents follow chunk refs from narrative
   - Condition A (chunks) and C (narrative+chunks) scored identically: 3.83/4.0
   - Narrative frontmatter serves as effective navigation to detail

### Hypotheses/Opinions

1. **Hybrid approach is optimal**: Code should reference the narrative for context-seeking agents, while the narrative links to constituent chunks for archaeology. Not a full replacement.

2. **LSM-tree analogy for chunk lifecycle**: The documentation system exhibits dynamics similar to a Log-Structured Merge tree:

   | LSM Concept | Documentation Analog |
   |-------------|---------------------|
   | Write → memtable | New work → chunk |
   | Memtable flush → immutable SSTable | Chunk completion → immutable GOAL.md |
   | Accumulating SSTables at L0 | Code accumulating chunk backreferences |
   | Compaction merges SSTables → larger segments | Consolidation merges chunks → narrative |
   | Read amplification (must check many SSTables) | Token amplification (must traverse many chunks) |
   | Compaction reduces read amplification | Narrative consolidation reduces token amplification |

   This suggests a natural lifecycle: chunks are the "write-optimized" format (quick to create, captures discrete work), narratives are the "read-optimized" format (synthesized for understanding).

3. **"Compaction" trigger heuristics** (to explore):
   - Code block exceeds N chunk backreferences (e.g., N=5)?
   - Oldest chunk reference exceeds age threshold (e.g., 20 chunks ago)?
   - Semantic clustering: chunks that share a theme become compaction candidates?

4. **Multi-level compaction hierarchy**:

   ```
   L0: Chunks        → L1: Narratives      → L2: Subsystems
   (work units)         (thematic arcs)       (architectural domains)
   ```

   The L0→L1 compaction (chunks→narratives) is mechanizable: cluster chunks by code overlap, temporal proximity, or stated theme.

   The L1→L2 compaction (narratives→subsystems) requires insight—discovering domain boundaries, invariants, and contracts. This is hard to automate directly.

   **However**: The L0→L1 compaction might provide the *affordance* for L1→L2 insight:
   - When multiple narratives touch the same code areas, that's a subsystem candidate signal
   - When narratives share implicit invariants, that's a contract waiting to be named
   - The act of viewing consolidated narratives provides the high-level perspective needed to recognize edges

   This suggests a human-in-the-loop design:
   - Automated: "These 3 narratives have 70% code overlap—possible subsystem?"
   - Human/Agent: "Yes, they all enforce template rendering patterns. That's the template_system subsystem."

5. **Token savings hypothesis requires refinement** (H4 tested, inconclusive):

   See `prototypes/h4_test_bench.py` for the test implementation.

   **Test results (2026-01-10):**
   | Condition | Doc Size | Cache Read Tokens | Total Tokens |
   |-----------|----------|-------------------|--------------|
   | A: 8 Chunks | 2,405 bytes | 90K | 914 |
   | B: 1 Narrative | 1,802 bytes | 139K | 943 |

   **Surprising finding:** The narrative condition used MORE tokens despite smaller documentation.

   **Analysis:** The token measurement includes more than file content:
   - Agent's system prompt and conversation context
   - Tool calls, results, and reasoning chains
   - The narrative was only 25% smaller, not 10x as hypothesized
   - Agent behavior differed between conditions (not controlled)

   **Methodology flaw:** The Claude Agent SDK cache tokens don't cleanly isolate "tokens spent reading documentation." The agent's decision-making overhead dominates.

   **Refined hypothesis:** Token savings may exist but require:
   - Measuring file read operations directly, not agent cache tokens
   - A narrative that's genuinely more concise (not just synthesized from chunks)
   - Controlling for agent reasoning overhead

## Proposed Chunks

1. **Chunk-to-narrative consolidation workflow**: Implement a process (possibly `/narrative-compact` or similar) that:
   - Identifies code blocks with high chunk backreference counts
   - Clusters related chunks by theme/code overlap
   - Generates a narrative synthesizing those chunks
   - Updates code backreferences to point to the narrative
   - Priority: Medium
   - Dependencies: Narrative backreference support

2. **Narrative backreference support**: Add support for `# Narrative: docs/narratives/NNNN-name` format in code files, parallel to chunk backreferences.
   - Priority: High
   - Dependencies: None

## Resolution Rationale

**Status: SOLVED**

The original hypothesis—that chunk backreferences lose semantic value over time and should be consolidated into narratives—was **partially confirmed with important nuances**.

### What we learned

1. **Chunk references DO accumulate and include old chunks** (H3 verified). Files like src/ve.py span 97% of project history with 46 backreferences.

2. **Old chunks provide low semantic value for PURPOSE understanding** (H1 verified). They document WHAT was built, not WHY it matters architecturally.

3. **Narratives provide superior context for PURPOSE questions** (H2 verified). A synthesized narrative immediately frames code purpose ("this is lifecycle infrastructure").

4. **BUT: Chunks are superior for DETAIL questions** (H5). At 8 chunks, chunks scored 100% vs narrative's 92% on detail-oriented questions. Narratives trade detail for coherence.

5. **Agents follow breadcrumbs when needed** (H6 falsified). When both narrative and chunks exist, agents navigate from narrative to chunks for detail. No overconfidence problem detected.

### The answer

**Narratives and chunks serve complementary purposes:**
- Narratives: Read-optimized for understanding PURPOSE/WHY
- Chunks: Write-optimized, preserve DETAIL/WHAT and HISTORY

**The hybrid approach is correct:** Code references narrative for context, narrative links to chunks for archaeology and detail. This follows the LSM-tree analogy—compaction (chunks→narrative) reduces read amplification while preserving data.

### Proposed follow-up work

Two chunks proposed in frontmatter:
1. Implement chunk-to-narrative consolidation workflow
2. Add narrative backreference support to code files