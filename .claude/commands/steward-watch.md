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

**Single watch only.** There must be exactly ONE watch per channel at any time.
Before starting a new watch, stop any previous watch background task using
`TaskStop`. Running multiple concurrent watches on the same channel causes
cursor confusion — both watches consume from the same cursor position, leading
to missed or double-processed messages. Track the current watch task ID and
stop it explicitly before starting the next one.

**OS-level safety net.** The `ve board watch` command now automatically
kills any existing watch process on the same channel before starting.
However, you should still explicitly stop previous background tasks via
`TaskStop` — the PID-based kill is a fallback for zombie processes that
survive task termination, not a replacement for clean task lifecycle
management.

Example:
```
# Stop previous watch if one exists
# TaskStop(task_id="<previous_watch_task_id>")

# Start watching in the background
ve board watch <channel> --swarm <swarm_id>
# Record the returned task ID — you'll need it to stop this watch later
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
ve board ack <channel>
```

The ack command auto-increments the cursor by 1 — no position argument needed.

**Critical:** Do NOT ack before processing is complete. The cursor is the
steward's recovery mechanism — if the agent crashes, it will re-read from the
last acked position on restart, automatically re-processing the unfinished
message.

**Every message must be acked.** This includes messages that don't produce
actionable work — bootstrap/initialization messages, questions answered inline,
no-ops, and duplicates. The ack advances the cursor past the message. Without it,
the cursor stays in place and the next watch cycle re-delivers the same message,
causing the steward to loop on it indefinitely.

### Step 6: Start orchestrator monitor

After injecting a chunk, set up a recurring monitor using `/loop` so the
steward can track orchestrator progress **concurrently** with the blocking
channel watch. This is critical — without it, the requester never learns
that their work was completed.

Use `/loop 5m` with a prompt that:

1. Runs `ve orch ps` and checks the status of all injected chunks
2. For **DONE** chunks:
   a. **Check for worker changes** — Read the completed chunk's `GOAL.md`
      frontmatter and inspect its `code_paths` list. If any path starts with
      `workers/`, a Durable Object deploy is needed.
   b. **Deploy conditionally** — If worker paths were found, run
      `cd workers/leader-board && npm run deploy` and verify the command exits
      0. If the deploy fails, include the failure details in the changelog
      entry but do not block — proceed to the next sub-step.
   c. **Post a changelog entry** announcing the completion (include the chunk
      name and what it accomplished).
   d. **Remove the chunk** from the monitoring prompt.
3. For **NEEDS_ATTENTION** chunks — alerts the operator or runs
   `/orchestrator-investigate` to diagnose and resolve
4. For **RUNNING** chunks — takes no action
5. For **FAILED** chunks — posts a failure summary to the changelog

Example `/loop` prompt:
```
/loop 5m Check orchestrator status for injected chunks: run `ve orch ps`
and look for `<chunk_name>`. If DONE, post a changelog entry via
`ve board send <changelog_channel> "<summary>" --swarm <swarm_id>`.
If NEEDS_ATTENTION, alert me. If RUNNING, no action needed.
```

When new chunks are injected during the session, cancel the existing loop
(CronDelete) and create a new one that monitors all active chunks.

The steward is the bridge between the orchestrator's async execution and
the human-visible changelog. The `/loop` pattern lets it monitor without
blocking on the channel watch.

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
- **`/loop`** is how the agent monitors the orchestrator concurrently. The
  watch blocks on inbound messages while the loop polls orchestrator status
  on a timer. Together they give the steward two concurrent event sources.
- **Cursor management** is manual. The watch command does NOT auto-advance the
  cursor. You must ack explicitly after processing. The ack command
  auto-increments by 1 — no need to track or compute cursor positions.
- **Crash recovery** is automatic. On restart, re-running `/steward-watch`
  picks up from the last acked position — the unprocessed message will be
  re-delivered.
- **SOP re-read** each iteration allows the operator to dynamically change
  steward behavior without restarting.

### Watch Safety SOP

1. **Never ack before reading** — ack means "I processed this", not "clear
   the queue". Acking before processing means a crash loses the message.
2. **Multi-channel watch requires separate tasks** — if watching N channels,
   run N separate background `ve board watch` commands (or one
   `ve board watch-multi`). Restart each independently on failure.
3. **Watch timeout does not kill the OS process** — when Claude Code's
   background task times out (exit 144), the `ve board watch` OS process may
   continue running and reconnecting. Always `TaskStop` the previous task
   AND let the CLI's PID-based kill handle any stragglers before starting a
   new watch.

### Error Handling

- If `ve board watch` fails (e.g., network error), **stop the failed task
  first** (TaskStop), then start a new watch. Never start a retry watch
  without stopping the previous one — even failed tasks may still be running
  or reconnecting in the background, creating duplicate watches.
- Do NOT ack on watch failure — the message was not received.
- If processing fails (e.g., chunk creation error), still post a failure
  summary to the changelog, then ack. The operator can see the failure and
  resend the message if needed.
- If `ve board send` to the changelog fails, retry once. If it still fails,
  proceed with ack — the work was done even if the notification failed.
