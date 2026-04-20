

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk is purely a template content change — no new Python logic, no new CLI commands,
and no new test code. All changes are to two Jinja2 template files:

- `src/templates/entity/wiki_schema.md.jinja2` — primary target, multiple sections
- `src/templates/entity/wiki/identity.md.jinja2` — audit and minor comment adjustment

Per the project's TESTING_PHILOSOPHY.md: "Template content: We verify templates render
without error and files are created, but don't assert on template prose." No new tests
are required. Existing tests (`test_entities.py` exercises `create_entity`, which renders
these templates) will serve as the regression guard — run them after each step.

The changes are sequenced so each step targets a distinct section of the template,
minimising the chance of a messy merge or missed update.

## Subsystem Considerations

No subsystems are relevant. This chunk touches only entity wiki templates.

## Sequence

### Step 1: Reframe the identity.md one-liner in "What Goes Where"

**File:** `src/templates/entity/wiki_schema.md.jinja2`

**Target (current line ~37):**
```
- **`identity.md`** — Your self-model: role, strengths, working style, values, and hard-won lessons.
```

**Replace with:**
```
- **`identity.md`** — Who you are and what you value. Lean, curated, readable in one sitting. NOT a dumping ground for technical findings or mechanics.
```

### Step 2: Rewrite the `### \`identity.md\`` block in "What to Capture"

**File:** `src/templates/entity/wiki_schema.md.jinja2`

**Target (current lines ~74–83):**
```markdown
### `identity.md`

Your self-model. The most important section is **Hard-Won Lessons** — document failures,
surprising discoveries, corrected assumptions, and adversity. This is where your memory matters most.

- **Who I Am**: What kind of entity you are, what you've done
- **Role**: Your current purpose and responsibilities
- **Working Style**: How you approach work — methodologies, phases, decision patterns
- **Values**: What you optimize for, what tradeoffs you make, what you refuse to compromise on
- **Hard-Won Lessons**: Lessons from failure and adversity — the things you had to learn the hard way
```

**Replace with:**
```markdown
### `identity.md`

Who you are and what you value. Lean, curated, readable in one sitting.
**NOT a dumping ground** for technical findings, mechanics, or recipes.

- **Who I Am**: What kind of entity you are, what you've done
- **Role**: Your current purpose and responsibilities
- **Working Style**: How you approach work — methodologies, phases, decision patterns
- **Values**: What you optimize for, what tradeoffs you make, what you refuse to compromise on
- **Hard-Won Lessons**: ~8–15 principle-level entries. Each ends with a `See:` link to the
  mechanics page(s) where the how-to details live. Adding to this section should be **rare**.
  If you are adding multiple entries per session, you are most likely dumping mechanics here.

**The routing test for Hard-Won Lessons:** Would this principle still apply if the codebase,
technology, or project changed completely? If yes → identity.md. If no → domain/ or techniques/.

*Worked examples:*
- "I learn fastest by writing a minimal failing case first." — codebase-independent → identity.md
- "The savings-account ledger requires a debit before a credit on reversals." — project-specific
  mechanics → domain/savings_ledger.md, with a `See:` link from any identity principle that
  covers the broader lesson.

**The `See:` convention:** Every Hard-Won Lessons entry that has a corresponding mechanics page
should end with `See: [[domain/page_name]]` or `See: [[techniques/pattern_name]]`. The principle
lives on identity.md; the mechanics live elsewhere. Neither duplicates the other.
```

### Step 3: Add "absorbs mechanics/recipes" framing to `domain/` and `techniques/` sections

**File:** `src/templates/entity/wiki_schema.md.jinja2`

After the `### \`domain/\` Pages` header and intro line, insert a clarifying sentence:

Current `domain/` intro:
```
One page per major concept. Capture:
```

Replace with:
```
One page per major concept. This is the **default home for technical findings and mechanics**
— when you discover how something works, it goes here first. Capture:
```

After the `### \`techniques/\` Pages` header and intro line:

Current `techniques/` intro:
```
One page per approach or pattern. Capture:
```

Replace with:
```
One page per approach or pattern. This is the **default home for recipes, procedures, and
reusable patterns**. When identity.md Hard-Won Lessons reference a how-to, the details live
here. Capture:
```

### Step 4: Add a "Decision Rubric" section

**File:** `src/templates/entity/wiki_schema.md.jinja2`

Insert a new section immediately **before** the existing `## Maintenance Workflow` section.
The rubric routes a finding to the correct location before any file is touched.

```markdown
## Decision Rubric: Where Does This Finding Go?

Before opening any wiki page, run this branching sequence:

1. **Is this a project state update?** (goals changed, key decisions made, current status)
   → **`projects/`** page for the relevant project.

2. **Is this a relationship update?** (learned something about how to work with a person or team)
   → **`relationships/`** page.

3. **Is this a technique, recipe, or procedure?** (how to do something — steps, pitfalls, examples)
   → **`techniques/`** page.

4. **Is this a concept, fact, or domain mechanic?** (how something works, key facts, open questions)
   → **`domain/`** page.

5. **Is this a principle that would survive a complete change of codebase, technology, and project?**
   (Apply the test: "Would this principle still apply if everything else changed?")
   - Yes → **`identity.md`** Hard-Won Lessons, with a `See:` link to the domain/techniques page
     that holds the mechanics.
   - No → Back to step 3 or 4.

**Identity.md is the last branch, not the first.** If you find yourself going straight to
identity.md, pause and re-run the rubric from step 1.
```

