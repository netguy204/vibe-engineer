---
status: SOLVED
trigger: Concurrent chunk reviews cause merge conflicts in shared DECISION_LOG.md, requiring manual resolution that disrupts flow
proposed_chunks:
  - prompt: |
      Create pydantic models and directory structure for per-file decisions.
      Model decision file frontmatter (decision, summary, operator_review union type).
      Create docs/reviewers/baseline/decisions/ directory. Use prototypes/decision_template.md
      as reference. The operator_review is Union[Literal["good", "bad"], FeedbackReview].
    chunk_directory: reviewer_decision_schema
    depends_on: []
  - prompt: |
      Add CLI command to instantiate decision templates.
      ve reviewer decision create <chunk> [--reviewer baseline] [--iteration 1]
      Creates file at docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md
      Pre-populates frontmatter with null values, body with criteria template from GOAL.md.
    chunk_directory: reviewer_decision_create_cli
    depends_on: [0]
  - prompt: |
      Add CLI to aggregate decisions for few-shot context.
      ve reviewer decisions --recent N [--reviewer baseline]
      Filters to only decisions with operator_review populated.
      Outputs working-directory-relative path, decision, summary, operator_review.
      See prototypes/fewshot_output_example.md for format.
    chunk_directory: reviewer_decisions_list_cli
    depends_on: [0]
  - prompt: |
      Add CLI for operator review workflow.
      ve reviewer decisions review <path> good|bad
      ve reviewer decisions review <path> --feedback "<message>"
      Updates operator_review field in decision file frontmatter.
      ve reviewer decisions --pending lists decisions awaiting review.
    chunk_directory: reviewer_decisions_review_cli
    depends_on: [0]
  - prompt: |
      Update chunk-review skill to use the new decision file system.
      Reviewer calls ve reviewer decision create before writing decision.
      Reviewer calls ve reviewer decisions --recent 10 for few-shot context.
      Remove append to DECISION_LOG.md. Update prompt to reference decision files.
      Migrate existing DECISION_LOG.md entries to individual decision files,
      preserving any operator feedback that already exists.
    chunk_directory: reviewer_use_decision_files
    depends_on: [1, 2, 3]
created_after: ["referential_integrity"]
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

The reviewer's DECISION_LOG.md is a single shared file that all chunk reviews append to. When the orchestrator runs multiple chunks concurrently, each reviewer instance appends decisions to the same file, virtually guaranteeing merge conflicts when worktrees are merged back.

The conflicts are always trivially resolvable—just retain all appended entries—but we don't have automation for resolving merge conflicts. This creates a manual chore that disrupts flow and limits chunk throughput. Every concurrent review batch requires operator intervention to resolve conflicts before proceeding.

## Success Criteria

1. **Identify a storage structure** that avoids concurrent-write conflicts while preserving access to decision history for few-shot context

2. **Validate the few-shot value is preserved** - the reviewer can still use past decisions to calibrate its judgment under the new structure

3. **Design operator tooling for trust graduation** - the new structure should enable CLI commands that let the operator see pending decisions, apply feedback (good/bad), and track reviewer calibration progress

## Testable Hypotheses

### H1: Per-chunk decision files eliminate conflicts without losing history

- **Rationale**: If each review writes to `decisions/{chunk_name}.yaml` instead of appending to a shared file, concurrent reviews never touch the same file
- **Test**: Verify that concurrent chunk reviews in separate worktrees produce no merge conflicts
- **Status**: UNTESTED

### H2: A CLI aggregation command provides few-shot context without coupling

- **Rationale**: The reviewer agent calls something like `ve reviewer decisions --recent 10` to get aggregated few-shot context. The reviewer doesn't need to know about file structure—aggregation logic is centralized in the CLI.
- **Test**: Prototype the CLI command and verify the output is usable as few-shot context in the reviewer prompt
- **Status**: UNTESTED

### H3: Recent decisions are sufficient for few-shot calibration

- **Rationale**: The reviewer doesn't need the entire decision history—just enough recent examples to calibrate judgment. This bounds the context size and simplifies aggregation.
- **Test**: Determine an appropriate N (e.g., 10-20 recent decisions) that provides calibration value without excessive context
- **Status**: UNTESTED

### H4: Per-file structure enables ergonomic operator review tooling

- **Rationale**: Individual decision files can carry metadata (reviewed: true/false, operator_feedback: good/bad/comment). CLI commands can filter, display, and update this metadata. This makes the observation → calibration → delegation loop practical.
- **Test**: Design the decision file schema and sketch CLI commands that would support the operator review workflow
- **Status**: UNTESTED

## Exploration Log

### 2026-01-31: Initial framing and key insight

Established the core design direction:

1. **Per-chunk decision files** instead of appending to shared DECISION_LOG.md
2. **CLI aggregation** for few-shot context (`ve reviewer decisions --recent N`)
3. **Operator tooling** for reviewing decisions and providing feedback

**Key insight: Curated few-shot context**

The CLI that provides few-shot examples should only include decisions that have operator feedback. This means:

- Reviewer makes decision → stored as pending review
- Operator reviews and marks good/bad/feedback → decision becomes eligible
- `ve reviewer decisions --recent 10` filters to only reviewed decisions

Unreviewed decisions don't pollute the few-shot context. The reviewer learns exclusively from calibrated examples. This makes trust graduation explicit—few-shot examples are earned through operator review, not accumulated automatically.

