---
name: entity-shutdown
description: Run the sleep cycle for an entity — extract memories and consolidate. Use when the operator asks to shut down, sleep, or consolidate a named entity at the end of an entity session.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve entity list:*), Bash(ve entity shutdown:*)
---

<!-- Chunk: docs/chunks/plugin_orch_commands - Static plugin port of entity-shutdown -->
<!-- Chunk: docs/chunks/entity_shutdown_skill - Entity shutdown skill template -->

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

Run the sleep cycle for a named entity. This consolidates what was learned this
session into the entity's persistent memory tiers.

The exact steps depend on whether this is a **wiki-based entity** (has a `wiki/`
directory) or a **legacy entity** (memory-only, no wiki).

### Step 1: Identify the entity

Ask the operator which entity to shut down, or accept the entity name as an
argument to this command (e.g., `/entity-shutdown mysteward`).

Verify the entity exists by running:
```
ve entity list --project-dir .
```

Check whether the entity is wiki-based:
```bash
ls .entities/<entity_name>/wiki 2>/dev/null && echo "wiki entity" || echo "legacy entity"
```

---

## Wiki-based entities (have `wiki/` directory)

For wiki entities, the shutdown pipeline uses Agent SDK to automatically diff
the wiki and consolidate new knowledge. No manual memory extraction is needed.

### Step 2 (wiki): Update the wiki

During the session, you should have updated the wiki pages in
`.entities/<entity_name>/wiki/` to reflect what was learned. If you haven't done
so yet, update the relevant wiki pages now.

Use git to check what changed:
```bash
git -C .entities/<entity_name> status
```

### Step 3 (wiki): Run the shutdown

```bash
ve entity shutdown <entity_name>
```

This command will:
1. Diff the wiki/ changes since last commit
2. Launch an Agent SDK session that reads existing memories and integrates new learning
3. The agent writes updated memory files and commits them
4. Report a summary of journals, consolidated, and core memory counts

### Step 4 (wiki): Report results

After the command completes, tell the operator:
- How many wiki diff lines were processed (journals_added)
- How many consolidated memories exist
- How many core memories exist
- Any notable changes to identity-level memories

---

## Legacy entities (no `wiki/` directory)

For legacy entities, you extract memories manually from the session, then run
the consolidation via the Anthropic API.

### Step 2 (legacy): Extract memories from this session

Review your entire conversation in this session. Identify moments worth
REMEMBERING across session boundaries.

**Categories of memory-worthy events** (in priority order):

1. **correction**: The operator corrected your behavior or approach.
2. **skill**: You learned a workflow, procedure, or pattern.
3. **domain**: The operator taught you something about the problem domain.
4. **confirmation**: The operator validated your approach.
5. **coordination**: You learned something about coordinating with other agents.
6. **autonomy**: The operator calibrated when you should act vs ask.

**For each memory, provide:**
- **title**: 3-8 word summary
- **content**: 1-3 sentences (frame as knowledge/skill, not narrative)
- **valence**: "positive" / "negative" / "neutral"
- **category**: one of the categories above
- **salience**: 1-5 (5 = critical)

### Step 3 (legacy): Write memories to a temp file

```json
[
  {
    "title": "Check PR state before acting",
    "content": "Before taking action on a PR, always verify its current state.",
    "valence": "negative",
    "category": "correction",
    "salience": 4
  }
]
```

Write this JSON to `/tmp/entity_memories.json`.

### Step 4 (legacy): Run the consolidation

```bash
ve entity shutdown <entity_name> --memories-file /tmp/entity_memories.json
```

### Step 5 (legacy): Report results

After the command completes, tell the operator:
- How many journal memories were extracted
- How many consolidated memories were created/updated
- How many core memories exist

Clean up the temporary file when done.
