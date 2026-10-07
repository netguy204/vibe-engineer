---
name: cluster-rename
description: Rename all chunks matching a prefix to use a new prefix, updating frontmatter references automatically and prose references with manual review. Use when the operator asks to rename a chunk cluster, re-prefix related chunks, or consolidate chunk naming.
---

<!-- GENERATED from src/templates/plugin/skills/cluster-rename.md.jinja2 — edit that template and run `ve plugin render --flavor cursor`; direct edits here will be overwritten. -->
<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of cluster-rename -->
<!-- Chunk: docs/chunks/cluster_rename - Slash command template for /cluster-rename -->

## Context

Run these commands first and read their output as the context for everything
below. They are safe, read-only probes; run all of them before acting on any
instruction in this skill.

- **ve CLI** — run: `ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- **Task workspace** — run: `cat .ve-task.yaml 2>/dev/null || cat ../.ve-task.yaml 2>/dev/null || echo "(not a task workspace)"`
- **Project config** — run: `cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults apply)"`
- **Project hook** — run: `ve hooks show cluster-rename 2>/dev/null || echo "(no project hook)"`

## Runtime context

Interpret the results of those probes before following the instructions:

- **ve CLI**: The `ve` command is an installed CLI tool, not a file in the
  repository. Do not search for it — run it directly in the terminal. If the
  probe printed "(ve CLI not found)", tell the operator that the
  vibe-engineer plugin requires the separately installed `ve` CLI, suggest
  `uv tool install --upgrade 'vibe-engineer>=0.10.0'`
  (or `pip install 'vibe-engineer>=0.10.0'`), and
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
- **Project hook**: `docs/hooks/cluster-rename.md` holds this repository's
  own requirements for this command. When the probe printed hook content,
  treat it as a binding instruction from the operator: satisfy it before
  reporting this command complete, and say so when you do. When it printed
  "(no project hook)", there are none. If a hook contradicts this command's
  own instructions, do not silently choose — surface the conflict to the
  operator and ask.

## Instructions

The operator has requested a cluster rename operation:

(Use the operator's request — the message that caused this skill to load — as the input here.)

Parse the arguments to extract `<old_prefix>` and `<new_prefix>`. The format should be:
`/cluster-rename <old_prefix> <new_prefix>`

---

### Phase 1: Dry-Run Preview

1. Run the cluster rename command in dry-run mode (default):
   ```
   ve chunk cluster-rename <old_prefix> <new_prefix>
   ```

2. Review the output, which shows:
   - **Directories to be renamed**: Chunk directories that will be renamed
   - **Frontmatter references to update**: `created_after`, subsystem `chunks`, narrative/investigation `proposed_chunks`
   - **Prose references for manual review**: Potential mentions in documentation that may need updating

3. If no chunks match the prefix or there are validation errors (collisions, dirty working tree), the command will fail with an error message. Address any issues before proceeding.

4. **Note the prose references** shown in the output—you will address these AFTER the automated rename completes.

---

### Phase 2: Execute the Rename

Execute the rename to apply all automatable changes:

1. Run with `--execute` flag:
   ```
   ve chunk cluster-rename <old_prefix> <new_prefix> --execute
   ```

2. The command will automatically:
   - Rename chunk directories
   - Update all frontmatter references (`created_after`, subsystem `chunks`, narrative/investigation `proposed_chunks`)

3. Verify the automated changes:
   - Run `ve chunk list` to see the renamed chunks
   - Spot-check a few updated frontmatter references

---

### Phase 3: Fix Prose References

Now that the automated rename is complete, manually review and fix the prose references that were identified in Phase 1.

**Why this order matters**: The CLI handles structured references (frontmatter fields, code backreferences) automatically. Prose references require semantic judgment that only you can provide. By executing first, you avoid accidentally duplicating work the CLI would have done.

Prose references are mentions of chunk names in documentation that cannot be safely auto-updated because they may be:
- Part of explanatory text
- In code examples
- Historical references that should not change
- False positives (similar text that isn't actually a reference)

For each prose reference from the dry-run output:

1. **Read the context** around the reference to understand its purpose
2. **Decide if it should be updated**:
   - If it's a live reference to the chunk being renamed → update it
   - If it's a historical reference or example that should preserve the old name → leave it
   - If it's a false positive → ignore it
3. **Apply the fix** using targeted edits

Common patterns to update:
- `docs/chunks/<old_name>` → `docs/chunks/<new_name>` in prose text
- References in OVERVIEW.md files linking to chunks
- References in other chunk GOAL.md/PLAN.md prose sections

---

## Error Recovery

If something goes wrong during execution:

1. **Missed references**: Run `grep -r "<old_prefix>_" docs/ src/` to find any remaining references that weren't updated

2. **Build/test failures**: The rename should be purely cosmetic. If tests fail after rename, check for hardcoded chunk names in test fixtures