### Step 5: Rewrite the "Triggers for wiki updates" block in Maintenance Workflow

**File:** `src/templates/entity/wiki_schema.md.jinja2`

**Target (current lines ~139–150):**
```markdown
**Triggers for wiki updates:**

- You encounter a new concept → create or update a `domain/` page
- You apply a technique → create or update a `techniques/` page
- You discover something was wrong → update the relevant page and add to `identity.md` Hard-Won Lessons
- You make a significant decision → update the relevant `projects/` page
- You learn something about how to work with someone → update their `relationships/` page
- A session ends → add a `log.md` entry
```

**Replace with:**
```markdown
**Triggers for wiki updates:**

- You encounter a new concept → create or update a `domain/` page
- You apply a technique → create or update a `techniques/` page
- You discover a mechanic was wrong → correct the `domain/` or `techniques/` page; only update
  `identity.md` if the **principle itself** changed (apply the routing test: codebase-independent?)
- You make a significant decision → update the relevant `projects/` page
- You learn something about how to work with someone → update their `relationships/` page
- A session ends → add a `log.md` entry
```

### Step 6: Add an "Identity.md Health Check" section

**File:** `src/templates/entity/wiki_schema.md.jinja2`

Insert a new `## Identity.md Health Check` section immediately after the `## Operations`
section (after the Lint block). This gives agents a periodic audit procedure.

```markdown
## Identity.md Health Check

Run this audit when `identity.md` Hard-Won Lessons exceeds 15 entries, or at the start of
a new major engagement:

1. For each Hard-Won Lessons entry, apply the routing test:
   *"Would this principle still apply if the codebase, technology, or project changed completely?"*
2. If **yes** — the entry belongs. Verify it has a `See:` link to any relevant mechanics page.
3. If **no** — the entry is a mechanic masquerading as a principle. Move the content to the
   appropriate `domain/` or `techniques/` page. Replace the entry with a one-line principle
   plus a `See:` link, or remove it entirely.
4. Target: **~8–15 entries** that are genuinely codebase-independent.

After the audit, update `index.md` if any pages were created or significantly changed.
```

### Step 7: Update the Page Operations table

**File:** `src/templates/entity/wiki_schema.md.jinja2`

**Target (current table):**
```markdown
| Situation | Action |
|-----------|--------|
| New distinct concept | Create a new page in the appropriate directory |
| Refinement, new example, corrected understanding | Update the existing page |
| Page exceeds ~500 words covering multiple separable concepts | Split into two pages, update index |
| Concept referenced from multiple places | Use wikilinks rather than duplicating content |
```

**Replace with:**
```markdown
| Situation | Action |
|-----------|--------|
| New distinct concept | Create a new page in the appropriate directory |
| Refinement, new example, corrected understanding | Update the existing page |
| Page exceeds ~500 words covering multiple separable concepts | Split into two pages, update index |
| Concept referenced from multiple places | Use wikilinks rather than duplicating content |
| identity.md Hard-Won Lessons entry fails the routing test | Move mechanics to domain/ or techniques/; replace with principle + `See:` link |
| identity.md Hard-Won Lessons exceeds 15 entries | Run the Identity.md Health Check |
```

### Step 8: Audit `identity.md.jinja2` and adjust the Hard-Won Lessons comment

**File:** `src/templates/entity/wiki/identity.md.jinja2`

The current comment in Hard-Won Lessons reads:
```
<!-- This section becomes your most valuable asset.
     Document failures, surprising discoveries, and corrected assumptions.
     Especially capture lessons from adversity — the things you learned the hard way.
     Update this throughout every session. -->
```

The phrase "Update this throughout every session" primes the section as a per-session
dump target. Replace with:

```
<!-- Principle-level lessons that would survive a complete change of codebase or project.
     Target ~8–15 entries. Each entry should end with: See: [[domain/page]] or [[techniques/page]]
     pointing to the mechanics page that holds the how-to details.
     Adding here should be RARE. If you are adding multiple entries per session,
     you are dumping mechanics — move them to domain/ or techniques/ instead. -->
```

### Step 9: Run existing tests to verify no regressions

```bash
uv run pytest tests/test_entities.py tests/test_entity_create_cli.py tests/test_entity_cli.py -v
```

These tests exercise `create_entity`, which renders both modified templates. A passing run
confirms the Jinja2 syntax is intact and templates render without error.

If any test fails, diagnose before proceeding. Template syntax errors (unclosed blocks,
malformed Jinja2 tags) are the most likely cause.

## Dependencies

None — this chunk only edits template files and requires no other chunk to be complete first.

## Risks and Open Questions

- **Preserving Jinja2 syntax**: The templates contain `{{ created }}`, `{{ role or "..." }}`
  substitutions. Edits must not break these. After each step, a quick `grep '{{' <file>` confirms
  variables are still intact.
- **Section ordering**: The new Decision Rubric and Health Check sections are inserted at
  specific positions. Verify the final document reads coherently end-to-end.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?
-->