**CLI-instantiated decision templates**

The reviewer agent should not free-form write decision files. Instead:

- `ve reviewer decision create <chunk>` instantiates a structured template
- The reviewer agent fills in the template fields
- This keeps decisions on track with the expected format and detail level
- Easier to parse, aggregate, and display in operator tooling

See prototype: `prototypes/decision_template.md`

File path convention: `docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md`
- Chunk and reviewer inferred from path, not stored in file
- Iteration count enables independent review per review cycle

**Few-shot output format (progressive discovery)**

The aggregation CLI prints a compact summary per decision:
- Filename (implies chunk + iteration)
- Summary
- Decision (APPROVE/FEEDBACK/ESCALATE)
- Operator verdict + feedback

The agent sees patterns at a glance ("operator said 'too strict' on that FEEDBACK"). If a past decision seems particularly relevant to the current review, the agent can read the full file to get detailed criteria assessment, feedback items, etc.

This keeps few-shot context compact while enabling deep dives when the situation warrants.

See prototype: `prototypes/fewshot_output_example.md`

**Operator review as union type**

The `operator_review` field is a union:
- String literal: `good` or `bad`
- Map with message: `{ feedback: "<message>" }`

```python
OperatorReview = Union[Literal["good", "bad"], FeedbackReview]
```

Type discriminates naturally—no prefix parsing needed.

## Findings

### Verified Findings

**F1: Per-file decisions eliminate merge conflicts**

Each review writes to `docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md`. Concurrent reviews never touch the same file.

**F2: CLI aggregation enables curated few-shot context**

`ve reviewer decisions --recent N` filters to only operator-reviewed decisions. Few-shot examples are earned through operator review, not accumulated automatically.

**F3: Union type cleanly represents operator review**

`operator_review` is either a string (`good` | `bad`) or a map (`{ feedback: "<message>" }`). Type discriminates naturally.

**F4: Progressive discovery keeps few-shot compact**

The aggregation CLI outputs summary/decision/review per file. The agent can read full details from decisions that seem relevant to the current review.

### Hypotheses/Opinions

- The appropriate N for `--recent N` needs operational experience to calibrate (start with 10?)
- Operator review workflow will surface additional UX needs as it's used

## Proposed Chunks

### 0. reviewer_decision_schema

Create the pydantic models and directory structure for per-file decisions.

**Deliverables:**
- Pydantic model for decision file frontmatter (decision, summary, operator_review union type)
- Create `docs/reviewers/baseline/decisions/` directory
- Add schema validation to reviewer subsystem

**Notes:** Use `prototypes/decision_template.md` as reference. The operator_review union type is `Union[Literal["good", "bad"], FeedbackReview]`.

---

### 1. reviewer_decision_create_cli

Add CLI command to instantiate decision templates.

**Deliverables:**
- `ve reviewer decision create <chunk> [--reviewer baseline] [--iteration 1]`
- Creates file at `docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md`
- Pre-populates frontmatter with null values, body with criteria template

**Notes:** The reviewer agent calls this before filling in the decision. Keeps decisions on track with expected format.

---

### 2. reviewer_decisions_list_cli

Add CLI command to aggregate decisions for few-shot context.

**Deliverables:**
- `ve reviewer decisions --recent N [--reviewer baseline]`
- Filters to only decisions with `operator_review` populated
- Outputs working-directory-relative path, decision, summary, operator_review per file

**Notes:** See `prototypes/fewshot_output_example.md` for output format. Progressive discovery: agent can read full files for details.

---

### 3. reviewer_decisions_review_cli

Add CLI command for operator review workflow.

**Deliverables:**
- `ve reviewer decisions review <path> good|bad`
- `ve reviewer decisions review <path> --feedback "<message>"`
- Updates the `operator_review` field in the decision file frontmatter
- `ve reviewer decisions --pending` lists decisions awaiting operator review

**Notes:** This enables the trust graduation loop. Only reviewed decisions appear in few-shot context.

---

### 4. reviewer_use_decision_files

Update chunk-review skill to use the new decision file system and migrate existing decisions.

**Deliverables:**
- Reviewer calls `ve reviewer decision create <chunk>` before writing decision
- Reviewer calls `ve reviewer decisions --recent 10` for few-shot context
- Remove append to DECISION_LOG.md
- Update reviewer prompt to reference decision files for past examples
- Migrate existing DECISION_LOG.md entries to individual decision files, preserving any operator feedback

**Notes:** This is the migration point. After this chunk, concurrent reviews no longer conflict. Decisions with existing operator feedback will appear in few-shot immediately.

## Resolution Rationale

The investigation answered all success criteria:

1. **Storage structure identified**: Per-file decisions at `docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md` eliminate concurrent-write conflicts entirely.

2. **Few-shot value preserved**: CLI aggregation (`ve reviewer decisions --recent N`) provides curated context. Only operator-reviewed decisions become few-shot examples—trust is earned, not accumulated.

3. **Operator tooling designed**: CLI commands for creating decisions, listing/aggregating, and applying operator review. Enables the trust graduation loop from the original reviewer investigation.

The solution also provides benefits beyond the original problem:
- Structured decision templates keep the reviewer on track
- Progressive discovery keeps few-shot compact while enabling deep dives
- Operator review workflow makes calibration practical

Five chunks proposed to implement the system, with chunks 1-3 parallelizable after the schema chunk completes. Chunk 4 is the migration point where the reviewer switches to the new system.