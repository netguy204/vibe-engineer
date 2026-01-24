# VIBE Engineering: Field Notes from Documentation-Driven Development

A blog series articulating the principles of VIBE engineering discovered through building this project.

## Series Overview

**Target Audience:** Engineering leaders helping organizations adopt agentic workflows, and senior developers skeptical of VibeCoding's tendency to produce slop.

**Core Thesis:** AI agents are very fast junior engineers. We already know how to manage junior engineers - through documentation, constraints, and review. VIBE engineering is that playbook, adapted.

**Transformation:** Fear to leverage. Readers will recognize this isn't as different or profound as it feels - organizations have struggled with reining in junior engineers since the beginning and have developed methodologies to accomplish this goal.

**Tone:** Practitioner's field notes. Honest about struggles, showing the evolution of discoveries over time.

**Structure:** Chronological, standalone articles. Each captures a "chunky realization" - a discrete insight with its own narrative arc (struggle → insight → resolution). The series grows as discoveries continue.

---

## Article 1: The Uncomfortable Truth About AI Coding

*The opening article establishing the core tension and thesis.*

### Outline

1. **The Seduction** - VibeCoding is intoxicating. You prompt, code appears, it mostly works. Ship it.

2. **The Hangover** - But you've been here before. It's the same slop you got from undertrained juniors, just faster. No one understands the codebase in 3 months. Changes break things in unexpected ways.

3. **The Reframe** - We already solved this problem. Every mature organization developed documentation practices, code review, architectural guardrails - not to slow people down, but to let them go fast safely. AI agents need the same thing.

4. **The Thesis** - VIBE engineering: treat AI as a very fast junior engineer. Invest in constraints, documentation, and workflow. The implementation becomes mechanical once the constraints are clear.

5. **What's Coming** - This series documents my journey discovering what that actually looks like in practice.

### Key Points
- The problem isn't AI, it's undisciplined AI
- Speed without direction produces slop faster
- We have decades of institutional knowledge about managing inexperienced contributors
- The goal is leverage, not replacement

### The Nuance: Superhuman Context, Missing Memory
The "fast junior" framing is useful but incomplete. Agents are *profoundly different* from juniors in two key ways:

**Superhuman context windows.** An agent can read 41 chunks, 3 narratives, 2 investigations, and synthesize a coherent story in seconds. No human holds that much in working memory.

**Missing episodic memory.** Unlike juniors who accumulate institutional knowledge over months and years, agents start fresh each session. They have no recollection of yesterday's decisions, last week's architectural discussions, or the reasoning behind existing code.

This means documentation artifacts serve two purposes:
1. **Guardrails** - Constrain the agent like you'd constrain a junior (scope, success criteria, review)
2. **Fuel** - Feed the agent's superhuman synthesis capability (structured artifacts it can traverse and integrate)

Documentation becomes the agent's *external memory* - compensating for what they lack while amplifying what they excel at.

### The Primacy of Toolmaking
Bryan Cantrill's talk ["Sharpening the Axe: The Primacy of Toolmaking"](https://www.youtube.com/watch?v=_GpBkplsGus) (P99 CONF 2022) provides the deeper frame:

> "Better tools yield better artifacts. But the tools themselves are entirely invisible to the user – and are often not even present in the end product."

Documentation artifacts *are* tools. The chunks, narratives, subsystems, and investigations - these are toolmaking for agent-driven development. They have immediate cost (time to write) but enable superhuman synthesis later.

Cantrill notes that toolmaking "feels like stealing time" because the payoff is delayed while the cost is immediate. This explains why documentation feels like overhead - until you see an agent traverse your entire project history and synthesize insights no human could hold in working memory.

The `ve` CLI itself embodies this: it's toolmaking that makes documentation-driven development sustainable. "The best time to develop a debugger is when debugging" - and the best time to develop documentation tooling is when you're drowning in undocumented agent output.

The VIBE engineering insight: create documentation that serves as both guardrails and fuel, building the tools that make this sustainable.

