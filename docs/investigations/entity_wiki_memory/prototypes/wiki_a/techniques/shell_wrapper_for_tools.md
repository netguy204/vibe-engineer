---
title: Shell Wrapper for Tools
created: 2026-03-31
updated: 2026-03-31
---

# Shell Wrapper for Tools

## What It Is

Wrapping a Node.js worker script in a bash shell script that unconditionally exits 0. The shell script is the registered tool; the Node script lives outside `tools/`.

## When to Use

When Node.js signal handling and exit code overrides prove insufficient to guarantee exit 0 under all conditions. Bash `exit 0` is unconditional and cannot be overridden by anything the child process does.

## Structure

```
tools/
  poll.sh          # Registered tool — entry point
workspace/
  poll-worker.js   # Actual implementation — NOT in tools/
```

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENTITY_DIR="$(dirname "$SCRIPT_DIR")"
node "$ENTITY_DIR/workspace/poll-worker.js"
exit 0
```

## Why the Worker Must Be Outside `tools/`

The [[tool_runner]] registers **every file** in `tools/` as a separate tool. If the worker is in `tools/`, both `poll.sh` and `poll-worker.js` get registered. The worker writes heartbeats for `poll.sh` but is spawned as `poll-worker.js` — heartbeat name mismatch causes timeouts.

## Pitfalls

- The worker's heartbeat file name must match the shell script name (`poll.sh`), not the worker name
- File watcher still triggers on shell script changes, but the worker can be edited freely since it's in `workspace/`
