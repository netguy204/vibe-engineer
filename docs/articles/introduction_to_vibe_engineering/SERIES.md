# Introduction to VIBE Engineering

A blog series articulating the principles of VIBE engineering discovered through building this project.

## Series Metadata

| Field | Value |
|-------|-------|
| Target Audience | Engineering leaders helping organizations adopt agentic workflows, and senior developers skeptical of VibeCoding's tendency to produce slop |
| Core Thesis | AI agents are very fast junior engineers. We already know how to manage junior engineers - through documentation, constraints, and review. VIBE engineering is that playbook, adapted. |
| Transformation | Fear to leverage. Readers will recognize this isn't as different or profound as it feels - organizations have struggled with reining in junior engineers since the beginning and have developed methodologies to accomplish this goal. |
| Tone | Practitioner's field notes. Honest about struggles, showing the evolution of discoveries over time. |
| Structure | Chronological, standalone articles. Each captures a "chunky realization" - a discrete insight with its own narrative arc (struggle → insight → resolution). The series grows as discoveries continue. |

---

## Themes Ledger

Framings discovered during writing that should thread through subsequent articles.

| Theme | Originated | Echo Notes |
|-------|------------|------------|
| Amnesiac surgeon | Article 1 | Session boundaries, context management, why memory matters |
| Onboarding exercise (multiple times/day) | Article 1 | Central frame for entire series; every artifact type is onboarding infrastructure |
| Judgment vs typing | Article 1 | Review workflows, architectural decisions, what humans uniquely contribute |
| Compounding judgment | Article 1 | Documentation accumulation, narrative consolidation, institutional leverage |
| Discoverable documentation | Article 1 | Chunks, narratives, subsystems—architecture that can be explored from any starting point |
| Externalized learning | Article 5 | The struggle still happens; subsystems are where tacit understanding becomes concrete and shareable |

---

## Article Sequence

### Article 1: The Uncomfortable Truth About AI Coding

*Status: PUBLISHED*

*The opening article establishing the core tension and thesis.*

#### Original Outline

1. **The Seduction** - VibeCoding is intoxicating. You prompt, code appears, it mostly works. Ship it.

2. **The Hangover** - But you've been here before. It's the same slop you got from undertrained juniors, just faster. No one understands the codebase in 3 months. Changes break things in unexpected ways.

3. **The Reframe** - We already solved this problem. Every mature organization developed documentation practices, code review, architectural guardrails - not to slow people down, but to let them go fast safely. AI agents need the same thing.

4. **The Thesis** - VIBE engineering: treat AI as a very fast junior engineer. Invest in constraints, documentation, and workflow. The implementation becomes mechanical once the constraints are clear.

5. **What's Coming** - This series documents my journey discovering what that actually looks like in practice.

#### Key Points
- The problem isn't AI, it's undisciplined AI
- Speed without direction produces slop faster
- We have decades of institutional knowledge about managing inexperienced contributors
- The goal is leverage, not replacement

---

### Article 2: Chunks - The Assignment That Becomes the Record

*Status: PLANNED*

*Discovery: The chunk is both the assignment and the documentation—same artifact, no extra cost.*

#### The Struggle
Plan mode and Cursor already give you scoped assignments. But when the session ends, the reasoning evaporates. The next agent sees the code but not *why*. You explain the same context again. And again.

#### The Insight
The chunk is both the assignment *and* the medical record—the same artifact serves both purposes. Writing the GOAL.md to assign the work *is* writing the documentation. No extra cost.

#### The Resolution
Every chunk you write is a page in your onboarding wiki that you never have to explain again. Future agents discover it through code backreferences. Your one-time effort compounds into institutional memory.

#### Key Tension Resolved
"Documentation feels like overhead" → "The assignment *is* the documentation."

#### Theme Connections
- **Amnesiac surgeon** — the chunk externalizes memory that would otherwise be lost
- **Discoverable documentation** — code links back to chunks; agents explore reasoning from anywhere
- **Compounding judgment** — chunks accumulate into a wiki that gets smarter over time

#### Source Material
- Chunks 0001-0003: Initial chunk creation, listing, project initialization
- Decision DEC-001: The core thesis that understanding constraints IS the problem

---

### Article 3: Making the Wiki Reachable

*Status: PLANNED*

*Discovery: The chunk only compounds if agents can find it. Backreferences must survive code evolution.*

#### The Struggle
The chunk only compounds if agents can find it. Backreferences rot. Line numbers shift with every edit. The medical record exists but the chart is unreadable. Your wiki becomes an unreachable island.

#### The Insight
This isn't a tooling problem—it's a format problem. Symbolic references (`file#Class::method`) survive refactoring. And it's a responsibility problem: the agent that changes code must update the references pointing to it.

