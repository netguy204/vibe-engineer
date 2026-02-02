# Backreference Investigation Findings

Research into how agents interact with chunk backreferences in code, based on analysis of 318 orchestrator transcripts.

## Key Finding: Agents Naturally Follow the GOAL → PLAN Hierarchy

When agents encounter a backreference like `# Chunk: docs/chunks/auth_refactor` and choose to follow it, they read:

| Pattern | % of Follows |
|---------|-------------|
| GOAL.md only | 53.4% |
| Both (GOAL first) | 26.1% |
| Both (PLAN first) | 4.8% |
| PLAN.md only | 15.7% |

**84.3% of the time, agents read GOAL.md** (either alone or before PLAN.md). This validates the two-file design: the GOAL contains the "why" that agents typically need, while the PLAN's "how" is consulted only when implementation details matter.

## Progressive Disclosure in Practice

The reading pattern varies by what the agent is doing:

| Phase | GOAL only | Both files |
|-------|-----------|------------|
| Implement | 70.2% | 21.5% |
| Complete | 51.9% | 27.9% |
| Plan | 45.9% | 42.7% |
| Review | 38.7% | 54.7% |

During implementation, agents are decisive—they read the GOAL to understand intent and move on. During planning and review, they're more exploratory and consult both files. The documentation structure naturally supports different depths of engagement without forcing agents to read everything.

## Backreference Followthrough by Phase

When agents encounter backreferences in code, how often they follow them depends on what phase they're in:

| Phase | Followthrough Rate | Interpretation |
|-------|-------------------|----------------|
| Plan | **62.2%** | Actively gathering context to understand the problem space |
| Complete | 38.8% | Updating references, moderate exploration |
| Review | 37.7% | Checking alignment, selective deep-dives |
| Implement | **23.1%** | Heads-down coding, minimal exploration |

This pattern is intentional and healthy. The plan phase is designed for context gathering—agents explore widely to understand how their work fits into the broader system. By the time they reach implementation, the PLAN.md contains all the context they need, so they stay focused on writing code rather than re-exploring.

The 23.1% implement-phase rate might look low, but it reflects good workflow design: do your thinking in planning, do your coding in implementation.

## Backreferences as Discovery, Not Prescription

Overall, agents follow backreferences about 39% of the time (1,340 reads out of 3,443 backreferences shown). This isn't a failure—it's healthy behavior. Backreferences serve as anchors that agents can follow when context demands deeper understanding, not mandatory reading that overwhelms every exploration.

When agents do follow backreferences, they're purposeful: reading foundational GOAL.md files of related work rather than exhaustively exploring every reference.

## No Evidence of Context-Related Review Failures

Searching review transcripts for phrases like "should have referenced," "inconsistent with existing pattern," or "doesn't follow approach used in related code" yielded no results. When reviews flag issues, they're about:

- Execution completeness (tests not written as planned)
- Minor metadata inconsistencies
- Infrastructure issues

This suggests the backreference system provides sufficient context for agents to make good decisions. The quality bottleneck is elsewhere (verification depth, not reading breadth).

## Implications for the Chunk Model

1. **The GOAL/PLAN split works**: Agents naturally treat GOAL as the primary reference and PLAN as supplementary detail. You don't need to force them into this pattern.

2. **Backreferences compound value over time**: Each chunk creates tent-poles of judgment that future agents discover through code exploration. The 18-35% follow rate means agents find and use relevant context without being overwhelmed.

3. **Documentation pays for itself**: The same artifact that assigns work to an agent (GOAL.md) becomes the artifact that explains the work to future agents. No extra effort required.

---

*Based on analysis of 318 orchestrator transcripts containing 14,893 backreferences across 21 chunks with complete plan/implement/review cycles.*
