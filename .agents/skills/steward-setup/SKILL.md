---
name: steward-setup
description: Set up a project steward via interactive interview
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->





## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Instructions

Set up a project steward by interviewing the operator to produce the steward's
Standard Operating Procedure document at `docs/trunk/STEWARD.md`.


### Prerequisites

The operator must have already created a swarm via `ve board swarm create`. The
swarm's private key should be stored in `~/.ve/keys/`. Swarm creation is NOT
part of this setup — only the SOP configuration is.

### Detect board defaults

Before starting the interview, check whether `~/.ve/board.toml` exists and
contains a default swarm configuration. This lets you pre-fill interview
answers.

1. Run `cat ~/.ve/board.toml` to read the board configuration
2. If the file exists and contains a `default_swarm` key, note the swarm ID
3. Look up the corresponding `[swarms.<id>]` section and extract `server_url`
   if present
4. Store the detected swarm ID and server URL as defaults for the interview

If the file does not exist or has no `default_swarm`, proceed normally — all
interview questions will require manual input and no error should be shown.

### Interview the operator

Walk through each of the following questions. Explain what each field means and
offer sensible defaults where applicable.

1. **Steward name** — A human-readable identifier for this steward.
   - Example: "Tool B Steward", "My Project Steward"
   - Convention: `<Project Name> Steward`

2. **Swarm ID** — Which swarm this steward belongs to. Help the operator
   identify their swarm:
   - If a default swarm was detected from `board.toml`, present it as the
     default and let the operator confirm or override
   - Otherwise, run `ls ~/.ve/keys/` to list available swarm key files
   - Run `ve board channels --swarm <id>` to verify the swarm exists
   - The operator should provide the swarm ID from their `ve board swarm create`
     output

3. **Channel name** — The inbound channel the steward will watch for messages.
   - Convention: `<project-name>-steward`
   - Example: `tool-b-steward`

4. **Changelog channel name** — Where the steward posts outcome summaries.
   - Convention: `<project-name>-changelog`
   - Example: `tool-b-changelog`

5. **Behavior mode** — How the steward responds to inbound messages. Explain
   each option and ask the operator to choose:
   - **`autonomous`**: The steward triages messages, acts on them (creates
     chunks, investigations, fixes code), and publishes results — all without
     human intervention.
   - **`queue`**: The steward creates work items (chunks, investigations) for
     human review but does not implement them. Results are posted to the
     changelog.
   - **`custom`**: The steward follows freeform instructions you provide. Choose
     this for arbitrary operator-defined behavior.

   If the operator chooses `custom`, capture their freeform instructions as
   markdown.

6. **Server URL** (optional) — If the swarm is hosted on a remote backend
   rather than `ws://localhost:8787`, ask the operator for the server URL and
   note it in the SOP prose body so `/steward-watch` can pass `--server`.
   - If a `server_url` was detected from the default swarm's config in
     `board.toml`, present it as the default and let the operator confirm or
     override

### Write the SOP

After collecting all answers, create `docs/trunk/STEWARD.md` with the following
structure:

```markdown
---
steward_name: "<name from interview>"
swarm: "<swarm_id>"
channel: "<channel-name>"
changelog_channel: "<changelog-channel-name>"
behavior:
  mode: <autonomous|queue|custom>
  custom_instructions: <markdown string if custom, null otherwise>
---

# <Steward Name>

<Brief prose summary of the steward's purpose for this project.>

## Behavior

<Describe the steward's behavior when messages arrive. Tailor this to the
chosen mode. For autonomous mode, use the template below as a starting point.
For queue or custom modes, adjust accordingly.>
```

#### Autonomous mode suggested behavior section

When the operator chooses `autonomous`, include a `## Behavior` section in the
SOP that describes the full chunk-and-changelog lifecycle. Use this as the
default content (adapt project-specific details):

```markdown
## Behavior

When a message arrives:

1. **Triage** — Determine whether the message is a bug report, change request,
   question, or something else.

2. **Create a FUTURE chunk** — For bug reports and change requests, create a
   chunk (`/chunk-create`) as FUTURE. Write only the goal — do NOT plan or
   implement. The orchestrator handles planning and implementation.

3. **Commit and inject** — Commit the chunk directory (both GOAL.md and
   PLAN.md) and inject it into the orchestrator (`ve orch inject <chunk>`).
   Never plan or implement chunks directly in the steward context — always
   delegate to the orchestrator. This protects the steward's context window
   from implementation noise.

4. **Monitor the orchestrator** — After injection, monitor orchestrator
   progress (`ve orch ps`). When a requested chunk completes, publish a
   changelog entry. When a chunk is stuck, investigate and resolve it
   autonomously (`/orchestrator-investigate`).

5. **Push completed work** — When a chunk finishes in the orchestrator, run
   `git push` to publish the merged work to the remote before posting the
   changelog entry.

6. **Deploy Durable Object worker** (conditional) — After pushing, check
   whether the completed chunk's `code_paths` (in its GOAL.md frontmatter)
   include files under `workers/`. If so, run
   `cd workers/leader-board && npm run deploy` and verify it succeeds. If
   the deploy fails, include the error in the changelog entry.

7. **Publish to changelog** — Write a concise summary of what was done and
   publish it to the changelog channel so the requester and any observers can
   see the outcome. Publish when:
   - A chunk finishes successfully (include what changed)
   - A stuck chunk is resolved (include what went wrong and how it was fixed)
   - A question is answered
```

#### Queue mode suggested behavior section

When the operator chooses `queue`, the behavior section should note that chunks
are created but NOT injected into the orchestrator — they are left as FUTURE
for the operator to review and schedule manually.

#### Notes section

```markdown
## Notes

<Any additional context from the interview, such as server URL, special
handling instructions, or project-specific conventions.>
```

### Bootstrap channels

After writing `STEWARD.md`, send bootstrap messages to ensure both channels
exist on the swarm before the first watch attempt.

1. Send a bootstrap message to the steward channel:
   ```
   ve board send <channel> "Steward channel bootstrapped." --swarm <swarm_id> [--server <url>]
   ```
2. Send a bootstrap message to the changelog channel:
   ```
   ve board send <changelog_channel> "Changelog channel bootstrapped." --swarm <swarm_id> [--server <url>]
   ```

The `--server` flag is only needed if the operator provided a non-default server
URL. If either `ve board send` command fails, surface the error to the
operator — this likely means the swarm doesn't exist or the key is missing.

### Validate

1. Verify the YAML frontmatter parses correctly by reading back the file
2. Confirm the swarm exists by running `ve board channels --swarm <swarm_id>`
3. Present the completed SOP to the operator for confirmation

### What's Next

Tell the operator:
- Use `/steward-watch` to start the steward's watch loop
- Other agents can send messages with `/steward-send`
- Observers can follow outcomes with `/steward-changelog`
- The SOP can be edited at any time — the steward re-reads it each iteration
