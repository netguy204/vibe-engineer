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

### Phase 3: Launch background watches

For each changelog channel that has **unread messages** OR is **at head**
(cursor == head, waiting for new messages), start a background watch:

```
ve board watch <channel> --swarm <swarm_id> [--server <url>]
```

Use `run_in_background` for each watch so they run concurrently.

Before launching each watch, note the current cursor position for that
channel (from the cursor file read in Phase 2). You'll need this for
acking in Phase 4.

Report to the operator which channels are being watched and how many
background watches were launched.

**Note:** If the swarm has many changelog channels, this will launch many
concurrent background watches. If resource usage is a concern, the operator
can re-run the command and select a subset of channels to monitor.

### Phase 4: Report incoming messages

As background watches complete (a message arrives on a channel):

1. **Display the message** to the operator inline, including which channel
   it came from. Example:

   ```
   [vibe-engineer-changelog] New message at position 6:
   <message content>
   ```

2. **Ack the message** to advance the cursor:

   ```
   ve board ack <channel> <position>
   ```

   Where `<position>` is the cursor position noted before watching + 1.

3. **Re-launch the watch** on that channel using `run_in_background` to
   continue monitoring for more messages.

Repeat this cycle as messages arrive. The monitoring continues until the
operator stops the session or all watches are complete.

### Key Concepts

- **`run_in_background`** is how the agent waits asynchronously for messages.
  Do NOT poll. Each `ve board watch` blocks until a message arrives.
- **Cursor management** is manual — you must `ve board ack` after each
  message to advance the cursor. Without acking, the next watch will
  re-deliver the same message.
- **Channel naming convention**: This command assumes `*-changelog` is the
  pattern for changelog channels. This matches the standard naming
  convention (e.g., `vibe-engineer-changelog`).
- **Concurrent watches**: All channels are watched in parallel via
  `run_in_background`. Messages from any channel are reported as they arrive.
