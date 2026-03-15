
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk modifies a single file: the `steward-setup.md.jinja2` Jinja2 template
that generates the `/steward-setup` slash command. No Python code changes are
required — the existing `ve board send` CLI (in `src/cli/board.py`) already
resolves `--swarm` and `--server` from `~/.ve/board.toml` via
`resolve_swarm()`/`resolve_server()` in `src/board/config.py`, so the template
only needs to instruct the agent to run the right commands.

The two enhancements are additive insertions into the template's instruction
flow:

1. **Auto-suggest defaults** — Before the interview section, add a step that
   reads `~/.ve/board.toml` (via `cat`) and extracts `default_swarm` and the
   corresponding `server_url`. These are presented as pre-filled defaults in the
   interview questions for swarm ID and server URL.

2. **Bootstrap channels** — After writing `STEWARD.md` and before the existing
   validation section, add a step that runs `ve board send` to both the steward
   channel and the changelog channel with bootstrap messages. This ensures the
   channels exist on the swarm before the first `ve board watch`.

Per DEC-005, the template does not prescribe git operations. Per the template
system subsystem, we edit the source template and re-render via `uv run ve init`.

**Testing**: This chunk modifies only a Jinja2 template (agent instructions in
markdown). Per `docs/trunk/TESTING_PHILOSOPHY.md`, we verify templates render
without error and files are created, but don't assert on template prose. The
existing template rendering tests already cover that `steward-setup.md.jinja2`
renders successfully. No new tests are needed — the success criteria are
verified by manual execution (running `/steward-setup` and confirming channels
exist and defaults are pre-filled).

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template
  system. We edit the Jinja2 source template and re-render via `ve init`,
  following the established template editing workflow.

## Sequence

### Step 1: Add auto-suggest defaults from board.toml

Edit `src/templates/commands/steward-setup.md.jinja2` to add a new section
before the interview questions. This section instructs the agent to:

1. Run `cat ~/.ve/board.toml` to read the board configuration
2. If the file exists and contains `default_swarm`, extract the swarm ID
3. Look up the corresponding `[swarms.<id>]` section for `server_url`
4. Store these as defaults to pre-fill interview questions 2 (swarm ID) and 6
   (server URL)
5. If the file doesn't exist or has no `default_swarm`, proceed normally
   (fall back to manual input with no errors)

Modify interview question 2 (Swarm ID) to say: "If a default was detected from
board.toml, present it as the default and let the operator confirm or override."

Modify interview question 6 (Server URL) similarly: "If a server_url was
detected from the default swarm's config, present it as the default."

Location: `src/templates/commands/steward-setup.md.jinja2`, within the
`{% raw %}` block.

### Step 2: Add bootstrap channel messages

In the same template file, add a new section between "Write the SOP" and
"Validate". This section instructs the agent to:

1. After writing `docs/trunk/STEWARD.md`, send a bootstrap message to the
   steward channel:
   ```
   ve board send <channel> "Steward channel bootstrapped." --swarm <swarm_id> [--server <url>]
   ```
2. Send a bootstrap message to the changelog channel:
   ```
   ve board send <changelog_channel> "Changelog channel bootstrapped." --swarm <swarm_id> [--server <url>]
   ```
3. If `ve board send` fails, surface the error to the operator — this likely
   means the swarm doesn't exist or the key is missing
4. The `--server` flag is only needed if the operator provided a non-default
   server URL

Location: `src/templates/commands/steward-setup.md.jinja2`, new subsection
after "### Write the SOP" and before "### Validate".

### Step 3: Re-render and verify

1. Run `uv run ve init` to re-render the template to
   `.claude/commands/steward-setup.md`
2. Read the rendered file and verify both new sections appear correctly
3. Confirm no other rendered files were unexpectedly changed

## Risks and Open Questions

- **board.toml format stability**: The `cat` + manual parsing approach in the
  template instructions is brittle if the TOML structure changes. However,
  there's no `ve board config show` command yet, and adding one is out of scope.
  The TOML is simple enough (flat `default_swarm` key, nested
  `[swarms.<id>].server_url`) that agent parsing is reliable.
- **Bootstrap message idempotency**: Sending to an already-existing channel is
  harmless — `ve board send` creates the channel on first use and appends on
  subsequent uses. Running `/steward-setup` twice won't cause problems.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->