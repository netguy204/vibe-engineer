---
status: COMPLETED
advances_trunk_goal: "Required Properties: Following the workflow must maintain the health of documents over time and should not grow more difficult over time."
proposed_chunks:
  - prompt: "Update orchestrator injection logic to distinguish depends_on: [] (explicit no-deps, bypass oracle) from depends_on: null/omitted (unknown deps, consult oracle)"
    chunk_directory: explicit_deps_null_inject
    depends_on: []
  - prompt: "Update chunk GOAL.md template documentation to explain null vs empty semantics for depends_on field"
    chunk_directory: explicit_deps_goal_docs
    depends_on: [0]
  - prompt: "Update narrative and investigation templates to document the null vs empty depends_on semantics in proposed_chunks schema"
    chunk_directory: explicit_deps_template_docs
    depends_on: [0]
  - prompt: "Update command prompts (chunk-create, narrative-create, etc.) to teach agents the depends_on null vs empty distinction"
    chunk_directory: explicit_deps_command_prompts
    depends_on: [1, 2]
friction_entries: [F015]
created_after: ["explicit_chunk_deps"]
---

## Advances Trunk Goal

**Required Properties**: "Following the workflow must maintain the health of documents over time and should not grow more difficult over time."

The `explicit_chunk_deps` narrative introduced the `depends_on` field to allow agents to declare dependencies explicitly and bypass the oracle's heuristic conflict detection. However, the semantics of an empty list vs null/omitted were not clearly distinguished. This creates friction: agents cannot declare "these chunks are independent, trust me" without adding fake dependencies. Clarifying these semantics completes the explicit dependency story.

## Driving Ambition

The original `explicit_chunk_deps` narrative established that `depends_on` can bypass the oracle, but the current implementation treats `depends_on: []` the same as omitting the field—both trigger oracle consultation. This leaves a semantic gap:

- **What agents want to express**: "I've analyzed these chunks and they have no dependencies on each other. Don't consult the oracle; trust my declaration."
- **What they can currently express**: Either explicit dependencies (which works) or "I don't know" (which triggers oracle).

We need to distinguish two cases:

| `depends_on` value | Meaning | Oracle behavior |
|-------------------|---------|-----------------|
| `null` or omitted | "I don't know my dependencies" | Consult oracle |
| `[]` (empty list) | "I explicitly have no dependencies" | Bypass oracle |
| `[chunk_a, chunk_b]` | "I depend on these chunks" | Bypass oracle |

This is a refinement to `explicit_chunk_deps`, not a new concept. The chunks here update the implementation and documentation to support this distinction.

## Chunks

1. **Update orchestrator injection logic** - Modify the injection path to set `explicit_deps=True` when `depends_on` is an empty list `[]`, not just when it contains values. Null/omitted means unknown (oracle consulted); empty list means "explicitly none" (oracle bypassed).

2. **Update chunk GOAL.md template** - Revise the `depends_on` field documentation to explain the null vs empty semantics clearly. (depends on #1)

3. **Update narrative/investigation templates** - Add the same clarification to the `proposed_chunks` schema documentation in narrative and investigation OVERVIEW.md templates. (depends on #1)

4. **Update command prompts** - Revise `/chunk-create`, `/narrative-create`, and related command prompts to teach agents when to use `[]` vs omit the field. (depends on #2, #3)

## Completion Criteria

When complete:

1. An agent creating chunks can declare `depends_on: []` to express "no dependencies, bypass oracle"
2. An agent omitting `depends_on` or setting it to `null` triggers oracle consultation as before
3. Template documentation and command prompts clearly explain when to use each form
4. Friction entry F015 is resolved—agents can declare chunks as independent without fake dependencies