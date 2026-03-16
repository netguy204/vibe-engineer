

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add a "Cross-project messaging" subsection to the Steward section of the CLAUDE.md
Jinja2 template (`src/templates/claude/CLAUDE.md.jinja2`). This is a documentation-only
change to the template — no Python code changes are needed.

The new subsection will be inserted directly after the steward command list and before
the `## Creating Artifacts` section. It explains the channel naming convention
(`<target-project>-steward`), the send command format, and explicitly warns against the
common mistake of sending to your own project's steward channel when you intend to
address a different project's steward.

After editing the template, run `ve init` to re-render and verify the output.

Per docs/trunk/TESTING_PHILOSOPHY.md, template prose content is not tested for exact
wording ("We verify templates render without error and files are created, but don't
assert on template prose"). The existing `test_init.py` tests already verify that
`ve init` renders CLAUDE.md successfully. No new tests are needed for this change.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system.
  The edit follows the established pattern: modify the `.jinja2` source template, then
  re-render with `ve init`. No deviation from the subsystem's invariants.

## Sequence

### Step 1: Add cross-project messaging guidance to the CLAUDE.md template

Edit `src/templates/claude/CLAUDE.md.jinja2` to insert a new subsection after the
steward command list (after the `/swarm-monitor` line) and before the `## Creating
Artifacts` section.

The new content should include:

1. A Jinja2 chunk backreference comment for this chunk
2. A `#### Cross-project messaging` heading (h4, since it's under `### Steward` which is h3)
3. An explanation of the naming convention: the channel name is `<target-project>-steward`,
   where `<target-project>` is the project whose steward you're addressing — NOT the
   project you're sending from
4. The send command: `ve board send <target-project>-steward "<message>" --swarm <swarm_id>`
5. A concrete example: "To tell the vibe-engineer steward from any project, send to
   `vibe-engineer-steward`"
6. An explicit warning about the common mistake: agents may find their local
   `STEWARD.md` and send to their own project's steward channel instead of the
   target project's channel

Location: `src/templates/claude/CLAUDE.md.jinja2`, lines 138-139 (between the
`/swarm-monitor` entry and the `## Creating Artifacts` section)

### Step 2: Re-render and verify

Run `uv run ve init` to re-render the CLAUDE.md from the updated template.

Verify that:
- The rendered CLAUDE.md contains the new "Cross-project messaging" subsection
- The subsection appears within the Steward section
- The `VE:MANAGED:START` / `VE:MANAGED:END` markers still wrap the content correctly

### Step 3: Run existing tests

Run `uv run pytest tests/test_init.py` to confirm the template still renders without
errors and the existing init tests pass.

## Risks and Open Questions

- The `/steward-send` command template already contains channel resolution logic
  (reading `STEWARD.md` frontmatter for `channel` and `swarm`). The CLAUDE.md guidance
  is complementary — it helps agents form the correct intent before invoking the command.
  There is no conflict, but the two sources of truth should stay consistent.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->