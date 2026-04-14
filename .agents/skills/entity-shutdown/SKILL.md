---
name: entity-shutdown
description: Run the sleep cycle for an entity — extract memories and consolidate
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->



## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Instructions


Run the sleep cycle for a named entity. This extracts memory-worthy events from
your current session and consolidates them into the entity's persistent memory.

### Step 1: Identify the entity

Ask the operator which entity to shut down, or accept the entity name as an
argument to this command (e.g., `/entity-shutdown mysteward`).

Verify the entity exists by running:
```
ve entity list --project-dir .
```

### Step 2: Extract memories from this session

Review your entire conversation in this session. Identify moments worth
REMEMBERING across session boundaries — things that would prevent the operator
from having to retrain you.

**Categories of memory-worthy events** (in priority order):

1. **correction**: The operator corrected your behavior or approach.
   Extract WHAT you were doing wrong and WHAT you should do instead.

2. **skill**: You learned a workflow, procedure, or pattern through
   interaction. Extract the skill as a reusable instruction.

3. **domain**: The operator taught you something about the problem domain
   — how entities relate, what distinctions matter, invariant rules.

4. **confirmation**: The operator validated your approach. Extract what
   was confirmed so you don't drift away from it.

5. **coordination**: You learned something about how to coordinate with
   other agents or async processes.

6. **autonomy**: The operator calibrated when you should act vs ask,
   take initiative vs wait.

**For each memory, provide:**
- **title**: 3-8 word summary
- **content**: 1-3 sentences capturing what was learned (NOT what happened —
  frame as knowledge/skill, not narrative)
- **valence**: "positive" (something that worked), "negative" (something to avoid),
  or "neutral" (factual knowledge)
- **category**: one of the categories above
- **salience**: 1-5 (5 = critical skill you keep forgetting, 1 = minor detail)

**Important guidelines:**
- Extract the LESSON, not the story. "Always check PR state before acting on it"
  not "On March 14th, the operator pointed out the PR was already merged."
- Be specific enough to be actionable. "Use exact-match keys instead of prefix
  matching" not "Be careful with matching."
- If the operator explicitly says "remember this" or "update your SOP", that's
  salience 5.
- Confirmation memories are important too — they anchor what's working.
- Aim for 5-20 memories per session. Not every message is memory-worthy.

### Step 3: Write memories to a temp file

Format the extracted memories as a JSON array and write to a temporary file:

```json
[
  {
    "title": "Check PR state before acting",
    "content": "Before taking action on a PR, always verify its current state. PRs may have been merged or closed while working on something else.",
    "valence": "negative",
    "category": "correction",
    "salience": 4
  },
  {
    "title": "Verification query after data reload",
    "content": "After triggering a data reload, always run the verification query to confirm the new data looks correct before proceeding.",
    "valence": "positive",
    "category": "skill",
    "salience": 3
  }
]
```

Write this JSON to a temporary file (e.g., `/tmp/entity_memories.json`).

### Step 4: Run the consolidation

```bash
ve entity shutdown <entity_name> --memories-file /tmp/entity_memories.json
```

This command will:
1. Store each extracted memory as a journal entry (tier 0)
2. Load existing consolidated (tier 1) and core (tier 2) memories
3. Run incremental consolidation to merge new memories into existing tiers
4. Write updated memory files to the entity's memory directory

### Step 5: Report results

After the command completes, tell the operator:
- How many journal memories were extracted
- How many consolidated memories were created/updated
- How many core memories exist
- Any notable promotions (journal → consolidated → core)

Clean up the temporary file when done.
