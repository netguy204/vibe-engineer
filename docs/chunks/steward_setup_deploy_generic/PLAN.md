

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The fix lives entirely in `src/templates/commands/steward-setup.md.jinja2`. The
autonomous mode behavior section is wrapped in `{% raw %}...{% endraw %}`, so
its content is emitted verbatim as prose instructions to the agent that runs
`/steward-setup`. The conditional deploy logic does not need Jinja2
conditionals — instead, we update the prose to:

1. Add a new interview question asking for an optional post-push deploy command.
2. Rewrite step 6 of the autonomous behavior template to be instruction-driven:
   if the operator provided a command, include it; if not, omit the step
   entirely.

After editing the template, re-render with `uv run ve init` to regenerate
`.claude/commands/steward-setup.md` and verify the hardcoded strings are gone.

No new Python code is needed — this is a template-only change. Testing is
verification-by-inspection: confirm the rendered output no longer contains
`workers/leader-board` or `npm run deploy`, and does contain the new interview
question.

## Sequence

### Step 1: Add interview question 7 for optional deploy command

In `src/templates/commands/steward-setup.md.jinja2`, inside the
`### Interview the operator` section (which is inside `{% raw %}`), add a new
question after the existing question 6 (Server URL):

```
7. **Post-push deploy command** (optional) — A shell command to run after
   `git push` completes. Leave blank if this project has no deploy step.
   - Example: `cd workers/my-worker && npm run deploy`
   - Example: `./scripts/deploy.sh`
   - If provided, this command will be embedded in the steward's STEWARD.md
     so the steward runs it automatically after each push.
```

### Step 2: Rewrite step 6 of the autonomous mode behavior template

Still inside `{% raw %}`, in the `#### Autonomous mode suggested behavior
section`, replace the current step 6:

**Before:**
```
6. **Deploy Durable Object worker** (conditional) — After pushing, check
   whether the completed chunk's `code_paths` (in its GOAL.md frontmatter)
   include files under `workers/`. If so, run
   `cd workers/leader-board && npm run deploy` and verify it succeeds. If
   the deploy fails, include the error in the changelog entry.
```

**After:**
```
6. **Deploy** (conditional) — If the operator provided a post-push deploy
   command during setup, run it now and verify it succeeds. If the deploy
   fails, include the error in the changelog entry. If no deploy command
   was provided, skip this step.
```

Also update the instructions that follow the behavior template to tell the
agent: when writing STEWARD.md, include step 6 only if the operator provided
a deploy command; otherwise omit it and renumber step 7 to 6. The placeholder
for the command in the generated STEWARD.md should use the operator-supplied
value verbatim.

Specifically, after the closing ` ``` ` of the autonomous mode behavior block,
add a clarifying note:

```
> **When writing the STEWARD.md**: If the operator provided a deploy command
> in question 7, replace "run it now" in step 6 with the actual command.
> If the operator left question 7 blank, omit step 6 entirely and renumber
> step 7 to step 6.
```

### Step 3: Re-render the command file

Run:

```
uv run ve init
```

This regenerates `.claude/commands/steward-setup.md` from the updated template.

### Step 4: Verify the rendered output

Read `.claude/commands/steward-setup.md` and confirm:

1. The strings `workers/leader-board` and `npm run deploy` are absent.
2. The new interview question 7 (post-push deploy command) is present.
3. Step 6 of the autonomous behavior template is the generic conditional form.
4. The clarifying note about conditional inclusion is present.
5. All other content is unchanged.

## Risks and Open Questions

- **Existing STEWARD.md files**: The goal explicitly notes that
  `leader-board`'s already-generated STEWARD.md is unaffected — this is
  correct since we're only changing the generation template, not patching
  existing files.

- **Renumbering**: If a deploy command is omitted, the agent writing STEWARD.md
  must renumber step 7 → 6. The prose instructions handle this. The
  clarifying note (Step 2 above) makes this explicit.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
