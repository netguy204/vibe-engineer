

# Implementation Plan

## Approach

This chunk is purely prompt engineering. The four prompts that drive entity creation
and migration currently produce functional wikis but fall short of the quality bar
set by the investigation prototypes (`wiki_a/`, `wiki_b/`, `wiki_uniharness/`). The
gap is conceptual framing, not capability: the construction agents aren't told that
cross-references ARE the value, that adversity is the richest source material, or
that a lint pass is required before they finish.

The sibling chunk (`entity_wiki_maintenance_prompt`) already strengthened the runtime
side: the schema document (`wiki/wiki_schema.md`) now carries the "compounding
artifact" framing and the Ingest/Query/Lint operations model. This chunk extends
that same framing into the initial creation and migration paths.

**Key principle**: Reuse the schema document — don't duplicate its content in the
creation prompts. The schema already exists in the entity repo; creation prompts
should reference it and apply its framing, not restate it verbatim.

**No interface changes**: All modifications are to prompt strings inside existing
functions. The signatures of `_wiki_creation_prompt`, `_wiki_update_prompt`,
`synthesize_identity_page`, and `synthesize_knowledge_pages` remain unchanged.

## Subsystem Considerations

No relevant subsystems (prompt construction is not part of any documented subsystem).

## Sequence

### Step 1: Strengthen `_wiki_creation_prompt` in `entity_from_transcript.py`

**Current state**: The prompt frames the task as "construct a comprehensive wiki from
the knowledge and patterns you discover" and lists quality-bar bullets. It does not
communicate that cross-references are primary, that adversity is the richest material,
or that a lint pass is required.

**Changes**:

1. Open with the compounding-artifact framing from `entity_wiki_maintenance_prompt`:
   the wiki is a persistent, compounding artifact; cross-references ARE the value;
   connections between pages compound over time.

2. Reframe the task description from "construct a comprehensive wiki" to "you are
   **integrating** the transcript's knowledge into a structured, interlinked wiki —
   not summarizing the conversation." The Ingest operation framing from the schema
   applies here.

3. Add adversity emphasis to the quality bar: the most valuable content comes from
   failures, surprises, corrections, and unexpected behaviors in the transcript.
   Flag these explicitly.

4. Add a numbered **Step 4: Lint pass** to the instructions sequence. After writing
   all pages, do a review pass:
   - Any concept mentioned in a page that lacks its own page → create it
   - Any page with no outbound wikilinks to related pages → add the links
   - Any two pages that clearly relate to each other but don't link → connect them
   - Check that `index.md` includes every page written
   This step is **not optional** — it is part of construction, not cleanup.

5. Update the quality-bar bullets to replace "Cross-references: link related pages"
   with a stronger statement: cross-references are not decoration — they are what
   makes the wiki a knowledge base rather than a collection of notes.

**Location**: `src/entity_from_transcript.py:_wiki_creation_prompt`

---

### Step 2: Strengthen `_wiki_update_prompt` in `entity_from_transcript.py`

**Current state**: The prompt frames subsequent transcripts as "updating the wiki with
new knowledge gained in this session." The quality bar says "Integrate, don't just
append" but doesn't elaborate on how. No lint step is present.

**Changes**:

1. Add explicit compounding framing: this transcript is **compounding** onto existing
   knowledge — the goal is not to add new pages alongside old ones, but to deepen
   existing understanding, revise pages where new evidence changes the picture, and
   connect new knowledge to old knowledge via cross-references.

