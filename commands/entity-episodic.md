---
name: entity-episodic
description: Search prior session transcripts for specific events, conversations, and decisions. Use when the operator references a prior session ("remember when we..."), when an error or decision feels familiar, or when you need the raw history behind a memory rather than distilled lessons.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve entity episodic:*), Bash(ve entity recall:*)
---

<!-- Chunk: docs/chunks/plugin_orch_commands - Static plugin port of entity-episodic -->
<!-- Chunk: docs/chunks/entity_episodic_skill - Episodic memory search skill -->

## Context

- ve CLI: !`ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- Task workspace: !`cat .ve-task.yaml 2>/dev/null || cat ../.ve-task.yaml 2>/dev/null || echo "(not a task workspace)"`
- Project config: !`cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults apply)"`

## Runtime context

Interpret the context above before following the instructions:

- **ve CLI**: The `ve` command is an installed CLI tool, not a file in the
  repository. Do not search for it — run it directly via Bash. If the
  context shows "(ve CLI not found)", tell the operator that the
  vibe-engineer plugin requires the separately installed `ve` CLI, suggest
  `uv tool install vibe-engineer` (or `pip install vibe-engineer`), and
  stop.
- **Uninitialized project**: If `ve` is installed but commands fail because
  there is no `docs/chunks/` structure, tell the operator to run `ve init`
  in the project root, then stop.
- **Task workspace**: If the Task workspace context shows YAML (keys
  `external_artifact_repo` and `projects`) instead of "(not a task
  workspace)", you are in a multi-project task workspace. Artifacts
  (chunks, narratives, investigations) live in the external artifact repo
  named by `external_artifact_repo`; code changes happen in the
  participating `projects`. Command-specific task guidance appears below.
- **Project config**: `.ve-config.yaml` holds project configuration.
  Known keys: `cluster_subsystem_threshold` (default 5 — the cluster size
  at which to suggest subsystem documentation). When the context shows
  "(no .ve-config.yaml — defaults apply)", use the defaults.

## Instructions

### When to use episodic vs memory recall

- `ve entity recall <name> <query>` → distilled knowledge, lessons, skills, principles.
  *"What do I know about X?"* These are insights extracted from prior sessions.

- `ve entity episodic --entity <name> --query "..."` → raw session history, conversations,
  decisions in context. *"When did I encounter X? What did the operator say? What was the
  outcome?"* These are actual transcript snippets, not distilled.

### Common triggers for episodic search

- The operator references something from a prior session ("remember when we...")
- You're about to make a decision similar to one made before
- You encounter an error you think you've seen before
- You need context behind a core memory (why was it created?)
- The operator asks you to find a specific conversation or decision

### Two-phase workflow

**Step 1 — Search**

Run the search to get ranked snippets:

```
ve entity episodic --entity <name> --query "..."
```

Scan the results to identify which hits look relevant. Each result includes a
copy-pasteable expand command.

**Step 2 — Expand**

Run the expand command from the search output to read the surrounding conversation:

```
ve entity episodic --entity <name> --expand <session_id> --chunk <chunk_id> --radius 10
```

The hit region is marked with `>>>`, context lines with spaces. Read the expanded
output to understand:
- What led to this moment
- What correction or decision followed
- What the outcome was

Be selective — expand the top 1–2 results, not all of them. Each expansion costs
context window space.

### Practical examples

```
# "I think we had a similar merge conflict issue before"
ve entity episodic --entity steward --query "merge conflict orchestrator"

# "What did the operator say about how to handle chunk creation?"
ve entity episodic --entity steward --query "chunk creation SOP correction"

# "I'm seeing a WebSocket timeout — have we debugged this before?"
ve entity episodic --entity steward --query "websocket timeout reconnect"
```

### Important caveats

- Episodic search only covers sessions run through `ve entity claude` (which archives
  transcripts). Older sessions may not be indexed.
- The search is keyword-based (BM25), not semantic. Use specific terms from the domain
  rather than abstract concepts.
- Expanding a hit costs context window space. Be selective — expand the top 1–2 results,
  not all of them.
