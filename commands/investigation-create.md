---
name: investigation-create
description: Start a new investigation for exploratory work, or redirect to a simpler chunk workflow when the task is straightforward. Use when the operator wants to explore, diagnose, or understand something with an unclear root cause, multiple hypotheses, or architectural implications.
allowed-tools: Bash(ve --help:*), Bash(cat:*), Bash(ve investigation create:*)
---

<!-- Chunk: docs/chunks/plugin_core_commands - Static plugin port of investigation-create -->

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
- **If this is a task workspace** (the Task workspace context above shows
  `.ve-task.yaml` contents): this command creates artifacts in the external
  artifact repo named by `external_artifact_repo` in `.ve-task.yaml`. The
  investigation OVERVIEW.md will be created there. Exploration may span all
  participating projects listed under `projects`.

## Instructions

The operator has described something they want to explore or understand:

$ARGUMENTS

---

## Phase 1: Scale Assessment

Before creating an investigation, evaluate whether this task truly needs
investigative exploration or could be handled directly as a chunk.

### Investigation-Warranted Signals

Look for these signals that suggest a full investigation is appropriate:

- **Unclear root cause**: "I don't know why...", "something is causing...",
  "need to figure out..."
- **Multiple hypotheses**: "could be X or Y", "not sure if it's...", "might be..."
- **Spans multiple systems**: "affects both...", "across the...", "throughout..."
- **Architectural implications**: "might need to change our approach",
  "fundamental to how we..."
- **Exploration needed**: "want to understand...", "need to learn about...",
  "should we migrate to..."
- **Cross-session work**: Implies ongoing discovery that may span multiple sessions

### Chunk-Sufficient Signals

Look for these signals that suggest a direct chunk would be more appropriate:

- **Known fix**: "I know we need to...", "just need to change...",
  "the fix is..."
- **Single hypothesis**: Clear understanding of what needs to happen
- **Localized change**: Affects one file, function, or small area
- **Obvious next step**: "add a button that...", "change the color of...",
  "fix the typo in..."
- **No exploration needed**: Clear requirements, no uncertainty

### Decision

Based on your assessment, proceed to either **Phase 2A** (if investigation
signals dominate) or **Phase 2B** (if chunk signals dominate).

---

## Phase 2A: Investigation Creation (Investigation-Worthy)

If the task warrants investigation:

1. **Derive a short name** from the operator's description:
   - Extract key nouns that capture the subject of investigation
   - Use underscore separation (e.g., `memory_leak`, `graphql_migration`)
   - Keep under 32 characters
   - Present the proposed name:
     > "I'll create an investigation called `<proposed_name>` to explore this
     > systematically. Does this name work?"

2. **Create the investigation**:
   ```
   ve investigation create <confirmed_name>
   ```
   Note the created directory path. We'll refer to this as `<investigation_directory>`.

3. **Guide Trigger population**:
   Ask the operator to articulate what prompted this investigation:
   > "What specifically triggered this investigation? I'll document this in the
   > Trigger section."

   Update `<investigation_directory>/OVERVIEW.md` with their response.

4. **Guide Success Criteria population**:
   Ask the operator to define what "done" looks like:
   > "What questions must be answered, or what evidence would you need, to
   > consider this investigation complete?"

   Update the Success Criteria section with their response.

5. **Seed initial hypotheses**:
   Based on the description, propose 1-2 initial testable hypotheses:
   > "Based on what you've described, I'd suggest starting with these hypotheses:
   >
   > **H1: [hypothesis statement]**
   > - Test: [how to verify]
   >
   > **H2: [hypothesis statement]**
   > - Test: [how to verify]
   >
   > Should I add these to the Testable Hypotheses section?"

   Update the Testable Hypotheses section if confirmed.

6. **Confirm next steps**:
   > "Investigation created at `<investigation_directory>`.
   >
   > **To continue exploring**: Work through hypotheses in the Exploration Log
   > **To document findings**: Update the Findings section as you verify/falsify
   > **To propose work**: Add chunk prompts to Proposed Chunks when action items emerge
   >   (see OVERVIEW.md for `depends_on` semantics when declaring inter-chunk dependencies)
   > **To resolve**: Update status to SOLVED, NOTED, or DEFERRED when complete"

---

## Phase 2B: Chunk Redirect (Simple Task)

If the task is better suited as a direct chunk:

1. **Explain why investigation isn't needed**:
   > "This looks like a straightforward task rather than an investigation:
   > - [reason 1 from signals above]
   > - [reason 2 if applicable]
   >
   > A full investigation would add overhead without much benefit here."

2. **Offer to create a chunk instead**:
   > "I can create a chunk directly with `/chunk-create` using this prompt:
   >
   > `[suggested chunk description derived from their input]`
   >
   > Would you like me to proceed with creating a chunk instead?"

3. **Allow override**:
   > "If you still feel this needs investigation (perhaps there's uncertainty
   > I'm not seeing), I'm happy to create an investigation instead. Just let me
   > know."

4. **If user confirms chunk**: Invoke `/chunk-create` with the suggested description.

5. **If user requests investigation**: Return to Phase 2A.
