---
status: ACTIVE
advances_trunk_goal: "Project Goal: strong documentation workflow leads to confident implementation"
proposed_chunks:
  - prompt: "Land docs/trunk/CHUNKS.md as the canonical statement of the four intent-ownership principles, and update the chunk status taxonomy in src/templates/chunk/GOAL.md.jinja2 and docs/trunk/SPEC.md to derive from it (drop SUPERSEDED, add COMPOSITE, sharpen ACTIVE/HISTORICAL definitions). Add a one-line cross-reference from docs/trunk/ARTIFACTS.md."
    chunk_directory: intent_principles
    depends_on: []
  - prompt: |
      Add an intent-judgment step to /chunk-create. The agent — not the operator — applies the principle-2 test: 'does this code need to remember why it exists?' The gate is asymmetric: silent on yes, escalate on suspected no.

      Behavior:
      - If the agent judges the work is clearly intent-bearing (architectural decision, constraint to remember, contract being established) → proceed silently. No prompt, no friction.
      - If the agent judges the work is likely NOT intent-bearing (mechanical change, typo, dep bump, performance tweak that doesn't change shape, comment cleanup) → surface to operator: 'this looks like it could be vibed — there's no obvious architectural intent to remember. Create the chunk anyway?' Operator confirms or skips.
      - If the agent detects orchestrator-execution signals in the user's request ('in the background', 'in parallel', 'via the orchestrator', 'queue these up', 'have an agent do this', 'spawn all the chunks in this narrative') → proceed silently regardless of intent-bearing judgment. The chunk is being created for delegation, not architectural memory; the operator has signaled they want a unit of work, not just a piece of intent.

      The asymmetry matters because operators routinely spawn whole narratives' worth of chunks in one prompt. Re-confirming every chunk would be unbearable. The agent only interrupts when it suspects scope creep into the chunk system — and even then, the operator has the override.

      Out of scope: changing /chunk-create's existing status routing (FUTURE vs IMPLEMENTING) or its handling of the existing-implementing-chunk case. This chunk only adds the intent-judgment layer in front of the goal-refinement step.
    chunk_directory: intent_create_gate
    depends_on: [0]
  - prompt: |
      Add a completion-time verification pass to /chunk-complete that enforces the principle 'a chunk's GOAL.md describes intent in present tense' and routes intent-less chunks toward deletion.

      Behavior at completion, before any status transition:

      1. Re-read GOAL.md. Detect retrospective framing tells: 'Currently,', 'was', 'we added', 'this chunk fixes', 'the fix:', 'will change to'. The agent rewrites the offending passages into present-tense descriptions of how the system works, using the implemented code as the source of truth. Proceed silently when the rewrite is mechanical (changing 'we added X' to 'X exists'; replacing 'Currently the system does Y, we'll change it to Z' with 'The system does Z because...'). Escalate to the operator only when (a) the goal asserts something the agent can't reconcile against the current code, (b) the rewrite would materially change the goal's meaning rather than just its tense, or (c) the agent's confidence in the rewrite is low. When escalating, present a candidate rewrite alongside the specific reason the agent couldn't land it on its own.

      2. Apply the intent test the same way /chunk-create does: does this code need to remember why it exists? If yes → status: ACTIVE. If no → status: HISTORICAL.

      3. When the agent decides HISTORICAL, prompt the operator: 'this chunk has no ongoing intent to remember — its job was to coordinate execution. Consider deleting it. The work is preserved in git; the chunk no longer earns its keep in docs/chunks/.' Operator chooses delete or keep. If keep, the chunk lands HISTORICAL with a brief note in its goal explaining why it was retained.

      4. Collapse the bug_type field. Under the new model, implementation-bug work doesn't flow through the chunk system at all (handled by the /chunk-create gate); semantic-bug work is just intent-bearing work that happens to start from a bug. Remove bug_type from the schema and the routing logic.

      The deletion prompt is the load-bearing piece: it lets chunks function as coordination mechanisms for orchestrator execution without permanently bloating the chunk corpus. A pure-execution chunk does its job, sequences alongside intent-bearing work, then gets cleaned up. The principle 'chunks exist for intent-bearing work' stays clean as a description of what survives in docs/chunks/.
    chunk_directory: intent_complete_verification
    depends_on: [0]
  - prompt: "Update CLAUDE.md and any other workflow-facing docs (README, ARTIFACTS.md getting-started sections, chunk-related skill descriptions) to reflect the gating principle: chunks are for intent-bearing work only. Replace any phrasing that implies chunks are the default mechanism for all work."
    chunk_directory: intent_workflow_docs
    depends_on: [0]
  - prompt: "Migrate the 12 existing SUPERSEDED chunks to either HISTORICAL (most cases — approach was replaced) or COMPOSITE (rare cases — chunk co-owns intent with active peers). Audit each one against the new taxonomy and update its status. Where HISTORICAL, ensure replaced_by or equivalent traceability is preserved. The 12 chunks: integrity_deprecate_standalone, jinja_backrefs, narrative_backreference_support, proposed_chunks_frontmatter, scratchpad_chunk_commands, scratchpad_cross_project, scratchpad_narrative_commands, scratchpad_storage, subsystem_template, template_drift_prevention, update_crossref_format, websocket_keepalive."
    chunk_directory: intent_superseded_migration
    depends_on: [0]
  - prompt: |
      Audit existing ACTIVE chunks for goals that don't describe the code as it actually stands. Two failure modes to catch:

      (1) Retrospective framing — goal text written in past/transitional tense that ages into a lie. Tells: 'Currently,', 'was', 'we added', 'this chunk fixes', 'this chunk adds', 'the fix:', 'will change to'. Anchor case: orch_activate_on_inject GOAL.md:46 ('Currently, the orchestrator injects FUTURE chunks...') is no longer true once ACTIVE.

      (2) Over-claimed scope — goal describes behaviors that the code does not actually implement. The chunk admits this in its own metadata. Tells: any code_reference with status: partial; implements descriptions containing 'does NOT implement', 'partial', 'only Step N of M', 'TODO', 'not yet'; success-criteria lists where the count of items exceeds the count of referenced symbols by a meaningful margin. Anchor case: respect_future_intent (status: ACTIVE) lists 5 success criteria but its code_references admit only Step 8 was implemented.

      For each candidate, present to the operator with the chosen failure mode and a recommended path:
      - Retrospective framing → rewrite goal text to present-tense description of how the system works.
      - Over-claimed scope → operator chooses between (a) revise the goal down to what the code actually does, or (b) finish the implementation so the goal becomes true. Prefer (a) for old chunks where the ambition has cooled; prefer (b) when the missing work is small and still wanted.

      Grep across docs/chunks/*/GOAL.md to enumerate candidates. Be exhaustive on the discovery pass; let the operator decide which to fix in this run vs defer.
    chunk_directory: intent_active_audit
    depends_on: [0]
  - prompt: "Deprecate SUPERSEDED rather than remove it. Removal would create a chicken-and-egg upgrade trap (chunks with status: SUPERSEDED fail validation; can't migrate without upgrading; can't upgrade without migrating). Instead: keep SUPERSEDED in ChunkStatus enum so existing chunks parse; close the on-ramp by removing ACTIVE→SUPERSEDED from VALID_CHUNK_TRANSITIONS; keep the off-ramp (SUPERSEDED→HISTORICAL) so the set drains. Emit a DeprecationWarning when SUPERSEDED is parsed, pointing at CHUNKS.md and the migration guide. ve chunk validate warns instead of erroring on SUPERSEDED. Update SPEC.md, CHUNKS.md, and the migration guide to note the deprecation."
    chunk_directory: intent_deprecate_superseded
    depends_on: [0]
created_after: ["leader_board"]
---

<!--
STATUS VALUES:
- DRAFTING: The narrative is being refined; chunks not yet created
- ACTIVE: Chunks are being created and implemented from this narrative
- COMPLETED: All chunks have been created and the narrative's ambition is realized

ADVANCES_TRUNK_GOAL:
- Reference the specific section of docs/trunk/GOAL.md this narrative advances
- Example: "Required Properties: Must support multi-repository workflows"

PROPOSED_CHUNKS:
- Starts empty; entries are added as prompts are turned into chunks via /chunk-create
- Each entry records which prompt was refined and where the resulting chunk lives
- prompt: The prompt text from this document that was used to create the chunk
- chunk_directory: The created chunk directory (e.g., "feature_name"), null until created
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
- DO NOT POPULATE this array during narrative creation. It will be populated as
  chunks are created.
- Use `ve chunk list-proposed` to see all proposed chunks that haven't been created yet
-->

## Advances Trunk Goal

`docs/trunk/GOAL.md` opens with: *"a strong documentation workflow leads to confident implementation of code and makes future change relatively low cost."* This narrative gives that thesis its sharpest expression in the chunk system: chunks are the documentation layer that *holds the codebase's architectural shape*. Code owns implementation; chunks own intent; together they are the architecture. Without a clear principle of what chunks are for, the documentation workflow drifts toward either over-documentation (a chunk for every change) or under-documentation (chunks as ceremony, not signal). This narrative establishes the principle and propagates it through every place that the chunk concept touches.

## Driving Ambition

The chunk system rests on a single, teachable principle:

> **Code owns implementation. Chunks own intent. Together they are the architecture.**

From that one sentence, three derivations follow:

1. **Chunks exist only for intent-bearing work.** Intent-less work — typos, dependency bumps, mechanical renames, one-off bug patches — bypasses the chunk system entirely. The test: *does this code need to remember why it exists?*
2. **A chunk's GOAL.md is present-tense.** It describes how the system works, not what changed. It reads true at every status. Git owns the past.
3. **Status answers a single question** — how much of the intent does this chunk own? FUTURE (not yet), IMPLEMENTING (taking ownership), ACTIVE (fully owns), COMPOSITE (shares ownership with peers), HISTORICAL (no longer owns).

The narrative threads this principle through every artifact that touches chunks — the canonical doc, the template, the spec, the skills, and the existing chunk corpus. By the end, an operator or agent encountering chunks for the first time gets a single, coherent answer to *"what is a chunk for?"* — and the existing corpus matches that answer.

## Chunks

The narrative decomposes into seven chunks. The first lands the principle as canonical text, reshapes the status taxonomy, and adds COMPOSITE to the runtime alongside SUPERSEDED. The next three derive behavior from the principle (skill changes and workflow doc updates). The next two clean up the existing corpus. The final chunk retires SUPERSEDED from the runtime once nothing uses it.

1. **`intent_principles`** *(IMPLEMENTING)* — Land `docs/trunk/CHUNKS.md`, update the status taxonomy in template + SPEC, and add COMPOSITE to the runtime enum / validation / CLI / orchestrator activation. SUPERSEDED stays in the runtime for now (the 12 existing chunks still need it). The seed.
2. **Intent-test gate at `/chunk-create`** — Soft-prompt the operator at chunk creation: *"Does this code need to remember why it exists?"* Gate, not block.
3. **Completion-time verification pass at `/chunk-complete`** — Re-read GOAL.md and rewrite retrospective framing into present-tense (escalate only when the agent can't); apply the intent test to decide ACTIVE vs HISTORICAL; prompt to delete HISTORICAL chunks (so coordination-only chunks don't bloat the corpus); collapse `bug_type`.
4. **Workflow doc updates** — CLAUDE.md and other workflow-facing docs reflect the "chunks for intent-bearing work only" framing.
5. **SUPERSEDED chunk migration** — Move the 12 existing SUPERSEDED chunks into the new taxonomy (HISTORICAL or COMPOSITE).
6. **ACTIVE chunk truthfulness audit** — Sweep ACTIVE chunks for goals that don't describe code as it actually stands. Two failure modes: retrospective framing (goal ages into a lie) and over-claimed scope (goal asserts behaviors the code doesn't implement, often visible as `status: partial` in `code_references`). For each candidate, rewrite or finish the implementation depending on what's still wanted. Anchor cases: `orch_activate_on_inject` (retrospective) and `respect_future_intent` (over-claimed).
7. **Deprecate SUPERSEDED in the runtime** — Close the on-ramp (`ACTIVE → SUPERSEDED` transition removed) while keeping the off-ramp (`SUPERSEDED → HISTORICAL` preserved) and the enum value (existing SUPERSEDED chunks keep parsing). A DeprecationWarning fires on parse, pointing at the migration guide. Removing SUPERSEDED entirely is deferred indefinitely — that would create an upgrade-cycle trap.

Chunks 2-6 all depend on chunk 1 (the seed must exist before behavior or migration can reference it). Within 2-6, chunks are largely independent and can ship in any order — though chunk 6 (audit) benefits from being last so the verification pass from chunk 3 catches any new violations going forward. Chunk 7 also depends only on chunk 1: deprecation is safe regardless of migration progress, and the deprecation warning actively encourages unmigrated projects to run the migration.

## Completion Criteria

When the narrative is complete:

- **A new operator can read `docs/trunk/CHUNKS.md` in 2 minutes** and walk away knowing what chunks are for, when to make one, how to write its goal, and what its status means.
- **The `/chunk-create` skill prompts the intent test** before refining a goal, so operators don't accidentally create ceremonial chunks.
- **The `/chunk-complete` skill verifies present-tense framing** before marking ACTIVE, so chunks don't age into lies.
- **Every chunk in `docs/chunks/`** carries a status from the new taxonomy and reads true under the present-tense rule. No chunk uses the retired `SUPERSEDED` status.
- **Workflow-facing docs (CLAUDE.md, ARTIFACTS.md)** consistently describe chunks as the artifact for intent-bearing work, not as the default mechanism for all work.

The narrative is not about a feature. It is about getting the project to *speak with one voice* about its central artifact.