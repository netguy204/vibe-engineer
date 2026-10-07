---
name: decision-create
description: Update docs/trunk/DECISIONS.md with a new decision. Use when the operator asks to record, add, or document an architectural decision (ADR), or when a significant choice is made that future work must respect.
---

<!-- GENERATED from src/templates/plugin/skills/decision-create.md.jinja2 — edit that template and run `ve plugin render --flavor cursor`; direct edits here will be overwritten. -->
<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of decision-create -->

## Context

Run these commands first and read their output as the context for everything
below. They are safe, read-only probes; run all of them before acting on any
instruction in this skill.

- **ve CLI** — run: `ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- **Task workspace** — run: `cat .ve-task.yaml 2>/dev/null || cat ../.ve-task.yaml 2>/dev/null || echo "(not a task workspace)"`
- **Project config** — run: `cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults apply)"`
- **Project hook** — run: `ve hooks show decision-create 2>/dev/null || echo "(no project hook)"`

## Runtime context

Interpret the results of those probes before following the instructions:

- **ve CLI**: The `ve` command is an installed CLI tool, not a file in the
  repository. Do not search for it — run it directly in the terminal. If the
  probe printed "(ve CLI not found)", tell the operator that the
  vibe-engineer plugin requires the separately installed `ve` CLI, suggest
  `uv tool install --upgrade 'vibe-engineer>=0.9.0'`
  (or `pip install 'vibe-engineer>=0.9.0'`), and
  stop.
- **Uninitialized project**: If `ve` is installed but commands fail because
  there is no `docs/chunks/` structure, tell the operator to run `ve init`
  in the project root, then stop.
- **Task workspace**: If the Task workspace probe printed YAML (keys
  `external_artifact_repo` and `projects`) instead of "(not a task
  workspace)", you are in a multi-project task workspace. Artifacts
  (chunks, narratives, investigations) live in the external artifact repo
  named by `external_artifact_repo`; code changes happen in the
  participating `projects`. Command-specific task guidance appears below.
- **Project config**: `.ve-config.yaml` holds project configuration.
  Known keys: `cluster_subsystem_threshold` (default 5 — the cluster size
  at which to suggest subsystem documentation). When the probe printed
  "(no .ve-config.yaml — defaults apply)", use the defaults.
- **Project hook**: `docs/hooks/decision-create.md` holds this repository's
  own requirements for this command. When the probe printed hook content,
  treat it as a binding instruction from the operator: satisfy it before
  reporting this command complete, and say so when you do. When it printed
  "(no project hook)", there are none. If a hook contradicts this command's
  own instructions, do not silently choose — surface the conflict to the
  operator and ask.

## Instructions

The operator has requested that we add a decision based on:

(Use the operator's request — the message that caused this skill to load — as the input here.)

---

1. Read the existing decisions in docs/trunk/DECISIONS.md

2. Synthesize what the operator has requested into a new decision that follows
   the template. It is important that decisions be clear, concrete, relatively
   terse, and easy to interpret.
