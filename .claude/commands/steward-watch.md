---
description: Run the steward watch-respond-rewatch loop
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->



## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Instructions

Run the steward's watch-respond-rewatch loop. This is the core steward
lifecycle — the agent watches for inbound messages, triages them according to
the SOP, acts, posts outcomes, and rewatches.


### Step 1: Read the SOP

Read `docs/trunk/STEWARD.md` and parse the YAML frontmatter to extract:

- `swarm` — the swarm ID
- `channel` — the inbound channel to watch
- `changelog_channel` — where to post outcomes
- `behavior.mode` — `autonomous`, `queue`, or `custom`
- `behavior.custom_instructions` — freeform instructions (if mode is `custom`)

Also check the prose body for a server URL. If one is noted, use
`--server <url>` on all `ve board` commands.

If `docs/trunk/STEWARD.md` does not exist, tell the operator to run
`/steward-setup` first and stop.

### Step 2: Start the watch

Run `ve board watch <channel> --swarm <swarm_id>` using `run_in_background`.
This command blocks until a message arrives on the channel.

**Important:** Before starting the watch, note the current cursor position.
The cursor file is at `.ve/board/cursors/<channel>.cursor` (project-local).
Read it to get the current position N. If the file doesn't exist, the cursor
is at position 0. The next received message will be at position N+1 — you'll
need this for the ack step.

Example:
```
# Read current cursor position (may not exist yet — that's OK, treat as 0)
cat .ve/board/cursors/<channel>.cursor 2>/dev/null || echo 0

# Start watching in the background
ve board watch <channel> --swarm <swarm_id>
```

### Step 3: Receive and triage

When the background watch returns, it outputs the decrypted message plaintext
to stdout. Read the output and triage according to the SOP's behavior mode:

**If mode is `autonomous`:**
- Analyze the inbound message to understand the request
- Create a FUTURE chunk or investigation as appropriate (`/chunk-create`,
  `/investigation-create`). Write only the goal — do NOT plan or implement.
- Commit the chunk directory (both GOAL.md and PLAN.md)
- Inject into the orchestrator (`ve orch inject <chunk>`). The orchestrator
  handles planning and implementation autonomously.
- Summarize the outcome for the changelog

**If mode is `queue`:**
- Analyze the inbound message to understand the request
- Create a FUTURE chunk or investigation documenting the work item.
  Write only the goal — do NOT plan or implement.
- Commit the chunk directory (both GOAL.md and PLAN.md)
- Do NOT inject — leave it for the human operator to schedule
- Summarize what was queued for the changelog

**If mode is `custom`:**
- Follow the `custom_instructions` from the SOP frontmatter
- The instructions are freeform markdown — interpret and execute them
- Summarize the outcome for the changelog

### Step 4: Post outcome to changelog

After processing the message, post an outcome summary to the changelog channel:

```
ve board send <changelog_channel> "<outcome summary>" --swarm <swarm_id>
```

The outcome summary should be concise but informative — what was received, what
action was taken, and what the result was.

### Step 5: Ack to advance cursor

After durable processing is complete (the work is done and the changelog entry
is posted), acknowledge the message to advance the cursor:

```
ve board ack <channel> <position>
```

Where `<position>` is N+1 (the cursor position you noted in Step 2, plus one).

**Critical:** Do NOT ack before processing is complete. The cursor is the
steward's recovery mechanism — if the agent crashes, it will re-read from the
last acked position on restart, automatically re-processing the unfinished
message.

### Step 6: Check orchestrator progress

Before rewatching, check the status of any chunks the steward has injected.
Keep a running list of injected chunk names throughout the session.

```
ve orch ps
```

For each injected chunk, check its status:

- **DONE** — The orchestrator completed the chunk. Post a changelog entry
  announcing the completion (include the chunk name and what it accomplished).
  Remove it from your tracking list.
- **RUNNING** — Still in progress. No action needed.
- **NEEDS_ATTENTION** — The chunk is stuck. Run `/orchestrator-investigate` to
  diagnose and resolve it. Post a changelog entry with what went wrong and how
  it was fixed (or that it's being investigated).
- **FAILED** — Post a failure summary to the changelog so the requester knows.

This step is critical — without it, the requester never learns that their
work was completed. The steward is the bridge between the orchestrator's
async execution and the human-visible changelog.

### Step 7: Re-read SOP and rewatch

The operator may edit the SOP while the steward is running to change behavior.
Before starting the next watch iteration:

1. **Re-read `docs/trunk/STEWARD.md`** — parse the frontmatter again to pick
   up any changes to behavior mode, channels, or custom instructions.

2. **Start the next watch** — Go back to Step 2 and repeat the loop.

This creates a continuous watch-respond-rewatch cycle. The steward runs
autonomously until the agent session ends.

### Key Concepts

- **`run_in_background`** is how the agent waits asynchronously for messages.
  Do NOT poll. The watch command blocks until a message arrives.
- **Cursor management** is manual. The watch command does NOT auto-advance the
  cursor. You must ack explicitly after processing.
- **Crash recovery** is automatic. On restart, re-running `/steward-watch`
  picks up from the last acked position — the unprocessed message will be
  re-delivered.
- **SOP re-read** each iteration allows the operator to dynamically change
  steward behavior without restarting.

### Error Handling

- If `ve board watch` fails (e.g., network error), wait briefly and retry.
  Do NOT ack — the message was not received.
- If processing fails (e.g., chunk creation error), still post a failure
  summary to the changelog, then ack. The operator can see the failure and
  resend the message if needed.
- If `ve board send` to the changelog fails, retry once. If it still fails,
  proceed with ack — the work was done even if the notification failed.