#### The Resolution
Backreferences become reliable navigation. Agents trace code to reasoning. The wiki stays reachable. Your one-time documentation effort actually compounds because it can be discovered.

#### Theme Connections
- **Discoverable documentation** — this article is about making discoverability *work*
- **Compounding judgment** — references that rot break the compound interest

#### Source Material
- Chunk 0004: Reference overlap detection
- Chunk 0005: Code reference validation
- Chunk 0012: Symbolic reference format revolution

---

### Article 4: Planning When You're Not Ready for Chunks

*Status: PLANNED*

*Discovery: "Too big for a chunk" comes in two flavors—known destination (narrative) vs known direction (investigation).*

#### The Struggle
Some work is too big for a single chunk. But "too big" comes in two flavors: sometimes you know the destination but not the steps (map without legs), and sometimes you only know the direction (compass without map).

#### The Insight
**Narratives** are for when you have the map. The big idea is in your head—you know what needs to happen, just not how to break it up. The narrative captures the destination, then guides decomposition into sequenced chunks.

**Investigations** are for when you only have a compass. You know the answer is "over there" but not exactly where. The investigation frames your thinking, designs experiments, and builds the map that eventually produces chunks.

#### The Resolution
Both artifacts answer "what do I do before I'm ready for chunks?" Narratives decompose known work. Investigations explore unknown territory. Both can produce chunks—or not. The investigation that concludes "do nothing" is still valuable; the map got built.

#### Key Tension Resolved
"I know this is important but I don't know how to start" → "Use the artifact that matches your certainty level."

#### Theme Connections
- **Judgment vs typing** — both artifacts are where you exercise judgment about direction before agents execute
- **Externalized learning** — investigations make the exploration explicit; the map-building becomes an artifact
- **Compounding judgment** — even "do nothing" investigations prevent future agents from re-exploring

#### Source Material
- Chunk 0006: Narrative creation
- Narrative 0001: Cross-repo chunks (first narrative)
- Chunks 0027-0030: Investigation workflow
- Investigation 0001: Artifact sequence numbering
- Investigation 0002: Chunk reference decay

---

### Article 5: Subsystems Are Discovered, Not Designed

*Status: PLANNED*

*Discovery: The understanding that used to emerge from struggling with code still happens—it just gets externalized and named.*

#### The Struggle
Graybeards know: writing code is an act of thought. The struggle with implementation changes your understanding of the problem. Creatives rightfully fear what happens when agents take over the writing. Do we lose the opportunity to do that thinking?

Meanwhile, patterns started appearing across chunks. The same code kept getting touched by different work. Multiple backreferences accumulated—a signal that individual chunks were orbiting something they couldn't name.

#### The Insight
You can't design subsystems before you have code. They're *recognized*, not invented. Multiple chunk backreferences on the same code is the signal: understanding is ready to consolidate.

And here's the answer to the fear: the learning doesn't disappear when agents write the code—it gets externalized and named. The struggling still happens (just faster). The subsystem is where you capture what you learned. Like memory consolidation in psychology—details compress into patterns that persist.

#### The Resolution
Subsystem lifecycle: DISCOVERING → DOCUMENTED → REFACTORING → STABLE. The subsystem absorbs the understanding from the chunks that pointed at it. The pattern gets a name. Future agents learn the concept, not the history. Your tacit learning becomes institutional memory.

#### Key Tension Resolved
"If I'm not struggling with the code, am I still learning?" → "The learning still happens; now it becomes an artifact that compounds."

#### Theme Connections
- **Judgment vs typing** — the value was never the typing, it was the understanding that emerged
- **Compounding judgment** — externalized learning compounds; tacit learning fades
- **Consolidation signals** — chunk accumulation reveals patterns ready to name

#### Source Material
- Narrative 0002: Subsystem documentation initiative
- Chunks 0014-0022: Subsystem discovery workflow
- Subsystem 0001: Template system (first discovered subsystem)
- Subsystem 0002: Workflow artifacts (meta - the system documenting itself)

---

### Article 6: The Value of Deciding Not to Act (Yet)

*Status: PLANNED*

*A coda to Article 4: Investigations as trusted external storage for ideas that aren't ready.*

#### The Struggle
Some ideas burn. They demand attention but resist resolution. You can't stop thinking about them, but you can't figure out what to do about them either. They consume cognitive cycles without producing progress.

#### The Insight
Rich Hickey's "Hammock Driven Development" nails this: your background mind does the real synthesis, but you have to load up the problem first and then step away. The investigation is the artifact that lets you do this—externalize the burning concept, get it out of your head into a form you can see and interact with, then put it down. Your subconscious keeps working. Weeks later, you pick it back up and discover you understand it better.

