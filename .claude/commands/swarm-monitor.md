---
description: Monitor all changelog channels in a swarm
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->





## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Instructions

Monitor all changelog channels across a swarm from a single command. This
automates the workflow of listing channels, checking for unread messages,
and launching background watches — giving operators a unified view of swarm
activity.


### Phase 1: Discover changelog channels

$ARGUMENTS

Run `ve board channels` to list all channels in the swarm. By default this
uses the bound swarm from `~/.ve/board.toml`. If the operator provided a
`--swarm <id>` argument, pass it through. If a non-default server is needed,
add `--server <url>`.

```
ve board channels [--swarm <swarm_id>] [--server <url>]
```

**Output format:** Each line is `<name>  head=<N>  oldest=<N>`.

Filter the output for channels matching the `*-changelog` pattern (e.g.,
`vibe-engineer-changelog`, `lite-edit-changelog`). These are the channels
this command monitors.

**Error handling:**
- If `ve board channels` fails (e.g., no swarm configured, network error),
  report the error to the operator and stop.
- If no `*-changelog` channels are found, inform the operator that there are
  no changelog channels to monitor and stop.

Display the discovered changelog channels to the operator.

### Phase 2: Show cursor vs head for each channel

For each discovered changelog channel:

1. Read the local cursor file at `.ve/board/cursors/<channel>.cursor`
   (treat missing file as cursor position 0)
2. Parse the `head=<N>` value from the `ve board channels` output
3. Calculate unread count: `head - cursor`

Display a summary table to the operator:

```
Channel                        Cursor  Head  Unread
vibe-engineer-changelog             3     5       2
lite-edit-changelog                 7     7       0
another-project-changelog           0     3       3
```

Highlight any channels with unread messages (unread > 0).

### Phase 3: Launch multi-channel watch

Start a single `ve board watch-multi` command with `--count 1` and all
discovered changelog channels. This uses one WebSocket connection for all
channels and exits after receiving one message:

```
ve board watch-multi <channel1> <channel2> ... --count 1 --swarm <swarm_id> [--server <url>]
```

Use `run_in_background` so the agent is notified when a message arrives.
The `watch-multi` command auto-advances cursors after each message is
delivered and outputs messages tagged with their channel name.

Report to the operator which channels are being watched.

### Phase 4: Event-driven message loop

When the background `watch-multi --count 1` task completes, you will be
notified. Each line of output is formatted as `[channel-name] message text`.

For each completed task:

1. **Read the task output** to get the message.

2. **Display the message** to the operator inline. Example:

   ```
   [vibe-engineer-changelog] New message:
   <message content>
   ```

3. Cursors are **auto-advanced** by `watch-multi` — no manual `ve board ack`
   is needed.

4. **Re-launch** `watch-multi --count 1` with `run_in_background` to wait
   for the next message.

5. Repeat until the operator stops the session.

### Key Concepts

- **`watch-multi --count 1`** watches all channels on a **single connection**,
  receives one message, and exits. This makes it compatible with the
  `run_in_background` notification pattern.
- **Event-driven loop**: Launch `--count 1` in background → get notified on
  exit → process message → re-launch. This replaces indefinite streaming
  with deterministic exit-on-message.
- **`--count 0`** streams indefinitely (legacy behavior). Use `--count 1`
  (the default) for the event-driven agent pattern.
- **Cursor management** is automatic — `watch-multi` auto-advances cursors
  after each delivered message. No manual acking is needed.
- **Channel naming convention**: This command assumes `*-changelog` is the
  pattern for changelog channels. This matches the standard naming
  convention (e.g., `vibe-engineer-changelog`).
- **Output format**: Each line is `[channel-name] decrypted message text`.
