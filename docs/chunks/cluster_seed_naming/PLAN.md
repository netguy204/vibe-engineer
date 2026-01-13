<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds naming guidance to the `/chunk-create` skill template. The guidance
helps operators choose good prefix names when creating chunks that will seed new
clusters (i.e., when no similar existing chunks are found).

The implementation is purely additive text in the skill template. No code changes
are required — this is guidance embedded in the skill's step 1 (naming).

Key principles from the investigation:
- Use characteristic guidelines ("What initiative does this advance?") not prescriptive ones
- First chunk in a cluster is the critical naming decision — poor seed names cascade
- Initiative nouns (ordering_, taskdir_, template_) work; artifact types (chunk_, fix_, cli_) fail
- The `/chunk-plan` skill already handles prefix suggestion for similar chunks; this handles the bootstrapping case

## Subsystem Considerations

No subsystems are relevant to this chunk. The change is purely to skill template
content — no code patterns or subsystem interactions are affected.

## Sequence

### Step 1: Add cluster seed naming guidance to chunk-create template

Edit `src/templates/commands/chunk-create.md.jinja2` to add naming guidance in step 1
(where the short name is determined). The guidance should:

1. Use the characteristic question format: "What initiative does this chunk advance?"
2. Include examples of good prefixes (initiative nouns) and bad prefixes (artifact types)
3. Suggest looking at related narratives or investigations for initiative names
4. Note that `/chunk-plan` handles similar-chunk suggestions, but first chunk seeds are critical

Location: `src/templates/commands/chunk-create.md.jinja2`, step 1

### Step 2: Regenerate command file

Run `ve init` to regenerate `.claude/commands/chunk-create.md` from the updated template.

### Step 3: Update GOAL.md code_paths

Add the modified file to the chunk's `code_paths` field in GOAL.md.

### Step 4: Update investigation proposed_chunks

Update `docs/investigations/alphabetical_chunk_grouping/OVERVIEW.md` to set the
`chunk_directory` field for the "characteristic naming prompt for cluster seeds"
proposed chunk entry to `cluster_seed_naming`.

## Dependencies

None. This chunk adds guidance that complements the existing `cluster_prefix_suggest`
chunk (which is already ACTIVE), but does not depend on it for implementation.

## Risks and Open Questions

None. This is a low-risk change — adding guidance text to a skill template. The
guidance is based on verified findings from the `alphabetical_chunk_grouping`
investigation.

## Deviations

None. Implementation followed the plan exactly.