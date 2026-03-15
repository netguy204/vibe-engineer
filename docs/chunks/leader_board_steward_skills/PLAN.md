# Implementation Plan

## Approach

Create four Jinja2 command templates in `src/templates/commands/` that teach
Claude Code agents the steward workflow patterns. These templates follow the
established pattern used by all other slash commands: YAML frontmatter with a
`description` field, include of `partials/auto-generated-header.md.jinja2` and
`partials/common-tips.md.jinja2`, task-context conditional blocks, and
`$ARGUMENTS` placeholder where the command accepts operator input.

Each skill is a **prose document** — it instructs the agent *how* to accomplish
a workflow using existing `ve board` CLI commands (from the `leader_board_cli`
chunk). The skills do not contain executable code; they teach the agent the
correct sequence of CLI invocations, cursor management, SOP-driven triage, and
`run_in_background` looping patterns.

After creating the templates, register the four skills in the CLAUDE.md Jinja2
template so that agents (and the skill system) can discover them.

**Key patterns used:**
- Template rendering via `ve init` (per DEC-001 / template_system subsystem)
- Steward SOP format defined in SPEC.md §Steward SOP Document Format
- `ve board` CLI commands: `send`, `watch`, `ack`, `channels`
- Claude Code's `run_in_background` for async watch loops
- No git operations prescribed in templates (per DEC-005)

**Testing strategy:** Per TESTING_PHILOSOPHY.md, we don't test template prose
content. We verify that templates render without error and that `ve init`
produces the expected files in `.claude/commands/`. The existing `test_init.py`
pattern covers this — we add a test that confirms all four steward command
files are rendered by `ve init`.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template
  system to render command templates via `ve init`. We follow the established
  collection/template/partial pattern. No deviations from the subsystem's
  patterns are expected.

## Sequence

### Step 1: Create `/steward-setup` template

Create `src/templates/commands/steward-setup.md.jinja2`.

This skill walks the agent through an interactive interview with the operator
to produce `docs/trunk/STEWARD.md`. The interview captures:

1. **Steward name** — human-readable identifier (e.g., "Tool B Steward")
2. **Swarm ID** — which swarm to use. The agent should run `ve board channels
   --swarm <id>` or check `~/.ve/keys/` to help the operator identify their
   swarm. The swarm must already exist (created via `ve board swarm create`).
3. **Channel name** — the inbound channel the steward watches (e.g.,
   `tool-b-steward`). Convention: `<project-name>-steward`.
4. **Changelog channel name** — where the steward posts outcomes (e.g.,
   `tool-b-changelog`). Convention: `<project-name>-changelog`.
5. **Behavior mode** — one of `autonomous`, `queue`, or `custom`. The agent
   explains each mode and asks the operator to choose. If `custom`, capture
   freeform instructions.

The agent then writes `docs/trunk/STEWARD.md` with the YAML frontmatter
matching the SPEC.md §Steward SOP Document Format, plus a prose body
summarizing the steward's purpose. The template must NOT prescribe git
operations (DEC-005).

**Template structure:**
- YAML frontmatter: `description: "Set up a project steward..."`
- Include auto-generated header and common tips partials
- Task context conditional (not applicable here, but include for consistency)
- `$ARGUMENTS` is not needed — this is a guided interview, not argument-driven
- Instructions: phased interview → validate swarm exists → write SOP → confirm

Location: `src/templates/commands/steward-setup.md.jinja2`

### Step 2: Create `/steward-watch` template

Create `src/templates/commands/steward-watch.md.jinja2`.

This is the most complex skill. It teaches the agent the watch-respond-rewatch
loop using `run_in_background`. The instructions must cover:

1. **Read the SOP** — Load `docs/trunk/STEWARD.md`, parse frontmatter to get
   `swarm`, `channel`, `changelog_channel`, and `behavior`.
2. **Start the watch** — Run `ve board watch <channel> --swarm <swarm_id>` via
   `run_in_background`. This blocks until a message arrives.
3. **Receive and triage** — When the background watch returns plaintext, the
   agent triages the message according to the SOP's behavior mode:
   - `autonomous`: Create chunk/investigation, implement fix, publish results
   - `queue`: Create chunk/investigation documenting the work item, do not
     implement
   - `custom`: Follow `custom_instructions` from the SOP
4. **Post outcome to changelog** — Run
   `ve board send <changelog_channel> "<outcome summary>" --swarm <swarm_id>`
   to notify observers.
5. **Ack to advance cursor** — Run
   `ve board ack <channel> <position>` after durable processing.
   The position comes from the watch output (the agent needs to capture it).
   **Critical**: The watch command prints decrypted plaintext to stdout. The
   agent must also note the position from the message for ack. Since `watch`
   only prints plaintext, the agent should use `ve board watch` which returns
   a single message — the position is implicit (cursor + 1) or the agent reads
   the cursor file before and after. The skill should instruct the agent to
   load the current cursor, add 1, and that's the position to ack.
6. **Re-read SOP and rewatch** — Loop: re-read the SOP (operator may have
   edited it), then start another `run_in_background` watch.