2. Add three explicit integration requirements to the instructions:
   - **Revise existing pages** where new session evidence deepens or changes the
     current understanding (don't just append; rewrite the relevant sections)
   - **Cross-reference** between new pages/sections and existing pages they relate to
   - **Note contradictions**: if new evidence conflicts with an existing claim, update
     the existing page and mark the contradiction resolved (or flag it as open)

3. Add adversity emphasis: failures and corrections in the new transcript are the most
   valuable content — update the relevant domain/techniques pages and add to
   `identity.md` Hard-Won Lessons if the lesson generalizes.

4. Add a **Lint step** (same structure as Step 1, adapted for incremental update):
   - Any new concept introduced in this session that lacks a page → create it
   - Any existing page that needs an update given what happened → update it
   - Any cross-reference between a new page and an existing page that's missing → add it
   - Update `index.md` for any new pages

5. Strengthen identity evolution guidance: if the entity's self-model shifted during
   this session (new values surfaced, existing assumptions corrected), update
   `identity.md` to reflect it. Identity evolution is as important as domain knowledge.

**Location**: `src/entity_from_transcript.py:_wiki_update_prompt`

---

### Step 3: Strengthen `_IDENTITY_SYNTHESIS_PROMPT` in `entity_migration.py`

**Current state**: The prompt asks the LLM to produce an `identity.md` from memory
inputs and specifies the page structure. It has a wikilinks instruction ("Use wikilinks
to reference concepts that should have their own pages") but the overall framing is
synthesis/distillation — "distill the essence of the entity."

**Changes**:

1. Add the cross-reference quality bar more explicitly: the identity page should link
   to relevant domain, techniques, and relationship pages. Connections make identity
   legible in context, not in isolation.

2. Elevate the **Hard-Won Lessons** section. The current prompt mentions it but doesn't
   explain its primacy. Add: this is the most important section — it captures what
   could only be learned by doing: failures, surprises, corrected assumptions, moments
   where the entity's model of the world turned out to be wrong. This is where the
   entity's memory earns its value.

3. Add framing that parallels the investigation's finding: the best identity pages don't
   enumerate what the entity knows — they capture who the entity is. Core memories are
   the raw material; the identity page should synthesize them into a self-model with
   character, not a list.

4. Strengthen the synthesis/organization instruction: do not list memories verbatim;
   organize them into a narrative that would read coherently to someone meeting the
   entity for the first time.

**Location**: `src/entity_migration.py:_IDENTITY_SYNTHESIS_PROMPT`

---

### Step 4: Strengthen `_KNOWLEDGE_PAGES_PROMPT` in `entity_migration.py`

**Current state**: The prompt asks for a JSON array of `{filename, content}` objects,
with pages that use wikilinks. There is no instruction to cross-reference between
pages within the same batch, and no post-synthesis lint pass.

**Changes**:

1. Add explicit intra-batch cross-reference requirement: after drafting all pages,
   review them as a set. Add wikilinks between any two pages in the batch that relate
   to each other. The pages should form a connected subgraph, not an isolated list.

2. Add cross-wiki reference guidance: where a domain page references a concept that
   belongs in a techniques page (or vice versa), add the wikilink even if the target
   page is in a different directory (`[[techniques/name]]`).

3. Add a **"cross-reference audit" step** embedded at the end of the prompt: after
   generating all page content, review the set and list any cross-reference additions
   made. Include those additions in the final page content before returning the JSON.
   This makes the lint pass part of the single LLM call rather than a separate pass.

4. Strengthen the "one concept per page" guidance: related memories should be grouped
   into a coherent page, not fragmented into micro-pages. If a concept is mentioned
   in multiple memories, those memories belong on the same page.

**Location**: `src/entity_migration.py:_KNOWLEDGE_PAGES_PROMPT`

---

### Step 5: Write tests for prompt content

Following the testing philosophy: tests assert semantically meaningful properties
(the prompts contain the required framing) rather than structural properties (the
function exists). The success criteria explicitly calls for these tests.

#### `test_entity_from_transcript.py` additions

Add a new `TestWikiPromptContent` class:

- **`test_creation_prompt_includes_compounding_framing`**: Call
  `_wiki_creation_prompt("test-entity", None, None)` and assert "compound" appears
  in the result. Verifies: creation prompt has compounding-artifact framing.

- **`test_creation_prompt_includes_lint_step`**: Assert the result includes a lint
  check instruction. Use keywords like "cross-reference" or "orphan" or "lint".
  Verifies: creation prompt includes an explicit lint operation.

- **`test_creation_prompt_emphasizes_adversity`**: Assert "adversity" or "failures"
  or "failure" appears in the result. Verifies: creation prompt frames adversity as
  the richest source material.

- **`test_update_prompt_includes_cross_reference_guidance`**: Call
  `_wiki_update_prompt("test-entity", 2, None)` and assert it includes cross-reference
  update guidance (e.g., "cross-reference" appears). Verifies: update prompt requires
  connecting new knowledge to existing pages.

- **`test_update_prompt_includes_lint_step`**: Assert the update prompt includes lint
  guidance (e.g., "lint" or "missing" cross-references). Verifies: update prompt
  includes an explicit lint operation.

- **`test_update_prompt_includes_identity_evolution`**: Assert the update prompt
  references identity evolution (e.g., "identity.md" and a change-related word like
  "evolved" or "shifted" or "update"). Verifies: update prompt captures self-model
  changes.

These functions are pure string-returning functions — no mocking needed. Tests call
them with simple args and assert on the returned string content.

Import `_wiki_creation_prompt` and `_wiki_update_prompt` directly from
`entity_from_transcript`.

#### `test_entity_migration.py` additions

Add a new `TestMigrationPromptContent` class:

- **`test_identity_prompt_includes_cross_reference_requirement`**: Assert
  `_IDENTITY_SYNTHESIS_PROMPT` contains a cross-reference instruction (e.g.,
  "wikilink" or "cross-reference"). Verifies: migration identity prompt requires
  linking to related pages.

- **`test_identity_prompt_emphasizes_hard_won_lessons`**: Assert the prompt
  emphasizes the Hard-Won Lessons section's primacy (e.g., "most important" or
  "failures" appearing near "lessons"). Verifies: identity synthesis prioritizes
  adversity content.

- **`test_knowledge_pages_prompt_includes_cross_reference_requirement`**: Assert
  `_KNOWLEDGE_PAGES_PROMPT` contains an intra-batch cross-reference requirement
  (e.g., "cross-reference" or "wikilink" between pages). Verifies: knowledge page
  synthesis produces interlinked pages.

Import `_IDENTITY_SYNTHESIS_PROMPT` and `_KNOWLEDGE_PAGES_PROMPT` directly from
`entity_migration`.

---

### Step 6: Update GOAL.md code_paths

Add `src/entity_from_transcript.py` and `src/entity_migration.py` to
`code_paths` in `docs/chunks/entity_creation_wiki_prompts/GOAL.md` and add
`code_references` entries for the four modified prompts.

(This step is already partially done — both files are listed — but
`code_references` should be populated after implementation.)

## Dependencies

- `entity_wiki_maintenance_prompt` chunk (listed in `depends_on`) must be ACTIVE
  before this chunk lands, so that `wiki/wiki_schema.md` already carries the
  compounding-artifact framing referenced in the creation prompts. The schema document
  is what the creation agent reads at the start of its session; its quality directly
  affects whether the framing in the creation prompt lands.

## Risks and Open Questions

- **Prompt length vs. quality**: The creation and update prompts will get longer. The
  current prompts are ~40 lines. Adding compounding framing + lint step will bring
  them to ~60–70 lines each. This is well within practical limits for Agent SDK
  sessions but worth watching.

- **Lint step effectiveness**: The lint step is embedded in the same agent session as
  construction. Whether the agent actually performs it as a distinct review vs. just
  claims it did is not testable without live evaluation. The tests verify the prompt
  instructs a lint pass; actual quality verification is the operator's responsibility
  (per the success criterion "After landing, new entities ... have cross-reference
  density comparable to investigation prototypes").

- **`_KNOWLEDGE_PAGES_PROMPT` cross-reference audit**: The post-batch review is
  embedded in a single Messages API call (not an Agent SDK session). The agent has no
  file system access — it only sees the memories text. The cross-reference audit must
  therefore produce wikilinks between pages it is drafting within that single response,
  without being able to read the actual files. This is the correct framing: instruct
  the LLM to audit its own output before serializing to JSON.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION, not at planning time. -->
