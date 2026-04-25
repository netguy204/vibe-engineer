---
status: ACTIVE
advances_trunk_goal: "Project Goal: strong documentation workflow leads to confident implementation"
proposed_chunks:
  - prompt: "Land docs/trunk/CHUNKS.md as the canonical statement of the four intent-ownership principles, and update the chunk status taxonomy in src/templates/chunk/GOAL.md.jinja2 and docs/trunk/SPEC.md to derive from it (drop SUPERSEDED, add COMPOSITE, sharpen ACTIVE/HISTORICAL definitions). Add a one-line cross-reference from docs/trunk/ARTIFACTS.md."
    chunk_directory: intent_principles
    depends_on: []
  - prompt: "Add an intent-test gate to /chunk-create. Before refining a goal, the skill asks the operator the principle-2 question: does this code need to remember why it exists? If no, it suggests skipping the chunk and editing directly. The gate is a soft prompt, not a hard block — operator can override."
    chunk_directory: null
    depends_on: [0]
  - prompt: "Add a present-tense verification pass to /chunk-complete. Before marking ACTIVE, re-read GOAL.md and flag retrospective framing tells (Currently,, was, we added, this chunk fixes); prompt the operator to rewrite into present-state description. Also collapse the bug_type field: implementation bugs no longer flow through chunks at all (handled by the /chunk-create gate); semantic bugs follow the standard ACTIVE path."
    chunk_directory: null
    depends_on: [0]
  - prompt: "Update CLAUDE.md and any other workflow-facing docs (README, ARTIFACTS.md getting-started sections, chunk-related skill descriptions) to reflect the gating principle: chunks are for intent-bearing work only. Replace any phrasing that implies chunks are the default mechanism for all work."
    chunk_directory: null
    depends_on: [0]
  - prompt: "Migrate the 12 existing SUPERSEDED chunks to either HISTORICAL (most cases — approach was replaced) or COMPOSITE (rare cases — chunk co-owns intent with active peers). Audit each one against the new taxonomy and update its status. Where HISTORICAL, ensure replaced_by or equivalent traceability is preserved. The 12 chunks: integrity_deprecate_standalone, jinja_backrefs, narrative_backreference_support, proposed_chunks_frontmatter, scratchpad_chunk_commands, scratchpad_cross_project, scratchpad_narrative_commands, scratchpad_storage, subsystem_template, template_drift_prevention, update_crossref_format, websocket_keepalive."
    chunk_directory: null
    depends_on: [0]
  - prompt: "Audit existing ACTIVE chunks for retrospective framing tells (Currently,, was, we added, this chunk fixes, this chunk adds). Grep across docs/chunks/*/GOAL.md, present candidates to the operator, and rewrite violators into present-tense descriptions of system state. The known anchor case is orch_activate_on_inject GOAL.md:46 (Currently, the orchestrator injects FUTURE chunks...) which becomes a lie once ACTIVE."
    chunk_directory: null
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

The narrative decomposes into six chunks. The first lands the principle as canonical text and reshapes the status taxonomy. The next three derive behavior from the principle (skill changes and workflow doc updates). The last two clean up the existing corpus to match the new framing.

1. **`intent_principles`** *(IMPLEMENTING)* — Land `docs/trunk/CHUNKS.md` and update the status taxonomy in template + SPEC. The seed.
2. **Intent-test gate at `/chunk-create`** — Soft-prompt the operator at chunk creation: *"Does this code need to remember why it exists?"* Gate, not block.
3. **Present-tense verification pass at `/chunk-complete`** — Re-read GOAL.md before marking ACTIVE; flag retrospective framing tells; collapse `bug_type` field.
4. **Workflow doc updates** — CLAUDE.md and other workflow-facing docs reflect the "chunks for intent-bearing work only" framing.
5. **SUPERSEDED chunk migration** — Move the 12 existing SUPERSEDED chunks into the new taxonomy (HISTORICAL or COMPOSITE).
6. **ACTIVE chunk framing audit** — Sweep ACTIVE chunks for retrospective framing tells; rewrite violators into present-tense.

Chunks 2-6 all depend on chunk 1 (the seed must exist before behavior or migration can reference it). Within 2-6, chunks are largely independent and can ship in any order — though chunk 6 (audit) benefits from being last so the verification pass from chunk 3 catches any new violations going forward.

## Completion Criteria

When the narrative is complete:

- **A new operator can read `docs/trunk/CHUNKS.md` in 2 minutes** and walk away knowing what chunks are for, when to make one, how to write its goal, and what its status means.
- **The `/chunk-create` skill prompts the intent test** before refining a goal, so operators don't accidentally create ceremonial chunks.
- **The `/chunk-complete` skill verifies present-tense framing** before marking ACTIVE, so chunks don't age into lies.
- **Every chunk in `docs/chunks/`** carries a status from the new taxonomy and reads true under the present-tense rule. No chunk uses the retired `SUPERSEDED` status.
- **Workflow-facing docs (CLAUDE.md, ARTIFACTS.md)** consistently describe chunks as the artifact for intent-bearing work, not as the default mechanism for all work.

The narrative is not about a feature. It is about getting the project to *speak with one voice* about its central artifact.