**Key details the template must teach:**
- The watch command does NOT auto-advance the cursor — the agent must ack
- `run_in_background` is the mechanism for async waiting (not polling)
- The agent re-reads the SOP each iteration (allows dynamic behavior changes)
- Crash recovery: on restart, the cursor is at the last acked position, so
  the agent automatically re-processes the last unacked message

Location: `src/templates/commands/steward-watch.md.jinja2`

### Step 3: Create `/steward-send` template

Create `src/templates/commands/steward-send.md.jinja2`.

This skill teaches the agent how to send a message to a steward's channel from
any context. It accepts `$ARGUMENTS` as the target and message.

Instructions:
1. **Parse arguments** — Extract the target project/steward identifier and
   message body from `$ARGUMENTS`.
2. **Resolve the channel** — The agent needs the target steward's swarm ID
   and channel name. Options:
   - If the operator provides a channel name and swarm ID directly, use those.
   - If the operator names a project, the agent should check if that project
     has a `docs/trunk/STEWARD.md` accessible (e.g., via external artifact
     references or operator guidance).
3. **Send the message** — Run
   `ve board send <channel> "<message>" --swarm <swarm_id>`
4. **Confirm** — Report the position returned by the send command.
5. **Optionally watch changelog** — Suggest the operator can use
   `/steward-changelog` to watch for the steward's response.

Location: `src/templates/commands/steward-send.md.jinja2`

### Step 4: Create `/steward-changelog` template

Create `src/templates/commands/steward-changelog.md.jinja2`.

This skill teaches the agent how to watch a project's changelog channel with
the requester's own independent cursor. Used to close the loop after sending
a message to a steward.

Instructions:
1. **Identify the changelog channel** — From `$ARGUMENTS` or by reading the
   local project's `docs/trunk/STEWARD.md` if available, or the operator
   provides the channel name and swarm ID.
2. **Watch with the requester's cursor** — Run
   `ve board watch <changelog_channel> --swarm <swarm_id>` via
   `run_in_background`. The cursor is project-local, so each requester
   independently tracks their position on the changelog.
3. **Display the message** — When the watch returns, display the changelog
   entry to the operator.
4. **Ack and optionally rewatch** — Ack the cursor, then offer to continue
   watching for more updates.

Location: `src/templates/commands/steward-changelog.md.jinja2`

### Step 5: Register skills in CLAUDE.md template

Add the four steward skills to the "Available Commands" section in
`src/templates/claude/CLAUDE.md.jinja2`. Add them in a new "Steward" group
after the existing commands:

```
- `/steward-setup` - Set up a project steward via interactive interview
- `/steward-watch` - Run the steward watch-respond-rewatch loop
- `/steward-send` - Send a message to a project's steward
- `/steward-changelog` - Watch a project's changelog channel
```

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 6: Test that `ve init` renders the steward templates

Add a test in `tests/test_init.py` (or a new `tests/test_steward_skills.py`
if the existing file is already large) that:

1. Runs `ve init` in a temporary project directory
2. Asserts that `.claude/commands/steward-setup.md` exists
3. Asserts that `.claude/commands/steward-watch.md` exists
4. Asserts that `.claude/commands/steward-send.md` exists
5. Asserts that `.claude/commands/steward-changelog.md` exists
6. Asserts each file contains the auto-generated header (confirming template
   rendering worked)

Per TESTING_PHILOSOPHY.md: we verify the files are created and rendered, not
the prose content.

### Step 7: Verify end-to-end with `ve init`

Run `uv run ve init` in the worktree to confirm the templates render without
Jinja2 errors and produce the expected files. Verify the CLAUDE.md output
includes the new steward commands in the Available Commands section.

---

**BACKREFERENCE COMMENTS**

All four template files should include a module-level backreference:
```
# Chunk: docs/chunks/leader_board_steward_skills - Steward skill templates
```

This is placed as a Jinja2 comment (`{# ... #}`) at the top of each template
(after the frontmatter), following the pattern used by other command templates.

## Dependencies

- **leader_board_cli** (chunk): Must be complete. The steward skills reference
  `ve board send`, `ve board watch`, `ve board ack`, and `ve board channels`
  commands implemented by that chunk.
- **leader_board_spec** (chunk): The SPEC.md §Steward SOP Document Format
  defines the schema for `docs/trunk/STEWARD.md` that `/steward-setup`
  produces.

## Risks and Open Questions

- **Position tracking in watch loop**: The `ve board watch` command prints
  decrypted plaintext to stdout but doesn't print the message position. The
  steward-watch skill needs to teach the agent to derive the position for ack.
  The simplest approach: read the cursor file before watching (it's at the last
  acked position N), then the received message is at position N+1. If the watch
  command is later updated to include position in output, the skill can be
  simplified. Document this workaround in the template.
- **Server URL configuration**: The `ve board` commands default to
  `ws://localhost:8787`. The steward skills should teach agents to use `--server`
  if the swarm is on the hosted backend. Consider whether the SOP should include
  a `server` field — currently the SPEC doesn't include one, so the agent would
  need to infer it or the operator must provide it. For now, the skills can note
  this as optional and suggest the operator add it to the SOP prose body.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->