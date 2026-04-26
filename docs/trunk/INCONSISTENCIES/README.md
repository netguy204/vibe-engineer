# Inconsistencies Log

A running log of discovered mismatches between what the project's chunks (or trunk docs) claim about the system and what the code or runtime actually does.

This is a sibling concept to `docs/trunk/FRICTION.md` — both accumulate observations over time — but with two differences:

1. **Concurrent-safe by design.** Each entry is its own file. Multiple agents can add entries in parallel without coordinating. (FRICTION.md is a single file edited sequentially; this directory is touched by many agents at once during audits.)
2. **Tied to specific code/doc claims.** Every entry names the artifact that lies and the reality it's lying about. Friction entries describe felt pain; inconsistency entries describe verifiable mismatches.

## When to add an entry

Whenever you discover that a chunk's GOAL.md, a trunk doc, a template comment, or a skill description **claims something about the system that the code or runtime contradicts**. The two failure modes from the `intent_active_audit` chunk both qualify, but anything in this category counts:

- A doc or skill says behavior X is supported; the runtime rejects it.
- A chunk's GOAL.md asserts the system does X; grepping the code shows it doesn't.
- A chunk's `code_references` admit `status: partial` while the GOAL claims completeness.
- A skill description references a flag, command, or capability that doesn't exist.

## Filename convention

```
YYYYMMDD_HHMMSS_microseconds_<slug>.md
```

Example: `20260426_001910_713792_orch_rejects_active_depends_on.md`

Microsecond precision plus a descriptive slug makes collisions effectively impossible across concurrent writers. Agents should generate the timestamp at write time:

```
python3 -c "from datetime import datetime; print(datetime.now().strftime('%Y%m%d_%H%M%S_%f'))"
```

The slug is a short kebab-or-snake-case description of *what* is inconsistent, not the fix. `orch_rejects_active_depends_on` is good; `fix_depends_on_validation` is not.

## Entry format

Each entry is a markdown file with YAML frontmatter:

```yaml
---
discovered_by: <agent name or "operator">
discovered_at: <ISO 8601 timestamp>
severity: low | medium | high
status: open | resolved
resolved_by: <chunk name or commit SHA, when status: resolved>
artifacts:
  - <file path of the artifact making the false claim>
---
```

Body sections:

- **Claim** — what the artifact says (verbatim or close to it, with the file path and line number).
- **Reality** — what the code or runtime actually does. Include a reproduction (command, error message) where possible.
- **Workaround** — what was done in this session to proceed past the inconsistency, if anything. So the next agent doesn't redo it.
- **Fix paths** — possible resolutions, ranked by preference. Usually two: fix the artifact to match reality, or fix reality to match the artifact.

## Lifecycle

- Entries land with `status: open`.
- When a chunk or commit resolves the inconsistency, set `status: resolved` and `resolved_by:` to the chunk name or commit SHA.
- Resolved entries stay in the log indefinitely (cheap to keep, useful for archaeology). If the directory grows too dense, that's a separate cleanup concern — propose a pruning chunk rather than deleting ad-hoc.

## How this differs from chunk audit work

The `intent_active_audit` chunk (and any future audit chunks) **discovers** inconsistencies and writes entries here. The audit chunk's job is enumeration and triage; the actual fixes happen in follow-up chunks (or inline, if mechanical). This log is the durable record of what was found, what's been resolved, and what's still outstanding — independent of whether any particular audit chunk is currently running.
