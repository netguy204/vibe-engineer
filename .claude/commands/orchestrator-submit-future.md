---
description: Batch-submit all FUTURE chunks to the orchestrator.
---




<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

This file is rendered from: src/templates/commands/orchestrator-submit-future.md.jinja2
Edit the source template, then run `ve init` to regenerate.
-->


## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Instructions

This command batch-submits all FUTURE chunks to the orchestrator, with guards
for uncommitted changes and already-running chunks.

Follow these steps in order:

### Step 1: Ensure orchestrator is running

Check the orchestrator status:

```bash
ve orch status
```

If the orchestrator is not running, start it:

```bash
ve orch start
```

### Step 2: Identify FUTURE chunks

List all chunks and filter for FUTURE status:

```bash
ve chunk list | grep "\[FUTURE\]"
```

From the output, identify chunks marked with `[FUTURE]`. If there are no FUTURE
chunks, inform the user and stop.

### Step 3: Get current orchestrator work units

Query the orchestrator for already-running work:

```bash
ve orch ps --json
```

Parse the JSON output to get the list of chunk names currently in the
orchestrator. Note their status (RUNNING, DONE, etc.).

### Step 4: Evaluate each FUTURE chunk

For each FUTURE chunk identified in Step 2, check eligibility:

**4a. Check for uncommitted changes:**

```bash
git status --porcelain docs/chunks/<chunk_name>/
```

If this command produces any output, the chunk has uncommitted changes and
cannot be submitted. Add it to the "skipped (uncommitted)" list and continue
to the next chunk.

**4b. Check orchestrator presence:**

Compare the chunk name against the work units from Step 3. If the chunk is
already in the orchestrator (regardless of status), add it to the "skipped
(already in orchestrator)" list with its current status and continue to the
next chunk.

**4c. Submit eligible chunks:**

If the chunk passes both checks (committed AND not in orchestrator), submit it:

```bash
ve orch inject <chunk_name>
```

Add it to the "submitted" list.

### Step 5: Report summary

Present a summary to the user organized by outcome:

**Submitted:** (chunks successfully injected)
- List each chunk that was submitted

**Skipped (uncommitted changes):** (cannot submit until committed)
- List each chunk with uncommitted changes
- Suggest: "Commit these chunks before running this command again"

**Skipped (already in orchestrator):** (no action needed)
- List each chunk already in the orchestrator with its current status

If all FUTURE chunks were skipped, explain why no chunks were submitted.