---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/commands/entity-episodic.md.jinja2
  - src/templates/commands/entity-startup.md.jinja2
code_references:
  - ref: src/templates/commands/entity-episodic.md.jinja2
    implements: "New skill template teaching agents episodic search usage, triggers, two-phase workflow, and caveats"
  - ref: src/templates/commands/entity-startup.md.jinja2
    implements: "Updated startup skill with Step 9 (episodic memory) inserted after touch protocol (renumbered from Step 7 by entity_startup_wiki which added Steps 5-6 for wiki orientation)"
narrative: null
investigation: entity_session_harness
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_episodic_search
created_after:
- entity_session_tracking
---


# Chunk Goal

## Minor Goal

Create an `/entity-episodic` slash command skill that teaches agents how and when to
use episodic memory search during a session. Also update the existing `/entity-startup`
skill to mention episodic search availability.

Without this skill, agents won't know the episodic search tool exists or how to use
it effectively. The skill bridges the gap between the tool being available and the
agent actually using it at the right moments.

### What to build

**1. New skill template** `src/templates/commands/entity-episodic.md.jinja2`:

The skill should teach agents:

**When to use episodic search vs entity memory recall:**
- Use `ve entity recall <name> <query>` when you need distilled knowledge — "what do I
  know about X?" These are lessons, skills, and principles extracted from prior sessions.
- Use `ve entity episodic --entity <name> --query "..."` when you need context about
  what happened — "when did I encounter X? what was the full conversation? what did the
  operator say about this?" These are raw session transcripts, not distilled.

**Common triggers for episodic search:**
- The operator references something from a prior session ("remember when we...")
- You're about to make a decision similar to one made before
- You encounter an error you think you've seen before
- You need to understand the context behind a core memory (why was it created?)
- The operator asks you to find a specific conversation or decision

**The two-phase workflow:**

Step 1 — Search: run `ve entity episodic --entity <name> --query "..."` to get ranked
snippets. Scan the results to identify which hits look relevant. Each result includes
a copy-pasteable expand command.

Step 2 — Expand: run `ve entity episodic --entity <name> --expand <session_id> --chunk <chunk_id> --radius 10`
to read the surrounding conversation. The hit region is marked with `>>>`, context
with spaces. Read the expanded context to understand:
- What led to this moment
- What correction or decision followed
- What the outcome was

**Practical examples in the skill:**

```
# "I think we had a similar merge conflict issue before"
ve entity episodic --entity steward --query "merge conflict orchestrator"

# "What did the operator say about how to handle chunk creation?"
ve entity episodic --entity steward --query "chunk creation SOP correction"

# "I'm seeing a WebSocket timeout — have we debugged this before?"
ve entity episodic --entity steward --query "websocket timeout reconnect"
```

**Important caveats to include:**
- Episodic search only covers sessions that were run through `ve entity claude`
  (which archives transcripts). Older sessions may not be available.
- The search is keyword-based (BM25), not semantic. Use specific terms from the
  domain rather than abstract concepts.
- Expanding a hit costs context window space. Be selective — expand the top 1-2
  results, not all of them.

**2. Update `/entity-startup` skill** (`src/templates/commands/entity-startup.md.jinja2`):

Add a new step after Step 6 (touch protocol) — Step 7: Episodic memory.

```
### Step 7: Episodic memory

You can search your prior session transcripts for specific events, conversations,
and decisions using episodic search:

    ve entity episodic --entity <name> --query "..."

Use this when you need context about what happened in a prior session, not just
the distilled lessons in your memory. Run /entity-episodic for detailed usage.
```

(Also renumber the current Step 7 "Restore active state" to Step 8.)

**3. Run `ve init`** to re-render the templates into `.claude/commands/`.

## Success Criteria

- `/entity-episodic` skill template exists and renders correctly via `ve init`
- The skill clearly explains when to use episodic vs memory recall
- The skill includes the two-phase search→expand workflow with concrete examples
- `/entity-startup` mentions episodic search availability after the touch protocol step
- Both rendered commands appear in `.claude/commands/` after `ve init`
- The skill uses `uv run ve entity episodic` when in the vibe-engineer source repo (matching the pattern in entity-startup.md.jinja2)