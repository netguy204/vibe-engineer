

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk is pure template authoring — no Python logic, no CLI changes. We
create one new Jinja2 skill template and update an existing one, then re-render
both via `uv run ve init`.

The new `/entity-episodic` skill follows the same structural conventions as
`entity-startup.md.jinja2` and `entity-shutdown.md.jinja2`:
- Frontmatter with `description`
- `{% set source_template = ... %}` + auto-generated-header partial
- A backreference comment linking to this chunk
- `{% include "partials/common-tips.md.jinja2" %}`
- Content wrapped in `{% raw %}` / `{% endraw %}` to prevent Jinja2 from
  processing the command examples

The update to `/entity-startup` is minimal: insert a new Step 7 block after
the touch protocol step, and renumber the old Step 7 ("Restore active state")
to Step 8.

No new decisions are required — this chunk is purely documentation/skill
scaffolding.

## Subsystem Considerations

No subsystems are relevant to this chunk. The template command system is a
well-understood pattern; this chunk uses it but doesn't modify its
infrastructure.

## Sequence

### Step 1: Update `code_paths` in GOAL.md

Update the chunk's GOAL.md frontmatter to list the files this chunk touches:

```yaml
code_paths:
  - src/templates/commands/entity-episodic.md.jinja2
  - src/templates/commands/entity-startup.md.jinja2
```

### Step 2: Create `src/templates/commands/entity-episodic.md.jinja2`

Create the new skill template. It must include:

**Frontmatter** (YAML):
```yaml
description: Search prior session transcripts for specific events, conversations, and decisions
```

**Template preamble** (before `{% raw %}`):
```jinja2
{% set source_template = "entity-episodic.md.jinja2" %}
{% include "partials/auto-generated-header.md.jinja2" %}
{# Chunk: docs/chunks/entity_episodic_skill - Episodic memory search skill #}

## Tips

{% include "partials/common-tips.md.jinja2" %}
```

**Content** (inside `{% raw %}` / `{% endraw %}`):

The skill should cover these sections in order:

1. **When to use episodic vs memory recall** — a clear two-line contrast:
   - `ve entity recall <name> <query>` → distilled knowledge, lessons, skills,
     principles. "What do I know about X?"
   - `ve entity episodic --entity <name> --query "..."` → raw session history,
     conversations, decisions in context. "When did I encounter X? What did
     the operator say? What was the outcome?"

2. **Common triggers for episodic search** (bulleted list):
   - Operator references a prior session ("remember when we...")
   - About to make a decision similar to one made before
   - Encountered an error you think you've seen before
   - Need context behind a core memory (why was it created?)
   - Operator asks you to find a specific conversation or decision

3. **Two-phase workflow**:

   *Step 1 — Search*: Run `ve entity episodic --entity <name> --query "..."` to
   get ranked snippets. Scan the results to identify which hits look relevant.
   Each result includes a copy-pasteable expand command.

   If working in the vibe-engineer source repo, use `uv run`:
   ```
   uv run ve entity episodic --entity <name> --query "..."
   ```

   *Step 2 — Expand*: Run the expand command from the search output to read
   surrounding conversation context:
   ```
   ve entity episodic --entity <name> --expand <session_id> --chunk <chunk_id> --radius 10
   ```
   The hit region is marked with `>>>`, context lines with spaces. Read the
   expanded output to understand:
   - What led to this moment
   - What correction or decision followed
   - What the outcome was

   Be selective — expand the top 1–2 results, not all of them. Each expansion
   costs context window space.

4. **Practical examples**:
   ```
   # "I think we had a similar merge conflict issue before"
   ve entity episodic --entity steward --query "merge conflict orchestrator"

   # "What did the operator say about how to handle chunk creation?"
   ve entity episodic --entity steward --query "chunk creation SOP correction"

   # "I'm seeing a WebSocket timeout — have we debugged this before?"
   ve entity episodic --entity steward --query "websocket timeout reconnect"
   ```

5. **Important caveats**:
   - Episodic search only covers sessions run through `ve entity claude` (which
     archives transcripts). Older sessions may not be indexed.
   - The search is keyword-based (BM25), not semantic. Use specific terms from
     the domain rather than abstract concepts.
   - Expanding a hit costs context window space. Be selective.

### Step 3: Update `src/templates/commands/entity-startup.md.jinja2`

Insert a new Step 7 block immediately after the existing Step 6 ("Follow the
touch protocol") and before the current Step 7 ("Restore active state"). Then
renumber the existing Step 7 to Step 8.

The new Step 7 to insert:

```
### Step 7: Episodic memory

You can search your prior session transcripts for specific events, conversations,
and decisions using episodic search:

    ve entity episodic --entity <name> --query "..."

Use this when you need context about what happened in a prior session, not just
the distilled lessons in your memory. Run /entity-episodic for detailed usage.
```

After the insert, the original Step 7 heading becomes:

```
### Step 8: Restore active state
```

### Step 4: Re-render templates via `ve init`

Run:
```
uv run ve init
```

This re-renders all templates in `src/templates/commands/` into
`.claude/commands/`. Verify:
- `.claude/commands/entity-episodic.md` exists and contains the rendered skill
- `.claude/commands/entity-startup.md` contains the new Step 7 and the
  renumbered Step 8

### Step 5: Validate rendered output

Spot-check both rendered files:
- `entity-episodic.md` should open with the auto-generated header and contain
  the two-phase workflow instructions
- `entity-startup.md` should show Steps 1–8 with Step 7 being "Episodic memory"
  and Step 8 being "Restore active state"

No tests are needed for this chunk — the content is documentation, not logic.
The success criteria from GOAL.md are verified by reading the rendered output.

## Dependencies

- `entity_episodic_search` must be ACTIVE (it is — the `ve entity episodic`
  CLI command the skill teaches must exist before the skill is useful). ✓

## Risks and Open Questions

- The `partials/common-tips.md.jinja2` and `partials/auto-generated-header.md.jinja2`
  includes must be confirmed to exist before referencing them. Verify by reading
  another entity template and following its include paths.
- The `{% raw %}` / `{% endraw %}` wrapper is required because the template
  examples contain `{{ }}` and `{% %}` syntax that Jinja2 would try to process.
  Confirm the existing entity templates use this pattern before copying it.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
