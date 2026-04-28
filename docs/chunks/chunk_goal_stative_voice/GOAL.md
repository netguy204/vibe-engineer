---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/chunk/GOAL.md.jinja2
code_references:
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "Minor Goal placeholder with stative-voice guidance, present-tense framing, and contrast example"
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- narrative_proposed_chunks_doc
---

# Chunk Goal

## Minor Goal

The chunk GOAL.md template (`src/templates/chunk/GOAL.md.jinja2`) elicits
stative, evergreen, intent-owning prose for the Minor Goal section, matching
the project's principle that **"the intent of chunks is to always be an active
tense statement about the state of the architecture."**

The template's Minor Goal placeholder previously prompted transitory questions:

> "What does this chunk accomplish? Frame it in terms of docs/trunk/GOAL.md.
>  Why is this the right next step? What does completing this enable?"

All three phrasings — "accomplish", "next step", "completing this" — bias the
writer toward describing *the work being done* rather than *the state of the
architecture once the chunk owns its intent*. Real-world authoring sessions
routinely produce transitory goals as a result (e.g. "Wire progress() calls
into …" instead of "task-forecast-snapshots emits progress() calls at its
natural unit-of-work seams"). The system already paves over this by running
`/audit-intent` to migrate ACTIVE chunks to present-tense framing — an
indicator that the template is the upstream cause, and that fixing the
template removes the need for the post-hoc rewrite for newly-created chunks.

The schema's STATUS VALUES block already states "ACTIVE: Fully owns the intent
that governs the code," but that line is buried far above the Minor Goal
placeholder, and the connection between "owns intent" and "write in evergreen
tense" is implicit. The template surfaces that connection at the point of
authorship.

## Success Criteria

- The `## Minor Goal` placeholder in `src/templates/chunk/GOAL.md.jinja2` is
  rewritten so the prompts elicit stative voice. The transitory phrasings
  ("accomplish", "next step", "completing this") are removed.
- The new placeholder explicitly directs the writer to:
  - Describe the state of the architecture once the chunk owns its intent
  - Write in present tense as if the chunk is already ACTIVE
  - Avoid action verbs ("add", "wire", "make"); prefer state verbs ("emits",
    "enforces", "exposes", "tolerates")
  - Phrase the goal so it remains true years later if the chunk's intent
    continues to govern the code
- The placeholder includes at least one stative example alongside (or
  replacing) any implicit transitory example.
- The connection between "ACTIVE: Fully owns the intent" (already in the
  schema block) and the stative-voice requirement is made explicit at the
  point of authorship — either by repeating short guidance adjacent to the
  `## Minor Goal` heading, or by directly cross-referencing the STATUS VALUES
  definition.
- A fresh `ve chunk create <name>` (and `ve chunk create --future <name>`)
  produces a GOAL.md whose Minor Goal section guides the author toward
  stative phrasing on the first read.

## Out of Scope

- Changing the chunk schema, frontmatter fields, or validator behavior.
  This chunk only changes prompt wording in the GOAL.md template.
- Migrating existing chunks with transitory Minor Goal prose. That is the
  job of `/audit-intent` and is already covered.
- Touching the Success Criteria or Relationship-to-Parent placeholders,
  which already use stative voice acceptably.