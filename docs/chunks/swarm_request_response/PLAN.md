

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Create a new `/swarm-request-response` slash command skill that encapsulates the
full request-response lifecycle over swarm channel pairs. The skill is a Jinja2
template (like all other skills per the template_system subsystem) that renders
to `.claude/commands/swarm-request-response.md`.

The skill is purely agent instructions — no Python runtime code is needed. It
orchestrates existing `ve board` CLI primitives (`channels`, `watch`, `send`,
`ack`) into a safe, race-free request-response pattern. The key insight is
ordering: the response channel watch must start *before* the request is sent,
using `--offset` to skip historical messages and `run_in_background` to avoid
blocking.

This follows the same pattern as existing skills (`steward-watch`,
`steward-changelog`, `swarm-monitor`) — a Jinja2 template in
`src/templates/commands/` that gets rendered by `ve init` into
`.claude/commands/`. Registration happens in the CLAUDE.md Jinja2 template.

Per DEC-005, the skill does not prescribe git operations.

Testing: This chunk produces a template file (agent instructions in markdown),
not executable Python code. Per TESTING_PHILOSOPHY.md, we don't test template
prose content. The meaningful verification is that the template renders without
error and produces a file — this is already covered by the existing `ve init`
test infrastructure. No new test file is needed.

## Subsystem Considerations

- **docs/subsystems/template_system** (DOCUMENTED): This chunk USES the template
  system to create and render the new skill template. The new template follows
  the established pattern: Jinja2 source in `src/templates/commands/`, frontmatter
  with `description`, includes for `auto-generated-header` and `common-tips`
  partials, `{% raw %}` block for instruction content.

## Sequence

### Step 1: Create the skill template

Create `src/templates/commands/swarm-request-response.md.jinja2` with the full
request-response pattern instructions.

**Template structure** (follows existing skill conventions):
- YAML frontmatter with `description`
- `{% set source_template %}` and `{% include %}` for header/tips partials
- Chunk backreference comment
- `{% raw %}` block containing all agent instructions

**Instruction content — the request-response lifecycle:**

#### Phase 1: Parse arguments

Accept from `$ARGUMENTS`:
- **Request channel** — where to send the request (e.g., `myproject-steward`)
- **Response channel** — where to watch for the response (e.g., `myproject-changelog`)
- **Message body** — the request content
- **Swarm ID** — which swarm to use (optional if default is configured)
- **Server URL** — optional, for non-default backends

If the operator provides a project name instead of explicit channels, derive the
channel pair using the standard convention: `<project>-steward` (request) and
`<project>-changelog` (response).

#### Phase 2: Advance response channel cursor to head

Query current channel state:
```
ve board channels [--swarm <swarm_id>] [--server <url>]
```

Parse the `head=<N>` value for the response channel. This is the position we'll
start watching from — it skips all historical messages so we only see responses
that arrive *after* we start.

If the response channel doesn't exist yet in the output, warn the operator and
proceed (the steward may create it on first response).

#### Phase 3: Start watching response channel in background

Start the watch *before* sending the request. This prevents the race condition
where the steward responds before we're listening:

```
ve board watch <response_channel> --offset <head_position> --swarm <swarm_id>
```

Run with `run_in_background`. The `--offset` flag starts from the head position
(ephemeral, does not modify the persisted cursor). Record the task ID for later
`TaskStop` if needed.

**Watch safety:** Per existing conventions, there must be only one watch per
channel. If the agent is already watching the response channel from a previous
invocation, `TaskStop` the previous watch first.

#### Phase 4: Send the request

Now that the watch is active, send the request:

```
ve board send <request_channel> "<message>" --swarm <swarm_id>
```

Report the assigned position to the caller.

#### Phase 5: Receive and filter response

When the background watch returns a message, the agent must determine if it's
actually a response to this specific request. The response channel is a broadcast
channel — it may contain notifications from other requests or unrelated activity.

**Filtering heuristic:** The agent should use its judgment to assess relevance.
Signals include:
- Temporal proximity — the response arrived shortly after the request
- Content correlation — the response references or addresses the request topic
- Explicit acknowledgment — the response quotes or names the request

**If the message is NOT relevant:**
1. Ack the response channel to advance past this message:
   ```
   ve board ack <response_channel>
   ```
2. Re-launch the watch in background (same `--offset` is not needed now — the
   persisted cursor has advanced via ack):
   ```
   ve board watch <response_channel> --swarm <swarm_id>
   ```
3. Continue waiting.

**If the message IS relevant:**
1. Return the response content to the caller
2. Ack the response channel:
   ```
   ve board ack <response_channel>
   ```
3. Report success: what was sent, what was received, and on which channels.

#### Key Concepts section

Document these important concepts at the end of the skill:
- **Why watch-before-send matters** — prevents the race condition where the
  steward responds before the watch starts, causing the response to be missed
- **`--offset` vs persisted cursor** — offset is ephemeral and used only for
  the initial watch to skip history; subsequent re-watches (after acking
  irrelevant messages) use the persisted cursor naturally
- **Channel pair convention** — `<project>-steward` / `<project>-changelog` is
  the standard pair, but any two channels work
- **Broadcast channel filtering** — the response channel is shared; not every
  message is a response to your request
- **Manual cursor management** — this skill uses `ve board ack` explicitly
  (like `/steward-watch`), not auto-advancing cursors (like `/swarm-monitor`)

Location: `src/templates/commands/swarm-request-response.md.jinja2`

### Step 2: Register the skill in CLAUDE.md template

Add `/swarm-request-response` to the Available Commands section of
`src/templates/claude/CLAUDE.md.jinja2`, in the Steward subsection alongside
the other swarm/steward skills. Add a chunk backreference comment.

The entry should appear after `/swarm-monitor`:

```
- `/swarm-request-response` - Send a request and wait for the response on a channel pair
```

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 3: Render and verify

Run `uv run ve init` to render the new template. Verify:
- `.claude/commands/swarm-request-response.md` is created
- The rendered file contains the auto-generated header
- The CLAUDE.md file includes the new command listing
- The rendered content matches the template intent

Run `uv run pytest tests/` to ensure no existing tests break.

## Dependencies

All dependencies are already satisfied by the `created_after` chunks:
- `board_watch_safety` — watch safety (PID-based kill, single watch per channel)
- `board_watch_offset` — `--offset` flag for ephemeral cursor override
- `board_channel_delete` — `ve board channels` command for querying head positions

## Risks and Open Questions

- **Response filtering is heuristic, not deterministic.** The agent must use
  judgment to decide if a message on the response channel is relevant to the
  original request. This is intentional — the channel model is broadcast, and
  deterministic correlation would require protocol-level request IDs that don't
  exist. The skill documents this explicitly and provides filtering guidance.
- **Watch timeout.** If the steward takes a long time to respond, the
  background watch may hit Claude Code's task timeout (exit 144). The skill
  should mention this possibility and suggest re-launching the watch if it
  times out without a response.
- **Head position race.** Between querying `ve board channels` and starting the
  watch with `--offset`, a message could arrive on the response channel. This
  is acceptable — it would be a message from *before* our request, so filtering
  it out is correct behavior.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->