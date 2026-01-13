# Next Steps

## Immediate Options

### 1. Propose Implementation Chunks
The prototype is functional. Ready to create chunks for:

- **`reviewer_baseline_skill`**: Convert `prototypes/chunk-review.md` into a real skill at `.claude/skills/chunk-review.md`
- **`reviewer_registry`**: Create `docs/reviewers/` directory structure with baseline reviewer
- **`orchestrator_review_gate`**: Integrate final review as mandatory step before chunk-complete in orchestrator workflow
- **`reviewer_decision_log`**: Implement decision logging and operator feedback mechanism (good/bad marking)

### 2. Test Edge Cases
Both tested chunks got APPROVE. To validate FEEDBACK/ESCALATE paths:

- Find a chunk with known issues (incomplete implementation, missing tests)
- Create a mock chunk with deliberate misalignments
- Test loop detection by simulating multiple review iterations

### 3. Explore Remaining Hypotheses

**H2: Goal-to-implementation verification via tests**
- Pick completed chunks and compare GOAL.md success criteria against test assertions
- Determine if gaps are detectable programmatically

**H3: Subsystem invariants as tractable taste**
- Review existing subsystem OVERVIEW.md files for invariants
- Prototype a reviewer that checks subsystem conformity

**H4: Taste as reviewable heuristics**
- Interview: What did great engineers catch that others missed?
- Attempt to enumerate those catches as rules

## Recommended Path

**If you want to start using this soon:**
1. Create `reviewer_baseline_skill` chunk
2. Test it manually on a few chunks before orchestrator integration
3. Iterate on the prompt based on real usage

**If you want to validate the design further:**
1. Test FEEDBACK/ESCALATE paths
2. Explore H3 (subsystem invariants) since that's most concrete
3. Then propose chunks

## Open Questions for Future Sessions

1. Where should reviewer decision logs live? (`docs/reviewers/{name}/DECISION_LOG.md` vs centralized)
2. How does trust level persist across sessions? (METADATA.yaml seems right)
3. When should a reviewer be forked into domain-specific versions?
4. Should review happen incrementally during implementation or only at the end? (Prototype supports both)
5. How do we handle reviewer/implementer disagreements that persist?