#### The Resolution
"Do nothing now" isn't failure—it's a legitimate status. DEFERRED means "this is real, it's captured, and it's not time yet." The investigation holds space for ideas that aren't ready, so your brain doesn't have to. You've loaded the problem; now you can step away without losing the thread.

#### Key Tension Resolved
"I can't stop thinking about this but I don't know what to do" → "Externalize it, trust the artifact, let your background mind work."

#### Theme Connections
- **Externalized learning** — even uncommitted ideas become artifacts you can return to
- **Compounding judgment** — deferred investigations prevent future re-exploration of the same question
- **Judgment vs typing** — knowing when *not* to act is judgment too

#### Source Material
- Rich Hickey's "Hammock Driven Development" talk
- Investigation status: DEFERRED as first-class outcome

---

### Article 7: The Chaos Spectrum (What I Learned from Gas Town)

*Status: PLANNED*

*Discovery: Guardrails enable throughput. Parallel agents work reliably when constraints are clear.*

#### The Struggle
The throughput question: Can we run many agents in parallel? Steve Yegge's [Gas Town](https://github.com/steveyegge/gastown) says yes—20-30 agents at once. But [early reports](https://www.dolthub.com/blog/2026-01-15-a-day-in-gas-town/) show chaos: failing PRs merged automatically, repos force-reset, $100/hour burn rate. Quantity without quality.

#### The Shared Compass
Yegge and I are solving the same problem: agents forget. His "beads" ≈ my chunks. Both persist work state in git. Both recognized that memory is the core constraint. We started with the same compass.

#### The Fork
Yegge bet on quantity: *"It's okay to lose things, rewrite whole subsystems, whatever."* I bet on consolidation: chunks compound into subsystems, status signals intent, judgment stays central. He embraced chaos; I built guardrails.

#### The Synthesis
Here's what I learned: guardrails *enable* throughput. The orchestrator runs parallel agents reliably *because* the constraints are clear. Unobserved work produces reliable outcomes when chunks have explicit goals, success criteria, and status. The infrastructure isn't overhead—it's what makes scaling actually work.

#### The Humility
Yegge might be seeing the future. The discipline required today may become unnecessary as models improve. But right now, the reports suggest guardrails aren't optional—they're the difference between parallel productivity and parallel chaos.

#### Key Tension Resolved
"Do I need guardrails or throughput?" → "Guardrails enable throughput."

#### Theme Connections
- **Judgment vs typing** — the core bet: is the constraint throughput or judgment?
- **Compounding judgment** — guardrails let parallel work compound rather than conflict
- **Onboarding exercise** — the orchestrator works because each agent gets properly onboarded via chunks

#### Source Material
- Steve Yegge's Gas Town and Beads
- Tim Sehn's "A Day in Gas Town" experience report
- The ve orchestrator (`ve orch`)

---

### Article 8: Parallel Work Breaks Sequential Numbering

*Status: PLANNED*

*Discovery: Sequence numbers create merge conflicts; causal ordering is merge-friendly.*

#### The Struggle
Working in parallel (multiple engineers, git worktrees) created chunk numbering conflicts. Two people create chunk 0042 simultaneously. Merge conflict. Renumber. References break.

#### The Insight
Sequence numbers encode an implicit total ordering that doesn't exist in parallel development. What actually matters is causal relationships - "this chunk was created knowing about that chunk." That's a partial order, not a total order.

#### The Resolution
`created_after` field explicitly tracks causal dependencies. Topological sort produces display order. Numbers become cosmetic, not semantic. Merges just work because there's no implicit ordering to conflict.

#### Source Material
- Investigation 0001: Artifact sequence numbering analysis
- Chunks 0037-0039: Causal ordering implementation
- The ArtifactIndex and Kahn's algorithm for DAG sorting

---

### Article 9: Status Lifecycles Signal Intent

*Status: PLANNED*

*Discovery: Different states communicate what's appropriate to do next.*

#### The Struggle
Is this subsystem ready to use? Can I modify this chunk? Is this investigation still active? Without explicit status, agents had to infer intent from content. Often incorrectly.

#### The Insight
Status isn't just tracking - it's communication. DISCOVERING says "help figure this out." DOCUMENTED says "known issues, not fixing now." REFACTORING says "actively consolidating, you may expand scope." Each state authorizes different actions.

#### The Resolution
Explicit status enums for each artifact type with defined transitions. The status becomes part of the contract between humans and agents about what kind of work is appropriate.

#### Source Material
- Chunk 0019: Subsystem status transitions
- SubsystemStatus: DISCOVERING → DOCUMENTED → REFACTORING → STABLE → DEPRECATED
- ChunkStatus, NarrativeStatus, InvestigationStatus patterns

