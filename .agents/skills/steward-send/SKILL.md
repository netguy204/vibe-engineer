---
name: steward-send
description: Send a message to a project's steward
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->



## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Instructions

Send a message to a steward's inbound channel. Use this to request work from
another project's steward or your own.


### Parse arguments

$ARGUMENTS

The arguments should identify:
1. **Target** — the steward's channel name and swarm ID
2. **Message** — what to send

If the operator provides a channel name and swarm ID directly, use those. If
they name a project, check if that project has a `docs/trunk/STEWARD.md`
accessible (e.g., in a sibling directory, via external artifact references, or
from operator guidance) and read its frontmatter for `channel` and `swarm`.

If neither is available, ask the operator for the channel name and swarm ID.

### Send the message

Run:

```
ve board send <channel> "<message>" --swarm <swarm_id>
```

If a server URL is needed (non-default backend), add `--server <url>`.

### Confirm

Report the result to the operator, including:
- The channel the message was sent to
- The position returned by the send command (this is the message's position in
  the channel)

### Follow up

Suggest that the operator can watch for the steward's response using
`/steward-changelog` to monitor the target project's changelog channel. This
closes the loop — send a request, then watch for the outcome.
