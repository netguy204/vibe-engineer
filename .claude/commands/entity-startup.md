---
description: Wake an entity by loading its identity, memories, and operational context
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->



## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Instructions

Wake a named entity by loading its identity, accumulated memories, and
operational context into the current session.


### Step 1: Identify the entity

The entity name should be provided as an argument to this command. If no
argument was provided, ask the operator which entity to wake up. You can
list available entities with:

```
ve entity list
```

### Step 2: Load the startup payload

Run the startup command to get the entity's full context payload:

```
ve entity startup <name>
```

If you are working in the vibe-engineer source repository, use `uv run`:

```
uv run ve entity startup <name>
```

### Step 3: Adopt the identity

Read the **Entity** and **Role** section of the output. This is who you are
for this session. Adopt the described identity, responsibilities, and
behavioral style.

Read the **Startup Instructions** section carefully — these are
operator-provided instructions that should shape your behavior.

### Step 4: Internalize core memories

Read each numbered **Core Memory** (CM1, CM2, ...) in the output. These are
your internalized principles and skills — treat them as operational knowledge
you have already learned, not as instructions to be followed mechanically.

### Step 5: Note the consolidated memory index

The **Consolidated Memory Index** lists memories available for on-demand
retrieval. You don't need to load these now — just note what's available.

When you need details on a consolidated memory, retrieve it with:

```
ve entity recall <name> <query>
```

Where `<query>` is a case-insensitive substring of the memory title.

### Step 6: Follow the touch protocol

When you notice yourself applying a core memory (CM1, CM2, ...), run:

```
ve entity touch <memory_id> <reason>
```

This enables retrieval-as-reinforcement — the act of noticing you used a
memory strengthens it. For example:

```
ve entity touch CM3 "Used template editing workflow to fix rendering issue"
```

### Step 7: Restore active state

If the **Active State** section mentions channels you were watching or
async operations that were pending, restart them now. This typically means
re-running watch commands or resuming monitoring loops.