---

### Article 10: Idempotency Enables Incremental Adoption

*Status: PLANNED*

*Discovery: Tools that are safe to re-run let teams adopt gradually.*

#### The Struggle
How do you introduce this workflow to an existing project? "Run this initialization" is scary if it might overwrite things. Teams resist big-bang adoption.

#### The Insight
Every tool should be safe to run twice. If the artifact exists, don't overwrite it. This isn't just defensive programming - it's an adoption strategy. Teams can initialize, try one chunk, and expand gradually.

#### The Resolution
Idempotency as a core principle (Decision DEC-003). `ve init` on an existing project adds what's missing without touching what's there. Low-risk experimentation enables organic adoption.

#### Source Material
- Decision DEC-003: Idempotency principle
- Chunk 0003: Project initialization with existing file detection

---

### Article 11: The Workflow Itself Evolves

*Status: PLANNED*

*Discovery: The system for managing work is subject to the same iterative improvement.*

#### The Struggle
The initial workflow was just chunks. Then we needed narratives. Then subsystems. Then investigations. Each addition felt like scope creep. When does it end?

#### The Insight
This IS the workflow. The documentation system evolves through the same feedback loops as the code. Chunks document the evolution. Subsystems capture the emergent patterns. The workflow eating its own tail isn't a bug - it's the point.

#### The Resolution
Embrace meta-evolution. Subsystem 0002 (workflow_artifacts) documents the workflow itself. Investigation 0002 questions whether chunks accumulate too much. The system remains open to its own improvement.

#### Source Material
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

## Parking Lot

Ideas cut from articles that might fit elsewhere.

### From Article 1

#### Detailed Onboarding Principles (The Six Bullets)
Cut for pacing—condensed to a single paragraph. The detailed version:

- Onboarding is progressive discovery: All you need to know right now is what's necessary to find or do the next thing. Being told more than that is overwhelming.
- Onboarding captures intent, not just mechanics: Knowing *how* to do something isn't enough. "We use PostgreSQL" is mechanics. "Because we need ACID transactions" is intent. "We learned this migrating off distributed Mongo when eventual consistency broke us" is wisdom. Juniors can ask for all three. Agents only get what you wrote down.
- Onboarding is a team sport: If only the team lead can onboard newcomers, then bringing in newcomers destroys the capacity of the team by saturating its leadership.
- Onboarding is eventually carried by documentation: The junior has more free time than anyone else on the team. If they can apply that time to self-directed learning then onboarding scales. Documentation also survives the onboarder. Good documentation is institutional memory that doesn't walk out the door.
- Onboarding has guardrails: Code review, PR templates, linters. The newcomer can't easily make catastrophic mistakes while they're still learning. The constraints protect the codebase *and* the newcomer.
- Onboarding is testable: You know it worked when the newcomer's output respects the patterns without hand-holding. If you're still correcting the same mistakes, then you've discovered an area for improving your onboarding.

#### Process Improvement / Measurability
> "And because an onboarding process is measurable, it's improvable."

The insight: onboarding can be iteratively improved because you can observe whether it's working (testable bullet). The author has discovered rapid iteration and process improvement leverage while building the toolset. Could fit an article about the practice of building/refining onboarding systems.

#### The "Layered" Onboarding Principle
> First day, first week, first month. You don't dump everything at once. The newcomer earns deeper context as they demonstrate they can handle shallower context.

Cut because it doesn't translate well to agents (no continuity between sessions). But the underlying principle—documentation with layers of depth—might fit an article about documentation architecture.

#### Institutional Agility (Fresh Onboarding as Advantage)
> There's magic in every agent being on-boarded fresh in every session. It means that institutional inertia can shift very quickly which gives us a lot of leverage. We don't need to spend months retraining our legacy humans. A clarification to a bit of subsystem documentation means that every agent launched later understands your refined vision for that subsystem and can work to nudge reality in that direction.

The flip side of the amnesia problem: agents don't carry baggage. Institutional change can happen instantly through documentation updates. Could fit an article about organizational change or documentation as leverage.

#### Superhuman Synthesis
> Agents aren't just really fast juniors... they have an absolutely superhuman working memory and ability to synthesize information. Once you're onboarding your agents appropriately, you'll find them to be a new source of leverage for thinking about and shaping your systems in larger ways. A faster, well-grounded answer to "What would it mean if we changed X?" can lead to brilliant insight and much better designs. Not only are you increasing the impact of your judgement, you're gaining tools for arriving at better judgement.

The payoff of good onboarding: agents become thinking partners, not just task executors. Could fit an article about advanced agent collaboration or "what becomes possible after you solve onboarding."

---

## Source Material Map

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
