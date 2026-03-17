---
description: Watch a project's changelog channel
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->



## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Instructions

Watch a project's changelog channel to see steward outcomes. This is typically
used after `/steward-send` to close the loop — you sent a request and now want
to see the steward's response.


### Identify the changelog channel

$ARGUMENTS

Determine the changelog channel and swarm ID from:
1. **Arguments** — if the operator provided them directly
2. **Local SOP** — read `docs/trunk/STEWARD.md` if available and extract
   `changelog_channel` and `swarm` from the frontmatter
3. **Operator** — ask if neither of the above is available

### Watch with your own cursor

Run `ve board watch <changelog_channel> --swarm <swarm_id>` using
`run_in_background`.

The cursor for this channel is project-local (stored at
`.ve/cursors/<changelog_channel>.cursor`), so each requester independently
tracks their position on the changelog. You will only see messages posted
after your last acked position.

If a server URL is needed (non-default backend), add `--server <url>`.

### Display the message

When the watch returns, display the changelog entry to the operator. The
message is the decrypted plaintext from stdout.

### Ack and optionally continue

After displaying the message, acknowledge it to advance the cursor:

```
ve board ack <changelog_channel>
```

The ack command auto-increments the cursor by 1 — no position argument needed.

Then ask the operator:
- **Continue watching?** Start another `run_in_background` watch for more
  changelog updates.
- **Done?** Stop watching. The cursor is saved, so next time you watch you'll
  pick up where you left off.
