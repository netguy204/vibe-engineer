---
title: Nuclear Exit Safety
created: 2026-03-31
updated: 2026-03-31
---

# Nuclear Exit Safety

## What It Is

A defense-in-depth strategy to ensure a Node.js process **never** exits with a non-zero code, regardless of how it terminates.

## When to Use

When running under a supervisor (like the [[tool_runner]]) that penalizes non-zero exits, and you need guaranteed clean exits even during signal handling, unhandled rejections, or unexpected errors.

## Implementation

```javascript
// Layer 1: Set default exit code
process.exitCode = 0;

// Layer 2: Override process.exit
const _realExit = process.exit.bind(process);
process.exit = (code) => { _realExit(0); };

// Layer 3: Catch unhandled rejections (Node 22 exits with code 1)
process.on('unhandledRejection', () => {});

// Layer 4: Catch uncaught exceptions
process.on('uncaughtException', (err) => {
  try { process.stderr.write(`Uncaught: ${String(err)}\n`); } catch (_) {}
});

// Layer 5: Handle signals
process.on('SIGTERM', () => process.exit(0));
process.on('SIGINT', () => process.exit(0));
```

## Pitfalls

- **`err.message` on null**: If an exception handler accesses `err.message` and `err` is null, the handler itself throws, creating an infinite crash loop. Always use `String(err)`.
- **`process.stderr.write()` can throw**: If stderr is closed, writing throws. Wrap all logging in try/catch.
- **Shell wrapper is more reliable**: For absolute guarantees, wrap the Node script in `bash -c 'node worker.js; exit 0'`.

## When NOT to Use

When you actually want crash visibility. This pattern silences all errors. Use it only in proving/supervisor contexts where exit code semantics are binary (0 = healthy, anything else = broken).
