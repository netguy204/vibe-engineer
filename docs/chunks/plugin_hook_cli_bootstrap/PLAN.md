

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Extend hooks/session_start.sh in place: hoist plugin-version parsing above
the presence check, replace the missing-CLI hint branch with a guarded
bootstrap (announce → uv tool install from $CLAUDE_PLUGIN_ROOT → report →
markers), and add a managed-only sync branch to the drift warning. Extend
tests/test_session_hook.py with a stub uv harness. Record DEC-013, update
README.

## Subsystem Considerations

None — plugin shell content plus trunk docs.

## Sequence

### Step 1: Tests first — stub uv harness + four bootstrap paths
### Step 2: Rework hooks/session_start.sh
### Step 3: DEC-013 + README session-hook paragraph
### Step 4: Full session-hook suite + plugin suites green

## Dependencies

Parent chunk plugin_session_hooks (ACTIVE).

## Risks and Open Questions

- Real `uv tool install` latency on first session (seconds, one-time) —
  accepted; hooks run under Claude Code's own hook timeout.

## Deviations

(populated during implementation)