### Sources
- [Sharpening the Axe: The Primacy of Toolmaking - YouTube](https://www.youtube.com/watch?v=_GpBkplsGus) - Bryan Cantrill's full talk
- [P99 CONF Session Page](https://www.p99conf.io/session/sharpening-the-axe-the-primacy-of-toolmaking/) - Talk description and context
- [Slides on Speaker Deck](https://speakerdeck.com/bcantrill/sharpening-the-axe-the-primacy-of-toolmaking) - Presentation slides
- [The New Stack writeup](https://thenewstack.io/oxide-computings-bryan-cantrill-on-the-importance-of-toolmaking/) - Article summarizing key points

---

## Article 2: Chunks - The Atomic Unit of Agent Work

*Discovery: Work must be broken into discrete, validated units with explicit goals.*

### The Struggle
Early attempts at agent-driven development produced sprawling changes. No clear boundaries. Hard to review. Impossible to understand what was attempted vs achieved.

### The Insight
Agents need the same thing junior engineers need: a clearly scoped assignment with explicit success criteria. Enter the "chunk" - a discrete unit of work with a GOAL.md that captures what we're trying to accomplish before any code is written.

### The Resolution
- Chunks force articulation of intent before implementation
- Validation ensures chunks have required structure
- The chunk becomes the unit of review, discussion, and completion

### Source Material
- Chunks 0001-0003: Initial chunk creation, listing, project initialization
- Decision DEC-001: The core thesis that understanding constraints IS the problem

---

## Article 3: Referential Integrity is an Agent Problem

*Discovery: Code references drift; agents must maintain them.*

### The Struggle
Chunks reference code. Code changes. References become stale. We tried tracking line numbers (lines: 31-42), but they shift with every edit. Constant maintenance burden.

### The Insight
This isn't a tooling problem to solve with automation - it's an agent responsibility problem. The agent making changes must update the references. But we can make that easier by choosing reference formats that drift less.

### The Resolution
Symbolic references (`src/chunks.py#Chunks::create_chunk`) instead of line numbers. They survive refactoring. Hierarchical overlap detection becomes string operations. The maintenance burden drops dramatically.

### Source Material
- Chunk 0004: Reference overlap detection
- Chunk 0005: Code reference validation
- Chunk 0012: Symbolic reference format revolution

---

## Article 4: Write-Optimized vs Read-Optimized Documentation

*Discovery: Chunks are for capturing work; narratives are for understanding purpose.*

### The Struggle
After 10+ chunks, understanding "why" became difficult. Each chunk documented what it did, but the thematic connections were implicit. New agents (or humans) couldn't quickly grasp the larger initiative.

### The Insight
This is the LSM-tree pattern from databases. Chunks are write-optimized - fast to create, capture the moment. But you also need read-optimized views that synthesize meaning. A 40-line narrative explaining the arc is worth more than 800 lines of chunk details.

### The Resolution
Narratives as multi-chunk initiatives. They capture "advances trunk goal" and group related chunks. Chunks reference their parent narrative. Both formats serve different purposes.

### Source Material
- Chunk 0006: Narrative creation
- Narrative 0001: Cross-repo chunks (first narrative)
- Investigation 0002: The LSM-tree analogy for documentation

---

## Article 5: Subsystems Are Discovered, Not Designed

*Discovery: Cross-cutting patterns emerge organically and need a dedicated workflow.*

### The Struggle
Patterns started appearing across chunks - the template system, the workflow artifacts structure. But they weren't designed upfront. They emerged. And once emerged, we needed agents to use them consistently.

### The Insight
You can't design subsystems before you have code. They're recognized, not invented. But once recognized, they need formal documentation so future work respects their invariants. This requires a discovery-oriented workflow, not a design-oriented one.

### The Resolution
Subsystem lifecycle: DISCOVERING → DOCUMENTED → REFACTORING → STABLE. The DISCOVERING state is key - it signals "we're still figuring this out." The workflow guides collaborative exploration between human and agent.

### Source Material
- Narrative 0002: Subsystem documentation initiative
- Chunks 0014-0022: Subsystem discovery workflow
- Subsystem 0001: Template system (first discovered subsystem)
- Subsystem 0002: Workflow artifacts (meta - the system documenting itself)

---

## Article 6: Not All Exploration Produces Code

*Discovery: Investigations capture learning even when the answer is "do nothing."*

### The Struggle
Sometimes you need to understand something before committing to action. Is this a bug or expected behavior? Should we refactor this or leave it alone? These explorations were invisible - either producing chunks or disappearing.

### The Insight
Learning has value even when it doesn't produce code. "We investigated this and decided not to act" is a legitimate outcome that future agents should know about. Otherwise they'll re-investigate the same questions.

### The Resolution
Investigations as first-class artifacts. Status options include SOLVED, NOTED, and DEFERRED - not just "done" or "not done." Captures hypotheses, exploration log, and findings. Proposed chunks may be empty, and that's fine.

### Source Material
- Narrative 0003: Investigations initiative
- Chunks 0027-0030: Investigation workflow
- Investigation 0001: Artifact sequence numbering
- Investigation 0002: Chunk reference decay

---

## Article 7: Parallel Work Breaks Sequential Numbering

*Discovery: Sequence numbers create merge conflicts; causal ordering is merge-friendly.*

### The Struggle
Working in parallel (multiple engineers, git worktrees) created chunk numbering conflicts. Two people create chunk 0042 simultaneously. Merge conflict. Renumber. References break.

### The Insight
Sequence numbers encode an implicit total ordering that doesn't exist in parallel development. What actually matters is causal relationships - "this chunk was created knowing about that chunk." That's a partial order, not a total order.

### The Resolution
`created_after` field explicitly tracks causal dependencies. Topological sort produces display order. Numbers become cosmetic, not semantic. Merges just work because there's no implicit ordering to conflict.

### Source Material
- Investigation 0001: Artifact sequence numbering analysis
- Chunks 0037-0039: Causal ordering implementation
- The ArtifactIndex and Kahn's algorithm for DAG sorting

---

## Article 8: Status Lifecycles Signal Intent

*Discovery: Different states communicate what's appropriate to do next.*

### The Struggle
Is this subsystem ready to use? Can I modify this chunk? Is this investigation still active? Without explicit status, agents had to infer intent from content. Often incorrectly.

### The Insight
Status isn't just tracking - it's communication. DISCOVERING says "help figure this out." DOCUMENTED says "known issues, not fixing now." REFACTORING says "actively consolidating, you may expand scope." Each state authorizes different actions.

### The Resolution
Explicit status enums for each artifact type with defined transitions. The status becomes part of the contract between humans and agents about what kind of work is appropriate.

### Source Material
- Chunk 0019: Subsystem status transitions
- SubsystemStatus: DISCOVERING → DOCUMENTED → REFACTORING → STABLE → DEPRECATED
- ChunkStatus, NarrativeStatus, InvestigationStatus patterns

---

## Article 9: Idempotency Enables Incremental Adoption

*Discovery: Tools that are safe to re-run let teams adopt gradually.*

### The Struggle
How do you introduce this workflow to an existing project? "Run this initialization" is scary if it might overwrite things. Teams resist big-bang adoption.

### The Insight
Every tool should be safe to run twice. If the artifact exists, don't overwrite it. This isn't just defensive programming - it's an adoption strategy. Teams can initialize, try one chunk, and expand gradually.

### The Resolution
Idempotency as a core principle (Decision DEC-003). `ve init` on an existing project adds what's missing without touching what's there. Low-risk experimentation enables organic adoption.

### Source Material
- Decision DEC-003: Idempotency principle
- Chunk 0003: Project initialization with existing file detection

---

## Article 10: The Workflow Itself Evolves

*Discovery: The system for managing work is subject to the same iterative improvement.*

### The Struggle
The initial workflow was just chunks. Then we needed narratives. Then subsystems. Then investigations. Each addition felt like scope creep. When does it end?

### The Insight
This IS the workflow. The documentation system evolves through the same feedback loops as the code. Chunks document the evolution. Subsystems capture the emergent patterns. The workflow eating its own tail isn't a bug - it's the point.

### The Resolution
Embrace meta-evolution. Subsystem 0002 (workflow_artifacts) documents the workflow itself. Investigation 0002 questions whether chunks accumulate too much. The system remains open to its own improvement.

### Source Material
- Subsystem 0002: Workflow artifacts (the system documenting itself)
- Investigation 0002: Chunk reference decay (questioning the system)
- The entire chronological evolution from chunks-only to the current multi-artifact system

---

## Future Articles (As Discoveries Continue)

Topics that may emerge as the journey continues:

- **Agent collaboration patterns** - What makes a good agent instruction vs a bad one?
- **Review workflows for agent output** - How do you efficiently review AI-generated changes?
- **Cross-repository coordination** - Managing work that spans multiple codebases
- **Measuring documentation health** - How do you know if your docs are actually helping?
- **The compaction problem** - When and how to consolidate chunks into narratives
- **Teaching vs constraining** - Documentation that helps agents learn vs documentation that restricts them

---

## Ideas Cut From Article 1

These ideas were developed during Article 1 drafting but cut for flow. They may fit better in later articles.

### Detailed Onboarding Principles (The Six Bullets)
Cut for pacing—condensed to a single paragraph. The detailed version:

- Onboarding is progressive discovery: All you need to know right now is what's necessary to find or do the next thing. Being told more than that is overwhelming.
- Onboarding captures intent, not just mechanics: Knowing *how* to do something isn't enough. "We use PostgreSQL" is mechanics. "Because we need ACID transactions" is intent. "We learned this migrating off distributed Mongo when eventual consistency broke us" is wisdom. Juniors can ask for all three. Agents only get what you wrote down.
- Onboarding is a team sport: If only the team lead can onboard newcomers, then bringing in newcomers destroys the capacity of the team by saturating its leadership.
- Onboarding is eventually carried by documentation: The junior has more free time than anyone else on the team. If they can apply that time to self-directed learning then onboarding scales. Documentation also survives the onboarder. Good documentation is institutional memory that doesn't walk out the door.
- Onboarding has guardrails: Code review, PR templates, linters. The newcomer can't easily make catastrophic mistakes while they're still learning. The constraints protect the codebase *and* the newcomer.
- Onboarding is testable: You know it worked when the newcomer's output respects the patterns without hand-holding. If you're still correcting the same mistakes, then you've discovered an area for improving your onboarding.

### Process Improvement / Measurability
> "And because an onboarding process is measurable, it's improvable."

The insight: onboarding can be iteratively improved because you can observe whether it's working (testable bullet). The author has discovered rapid iteration and process improvement leverage while building the toolset. Could fit an article about the practice of building/refining onboarding systems.

### The "Layered" Onboarding Principle
> First day, first week, first month. You don't dump everything at once. The newcomer earns deeper context as they demonstrate they can handle shallower context.

Cut because it doesn't translate well to agents (no continuity between sessions). But the underlying principle—documentation with layers of depth—might fit an article about documentation architecture.

### Institutional Agility (Fresh Onboarding as Advantage)
> There's magic in every agent being on-boarded fresh in every session. It means that institutional inertia can shift very quickly which gives us a lot of leverage. We don't need to spend months retraining our legacy humans. A clarification to a bit of subsystem documentation means that every agent launched later understands your refined vision for that subsystem and can work to nudge reality in that direction.

The flip side of the amnesia problem: agents don't carry baggage. Institutional change can happen instantly through documentation updates. Could fit an article about organizational change or documentation as leverage.

### Superhuman Synthesis
> Agents aren't just really fast juniors... they have an absolutely superhuman working memory and ability to synthesize information. Once you're onboarding your agents appropriately, you'll find them to be a new source of leverage for thinking about and shaping your systems in larger ways. A faster, well-grounded answer to "What would it mean if we changed X?" can lead to brilliant insight and much better designs. Not only are you increasing the impact of your judgement, you're gaining tools for arriving at better judgement.

The payoff of good onboarding: agents become thinking partners, not just task executors. Could fit an article about advanced agent collaboration or "what becomes possible after you solve onboarding."

---

## Appendix: Source Material Map

| Article | Primary Chunks | Narratives | Investigations | Subsystems |
|---------|---------------|------------|----------------|------------|
| 1 | - | - | - | - |
| 2 | 0001-0003 | - | - | - |
| 3 | 0004, 0005, 0012 | - | - | - |
| 4 | 0006 | 0001 | 0002 | - |
| 5 | 0014-0022 | 0002 | - | 0001, 0002 |
| 6 | 0027-0030 | 0003 | 0001, 0002 | - |
| 7 | 0037-0039 | - | 0001 | - |
| 8 | 0019 | - | - | - |
| 9 | 0003 | - | - | - |
| 10 | - | - | 0002 | 0002 |
