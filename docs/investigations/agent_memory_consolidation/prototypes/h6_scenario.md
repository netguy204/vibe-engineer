# H6 Experiment: Self-Reporting Core Memory Usage

## Design

A sub-agent is given the 11 core memories and a startup prompt instructing it to
run a touch command whenever it applies a core memory. It then receives a sequence
of 10 operator messages forming a realistic workday. The agent role-plays its
responses (it cannot execute real work, so it describes what it would do).

We measure:
1. Does it touch memories at all?
2. Are touches accurate? (compared to ground truth)
3. Over-reporting? (touching memories not relevant to the action)
4. Under-reporting? (missing obvious applications)
5. Does metacognitive overhead degrade response quality?

## Ground Truth

Expected core memory triggers per scenario message:

| Msg | Scenario | Expected Memories |
|-----|----------|-------------------|
| 1 | PR merged notification | CM4 (rebase after merge), CM3 (verify branch/PR state) |
| 2 | Start a background watch | CM5 (kill old processes first) |
| 3 | Data mismatch reported | CM1 (verify both sides of join), CM7 (duplicate rows = missing discriminator) |
| 4 | Agent proposes a code fix | CM2 (verify code path is reachable), CM6 (update docs before committing) |
| 5 | Agent declares fix complete | CM10 (run integration tests first), CM1 (verify both sides) |
| 6 | Operator says "remember this for future" | CM6 (update documentation) |
| 7 | Send a request to another agent | CM8 (correct channel ordering - watch before send) |
| 8 | Operator gives minor feedback on approach | CM9 (standing permission / scope change vs small fix) |
| 9 | Create a new PR for the fix | CM3 (never push to main, verify branch) |
| 10 | Semantic change with small diff | CM11 (use chunks for semantic changes) |

Total expected touches: ~16 across 10 messages (some messages trigger 2 memories).
